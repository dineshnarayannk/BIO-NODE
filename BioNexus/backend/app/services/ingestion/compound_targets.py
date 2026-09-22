"""Compound-to-Protein target relationship and literature Evidence ingestion service.

Establishes 'compound -> targets -> protein' relationships and attaches
literature-grounded Evidence records (PubMed PMIDs, source databases, citations).
Strictly adheres to scientific truthfulness: confidence is NULL unless quantified by source.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from ...db.models import Compound, Evidence, Protein, Relationship
from ..normalization import normalize_uniprot_id

logger = logging.getLogger("bionexus.ingestion.compound_targets")


def ingest_compound_target_interaction(
    db: Session,
    compound_identifier: str,
    uniprot_id: str,
    source_database: str = "PubMed",
    source_record_id: Optional[str] = None,
    evidence_type: Optional[str] = "curated_literature",
    confidence: Optional[float] = None,
    source_url: Optional[str] = None,
) -> Tuple[Optional[Relationship], Optional[Evidence]]:
    """Connect a Compound in TiDB to a target Protein and attach an Evidence record.

    Matches compound by canonical_id (e.g., 'SM_31') or exact name (e.g., 'Doxorubicin').
    Matches protein by canonical UniProt ID (e.g., 'P11388').

    Returns:
        (relationship_entity, evidence_entity)
    """
    canon_uniprot = normalize_uniprot_id(uniprot_id)
    if not canon_uniprot:
        logger.warning(f"Invalid UniProt ID for compound target: {uniprot_id}")
        return None, None

    # 1. Find the compound
    compound = db.execute(
        select(Compound).where(
            or_(
                Compound.canonical_id == compound_identifier,
                Compound.name == compound_identifier,
            )
        )
    ).scalars().first()

    if compound is None:
        logger.warning(f"Compound not found in database: '{compound_identifier}'")
        return None, None

    # 2. Find the protein
    protein = db.execute(
        select(Protein).where(Protein.canonical_id == canon_uniprot)
    ).scalar_one_or_none()

    if protein is None:
        logger.warning(f"Protein '{canon_uniprot}' not found in database.")
        return None, None

    # 3. Create or find 'compound -> targets -> protein' relationship
    rel = db.execute(
        select(Relationship).where(
            Relationship.source_type == "compound",
            Relationship.source_id == compound.id,
            Relationship.relationship_type == "targets",
            Relationship.target_type == "protein",
            Relationship.target_id == protein.id,
        )
    ).scalar_one_or_none()

    if rel is None:
        rel = Relationship(
            source_type="compound",
            source_id=compound.id,
            relationship_type="targets",
            target_type="protein",
            target_id=protein.id,
        )
        db.add(rel)
        db.flush()

    # 4. Create or find Evidence attached to relationship
    evidence = None
    if source_database:
        # Construct standard PubMed URL if PMID is supplied without explicit URL
        if not source_url and source_record_id and source_record_id.isdigit():
            source_url = f"https://pubmed.ncbi.nlm.nih.gov/{source_record_id}/"

        evidence = db.execute(
            select(Evidence).where(
                Evidence.relationship_id == rel.id,
                Evidence.source_database == source_database,
                Evidence.source_record_id == source_record_id,
            )
        ).scalar_one_or_none()

        if evidence is None:
            evidence = Evidence(
                relationship_id=rel.id,
                source_database=source_database,
                source_record_id=source_record_id,
                evidence_type=evidence_type,
                confidence=confidence,  # None/NULL unless explicit
                source_url=source_url,
            )
            db.add(evidence)
            db.flush()

    return rel, evidence


def ingest_compound_targets_batch(
    db: Session,
    interactions: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Ingest a batch of verified compound-protein target interactions with evidence.

    Expected interaction keys:
      - 'compound_identifier' (e.g. 'SM_31' or 'Doxorubicin')
      - 'uniprot_id' (e.g. 'P11388')
      - 'source_database' (e.g. 'StreptomeDB' / 'PubMed' / 'ChEMBL')
      - 'source_record_id' (e.g. '11094008')
      - 'evidence_type' (e.g. 'curated_literature' / 'experimental_assay')
      - 'confidence' (e.g. None or float)
      - 'source_url' (e.g. 'https://pubmed.ncbi.nlm.nih.gov/11094008/') [optional]
    """
    stats = {
        "relationships_created": 0,
        "evidence_created": 0,
        "skipped_records": 0,
    }

    for item in interactions:
        compound_id = item.get("compound_identifier")
        uniprot_id = item.get("uniprot_id")

        if not compound_id or not uniprot_id:
            stats["skipped_records"] += 1
            continue

        existing_rel = db.execute(
            select(Relationship).join(
                Compound,
                Compound.id == Relationship.source_id,
            ).join(
                Protein,
                Protein.id == Relationship.target_id,
            ).where(
                Relationship.source_type == "compound",
                or_(
                    Compound.canonical_id == compound_id,
                    Compound.name == compound_id,
                ),
                Relationship.relationship_type == "targets",
                Relationship.target_type == "protein",
                Protein.canonical_id == normalize_uniprot_id(uniprot_id),
            )
        ).scalar_one_or_none()

        rel, ev = ingest_compound_target_interaction(
            db,
            compound_identifier=compound_id,
            uniprot_id=uniprot_id,
            source_database=item.get("source_database", "PubMed"),
            source_record_id=item.get("source_record_id"),
            evidence_type=item.get("evidence_type", "curated_literature"),
            confidence=item.get("confidence"),
            source_url=item.get("source_url"),
        )

        if rel and existing_rel is None:
            stats["relationships_created"] += 1
        elif rel is None:
            stats["skipped_records"] += 1

        if ev:
            stats["evidence_created"] += 1

    db.commit()
    return stats
