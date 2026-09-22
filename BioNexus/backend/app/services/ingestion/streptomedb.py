"""StreptomeDB Natural Compound SDF Ingestion Service.

Parses StreptomeDB SDF dataset files, normalizes chemical identifiers,
handles missing fields and duplicate records, and imports clean compound
entities into the TiDB Cloud / MySQL database.
"""

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from ...core.config import settings
from ...db.models import Compound
from ...db.session import get_engine, get_session_factory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bionexus.ingestion.streptomedb")

# Default SDF path candidates
DEFAULT_SDF_PATHS = [
    Path(__file__).resolve().parent.parent.parent.parent / "data" / "raw" / "streptomedb.sdf",
    Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "raw" / "streptomedb.sdf",
    Path(__file__).resolve().parent.parent.parent.parent.parent / "streptomedb.sdf",
]


@dataclass
class NormalizedCompound:
    """Normalized compound record ready for database persistence."""

    name: str
    canonical_id: str
    pubchem_cid: Optional[int]
    smiles: Optional[str]
    molecular_weight: Optional[float]
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionSummary:
    """Telemetry and metrics summary for an ingestion run."""

    file_path: str
    records_read: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    parsing_errors: int = 0
    duplicates: int = 0

    def print_summary(self, dry_run: bool = False) -> None:
        mode_str = " (DRY RUN - No DB changes)" if dry_run else ""
        logger.info(f"=== StreptomeDB Ingestion Summary{mode_str} ===")
        logger.info(f"Source file:        {self.file_path}")
        logger.info(f"Records read:       {self.records_read}")
        logger.info(f"Records inserted:   {self.records_inserted}")
        logger.info(f"Records updated:    {self.records_updated}")
        logger.info(f"Records skipped:    {self.records_skipped}")
        logger.info(f"Duplicates:         {self.duplicates}")
        logger.info(f"Parsing errors:     {self.parsing_errors}")
        logger.info("==============================================")


class StreptomeDBIngester:
    """Ingestion pipeline for StreptomeDB natural products."""

    @classmethod
    def resolve_sdf_path(cls, explicit_path: Optional[str] = None) -> Optional[Path]:
        """Locate the SDF file from explicit path or default candidates."""
        if explicit_path:
            p = Path(explicit_path).resolve()
            if p.exists() and p.is_file():
                return p
            logger.error(f"Specified SDF file not found: {explicit_path}")
            return None

        for p in DEFAULT_SDF_PATHS:
            if p.exists() and p.is_file():
                return p

        logger.error(
            "StreptomeDB SDF dataset not found. Please place 'streptomedb.sdf' in 'data/raw/'."
        )
        return None

    @classmethod
    def parse_sdf_block(cls, block_text: str) -> Dict[str, str]:
        """Parse property tags from an individual SDF record block."""
        props: Dict[str, str] = {}
        lines = block_text.splitlines()

        # First line is traditionally the molecule title
        if lines and not lines[0].startswith(">"):
            title = lines[0].strip()
            if title and not title.startswith("$$$$") and not title.startswith("OpenBabel"):
                props["_title"] = title

        current_tag: Optional[str] = None
        current_val_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(">") and "<" in stripped and ">" in stripped[stripped.find("<") :]:
                if current_tag is not None:
                    props[current_tag] = "\n".join(current_val_lines).strip()
                start = stripped.find("<") + 1
                end = stripped.find(">", start)
                current_tag = stripped[start:end].strip()
                current_val_lines = []
            elif current_tag is not None:
                if stripped == "$$$$":
                    break
                if stripped:
                    current_val_lines.append(stripped)

        if current_tag is not None:
            props[current_tag] = "\n".join(current_val_lines).strip()

        return props

    @classmethod
    def iterate_sdf_records(
        cls, file_path: Path, limit: Optional[int] = None
    ) -> Generator[Dict[str, str], None, None]:
        """Stream SDF records one-by-one from the dataset file."""
        count = 0
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            current_block: List[str] = []
            for line in f:
                if line.strip() == "$$$$":
                    if current_block:
                        block_text = "".join(current_block)
                        props = cls.parse_sdf_block(block_text)
                        if props:
                            yield props
                            count += 1
                            if limit is not None and count >= limit:
                                return
                        current_block = []
                else:
                    current_block.append(line)

            # Trailing block if any
            if current_block and (limit is None or count < limit):
                block_text = "".join(current_block)
                props = cls.parse_sdf_block(block_text)
                if props:
                    yield props

    @classmethod
    def normalize_record(cls, raw_props: Dict[str, str]) -> Optional[NormalizedCompound]:
        """Normalize raw SDF dictionary into a validated NormalizedCompound."""
        # 1. Canonical ID
        raw_id = (
            raw_props.get("compound_id")
            or raw_props.get("compound id")
            or raw_props.get("id")
            or ""
        ).strip()
        if not raw_id:
            return None

        canonical_id = f"SM_{raw_id}"

        # 2. Name (enforce safe length <= 495)
        raw_name = (
            raw_props.get("name")
            or raw_props.get("_title")
            or f"Compound {canonical_id}"
        ).strip()
        name = raw_name[:495] if len(raw_name) > 495 else raw_name

        # 3. SMILES
        smiles = (
            raw_props.get("canonical_smiles")
            or raw_props.get("smiles")
            or raw_props.get("canonical smiles")
        )
        if smiles:
            smiles = smiles.strip()
            if smiles.lower() in ("none", "null", ""):
                smiles = None

        # 4. PubChem CID
        raw_cid = (
            raw_props.get("pubchem cid")
            or raw_props.get("pubchem_cid")
            or raw_props.get("cid")
        )
        pubchem_cid: Optional[int] = None
        if raw_cid:
            cleaned_cid = str(raw_cid).strip()
            if cleaned_cid.isdigit():
                try:
                    pubchem_cid = int(cleaned_cid)
                except ValueError:
                    pubchem_cid = None

        # 5. Molecular Weight
        raw_mw = (
            raw_props.get("molwt")
            or raw_props.get("molecular_weight")
            or raw_props.get("mw")
        )
        molecular_weight: Optional[float] = None
        if raw_mw:
            try:
                molecular_weight = float(str(raw_mw).strip())
            except ValueError:
                molecular_weight = None

        # 6. StreptomeDB Source Metadata (preserved for future evidence mapping)
        metadata = {
            "source_database": "StreptomeDB",
            "streptomedb_id": raw_id,
            "organisms": raw_props.get("organisms", "").strip(),
            "pmids": raw_props.get("pmids", "").strip(),
            "activities": raw_props.get("activities", "").strip(),
            "synthesizing_routes": raw_props.get("synthesizing routes", "").strip(),
            "hbd": raw_props.get("HBD", "").strip(),
            "hba": raw_props.get("HBA", "").strip(),
            "rotatable_bonds": raw_props.get("rotatable bonds", "").strip(),
        }

        return NormalizedCompound(
            name=name,
            canonical_id=canonical_id,
            pubchem_cid=pubchem_cid,
            smiles=smiles,
            molecular_weight=molecular_weight,
            raw_metadata=metadata,
        )

    def import_dataset(
        self,
        db_session: Optional[Session] = None,
        file_path: Optional[str] = None,
        limit: Optional[int] = None,
        batch_size: int = 500,
        dry_run: bool = False,
    ) -> IngestionSummary:
        """Run the ingestion pipeline on the StreptomeDB SDF dataset."""
        resolved_path = self.resolve_sdf_path(file_path)
        if not resolved_path:
            raise FileNotFoundError(
                "StreptomeDB SDF dataset file could not be located."
            )

        summary = IngestionSummary(file_path=str(resolved_path))
        logger.info(f"Starting StreptomeDB ingestion from: {resolved_path}")
        if limit:
            logger.info(f"Limit applied: {limit} records (Validation Mode)")
        if dry_run:
            logger.info("DRY RUN ENABLED - No changes will be committed to database.")

        owns_session = False
        session = db_session

        if session is None and not dry_run:
            factory = get_session_factory()
            if factory is None:
                raise RuntimeError(
                    "Database is not configured. Please set DB_HOST / DATABASE_URL in .env."
                )
            session = factory()
            owns_session = True

        seen_canonical_ids = set()
        pending_records: List[NormalizedCompound] = []

        try:
            for raw_record in self.iterate_sdf_records(resolved_path, limit=limit):
                summary.records_read += 1
                try:
                    norm = self.normalize_record(raw_record)
                    if not norm:
                        summary.records_skipped += 1
                        continue

                    # Deduplication within batch / file
                    if norm.canonical_id in seen_canonical_ids:
                        summary.duplicates += 1
                        summary.records_skipped += 1
                        continue
                    seen_canonical_ids.add(norm.canonical_id)

                    pending_records.append(norm)

                    # Flush chunk when batch size reached
                    if len(pending_records) >= batch_size:
                        self._process_batch(session, pending_records, summary, dry_run)
                        logger.info(
                            f"Processed {summary.records_read} records "
                            f"(Inserted: {summary.records_inserted}, Updated: {summary.records_updated}, Skipped: {summary.records_skipped})..."
                        )
                        pending_records = []

                except Exception as e:
                    summary.parsing_errors += 1
                    logger.warning(f"Error parsing SDF record: {e}")

            # Flush remaining records
            if pending_records:
                self._process_batch(session, pending_records, summary, dry_run)

        except Exception as e:
            if session and not dry_run:
                session.rollback()
            logger.error(f"Ingestion failed with exception: {e}")
            raise
        finally:
            if owns_session and session is not None:
                session.close()

        summary.print_summary(dry_run=dry_run)
        return summary

    def _process_batch(
        self,
        session: Optional[Session],
        records: List[NormalizedCompound],
        summary: IngestionSummary,
        dry_run: bool,
    ) -> None:
        """Process a chunk of normalized compound records with fallback per record."""
        if dry_run or session is None:
            summary.records_inserted += len(records)
            return

        try:
            cids = [r.canonical_id for r in records]
            stmt = select(Compound).where(Compound.canonical_id.in_(cids))
            existing_rows = {
                row.canonical_id: row for row in session.execute(stmt).scalars().all()
            }

            to_insert: List[Dict[str, Any]] = []

            for item in records:
                if item.canonical_id in existing_rows:
                    existing = existing_rows[item.canonical_id]
                    updated = False
                    if existing.name != item.name:
                        existing.name = item.name
                        updated = True
                    if existing.smiles != item.smiles:
                        existing.smiles = item.smiles
                        updated = True
                    if existing.pubchem_cid != item.pubchem_cid:
                        existing.pubchem_cid = item.pubchem_cid
                        updated = True
                    if existing.molecular_weight != item.molecular_weight:
                        existing.molecular_weight = item.molecular_weight
                        updated = True
                    if updated:
                        summary.records_updated += 1
                    else:
                        summary.records_skipped += 1
                else:
                    to_insert.append(
                        {
                            "name": item.name,
                            "canonical_id": item.canonical_id,
                            "pubchem_cid": item.pubchem_cid,
                            "smiles": item.smiles,
                            "molecular_weight": item.molecular_weight,
                        }
                    )

            if to_insert:
                session.execute(insert(Compound), to_insert)
                summary.records_inserted += len(to_insert)

            session.commit()
        except Exception as e:
            session.rollback()
            logger.warning(
                f"Batch SQL insert error ({e}); falling back to single-record persistence for this batch..."
            )
            for item in records:
                try:
                    stmt = select(Compound).where(Compound.canonical_id == item.canonical_id)
                    existing = session.execute(stmt).scalar_one_or_none()
                    if existing:
                        existing.name = item.name
                        existing.smiles = item.smiles
                        existing.pubchem_cid = item.pubchem_cid
                        existing.molecular_weight = item.molecular_weight
                        summary.records_updated += 1
                    else:
                        new_c = Compound(
                            name=item.name,
                            canonical_id=item.canonical_id,
                            pubchem_cid=item.pubchem_cid,
                            smiles=item.smiles,
                            molecular_weight=item.molecular_weight,
                        )
                        session.add(new_c)
                        summary.records_inserted += 1
                    session.commit()
                except Exception as sub_e:
                    session.rollback()
                    summary.parsing_errors += 1
                    logger.warning(
                        f"Failed to persist compound {item.canonical_id}: {sub_e}"
                    )


def main():
    """CLI entrypoint for StreptomeDB SDF ingestion."""
    parser = argparse.ArgumentParser(
        description="BioNexus StreptomeDB Natural Compound Ingestion Pipeline"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of records to ingest (useful for validation mode, e.g. --limit 10)",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to streptomedb.sdf file",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Database batch size for chunked upserts (default: 500)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate records without committing to database",
    )

    args = parser.parse_args()

    ingester = StreptomeDBIngester()
    try:
        summary = ingester.import_dataset(
            file_path=args.file,
            limit=args.limit,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal ingestion error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
