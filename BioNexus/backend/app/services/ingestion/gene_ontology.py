"""Gene Ontology (GO) biological process ingestion and gene-to-process relationship service.

Parses biological process records, normalizes GO identifiers, creates or updates
BiologicalProcess entities, and establishes 'gene -> associated_with -> biological_process' relationships.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...db.models import BiologicalProcess, Gene, Relationship
from ..normalization import normalize_gene_symbol, normalize_go_id

logger = logging.getLogger("bionexus.ingestion.go")


def ingest_process_record(
    db: Session,
    go_id: str,
    name: str,
    gene_symbol: Optional[str] = None,
) -> Tuple[Optional[BiologicalProcess], Optional[Relationship]]:
    """Ingest a single BiologicalProcess (GO term) and link an associated Gene if provided.

    Deduplicates BiologicalProcess entities by canonical_id.
    Creates a 'gene -> associated_with -> biological_process' relationship if gene exists.
    """
    canon_go_id = normalize_go_id(go_id)
    if not canon_go_id:
        logger.warning(f"Invalid GO ID: {go_id}")
        return None, None

    cleaned_name = name.strip() if name else f"Process {canon_go_id}"

    # 1. Lookup or create BiologicalProcess
    process = db.execute(
        select(BiologicalProcess).where(BiologicalProcess.canonical_id == canon_go_id)
    ).scalar_one_or_none()

    if process is None:
        process = BiologicalProcess(
            name=cleaned_name,
            canonical_id=canon_go_id,
        )
        db.add(process)
        db.flush()
    else:
        if process.name.startswith("Process ") and not cleaned_name.startswith("Process "):
            process.name = cleaned_name
            db.flush()

    rel = None
    # 2. Link Gene to BiologicalProcess if gene_symbol provided
    if gene_symbol:
        canon_gene_id = normalize_gene_symbol(gene_symbol)
        if canon_gene_id:
            gene = db.execute(
                select(Gene).where(Gene.canonical_id == canon_gene_id)
            ).scalar_one_or_none()

            # If gene does not exist, create placeholder gene record
            if gene is None:
                gene = Gene(
                    name=canon_gene_id,
                    canonical_id=canon_gene_id,
                )
                db.add(gene)
                db.flush()

            rel = db.execute(
                select(Relationship).where(
                    Relationship.source_type == "gene",
                    Relationship.source_id == gene.id,
                    Relationship.relationship_type == "associated_with",
                    Relationship.target_type == "biological_process",
                    Relationship.target_id == process.id,
                )
            ).scalar_one_or_none()

            if rel is None:
                rel = Relationship(
                    source_type="gene",
                    source_id=gene.id,
                    relationship_type="associated_with",
                    target_type="biological_process",
                    target_id=process.id,
                )
                db.add(rel)
                db.flush()

    return process, rel


def ingest_go_batch(
    db: Session,
    records: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Ingest a batch of verified Gene Ontology biological process mappings.

    Expected record keys:
      - 'go_id' (e.g. 'GO:0006915')
      - 'name' (e.g. 'apoptotic process')
      - 'gene_symbol' (e.g. 'TOP2A') [optional]
    """
    stats = {
        "processes_created": 0,
        "processes_existing": 0,
        "relationships_created": 0,
        "invalid_records": 0,
    }

    for item in records:
        go_id = item.get("go_id")
        name = item.get("name")
        gene_symbol = item.get("gene_symbol")

        if not go_id or not normalize_go_id(go_id):
            stats["invalid_records"] += 1
            continue

        existing_p = db.execute(
            select(BiologicalProcess).where(BiologicalProcess.canonical_id == normalize_go_id(go_id))
        ).scalar_one_or_none()

        process, rel = ingest_process_record(
            db,
            go_id=go_id,
            name=name,
            gene_symbol=gene_symbol,
        )

        if process:
            if existing_p is None:
                stats["processes_created"] += 1
            else:
                stats["processes_existing"] += 1

        if rel:
            stats["relationships_created"] += 1

    db.commit()
    return stats
