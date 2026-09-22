"""Reactome pathway ingestion and gene-to-pathway relationship service.

Parses biological pathway records, normalizes Reactome identifiers, creates or updates
Pathway entities, and establishes 'gene -> participates_in -> pathway' relationships.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...db.models import Gene, Pathway, Relationship
from ..normalization import normalize_gene_symbol, normalize_reactome_id

logger = logging.getLogger("bionexus.ingestion.reactome")


def ingest_pathway_record(
    db: Session,
    reactome_id: str,
    name: str,
    gene_symbol: Optional[str] = None,
) -> Tuple[Optional[Pathway], Optional[Relationship]]:
    """Ingest a single Reactome Pathway and link an associated Gene if provided.

    Deduplicates Pathway entities by canonical_id.
    Creates a 'gene -> participates_in -> pathway' relationship if gene exists.
    """
    canon_pathway_id = normalize_reactome_id(reactome_id)
    if not canon_pathway_id:
        logger.warning(f"Invalid Reactome ID: {reactome_id}")
        return None, None

    cleaned_name = name.strip() if name else f"Pathway {canon_pathway_id}"

    # 1. Lookup or create Pathway
    pathway = db.execute(
        select(Pathway).where(Pathway.canonical_id == canon_pathway_id)
    ).scalar_one_or_none()

    if pathway is None:
        pathway = Pathway(
            name=cleaned_name,
            canonical_id=canon_pathway_id,
        )
        db.add(pathway)
        db.flush()
    else:
        if pathway.name.startswith("Pathway ") and not cleaned_name.startswith("Pathway "):
            pathway.name = cleaned_name
            db.flush()

    rel = None
    # 2. Link Gene to Pathway if gene_symbol provided
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
                    Relationship.relationship_type == "participates_in",
                    Relationship.target_type == "pathway",
                    Relationship.target_id == pathway.id,
                )
            ).scalar_one_or_none()

            if rel is None:
                rel = Relationship(
                    source_type="gene",
                    source_id=gene.id,
                    relationship_type="participates_in",
                    target_type="pathway",
                    target_id=pathway.id,
                )
                db.add(rel)
                db.flush()

    return pathway, rel


def ingest_reactome_batch(
    db: Session,
    records: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Ingest a batch of verified Reactome pathway mappings.

    Expected record keys:
      - 'reactome_id' (e.g. 'R-HSA-5693532')
      - 'name' (e.g. 'DNA Double-Strand Break Repair')
      - 'gene_symbol' (e.g. 'TOP2A') [optional]
    """
    stats = {
        "pathways_created": 0,
        "pathways_existing": 0,
        "relationships_created": 0,
        "invalid_records": 0,
    }

    for item in records:
        reactome_id = item.get("reactome_id")
        name = item.get("name")
        gene_symbol = item.get("gene_symbol")

        if not reactome_id or not normalize_reactome_id(reactome_id):
            stats["invalid_records"] += 1
            continue

        existing_p = db.execute(
            select(Pathway).where(Pathway.canonical_id == normalize_reactome_id(reactome_id))
        ).scalar_one_or_none()

        pathway, rel = ingest_pathway_record(
            db,
            reactome_id=reactome_id,
            name=name,
            gene_symbol=gene_symbol,
        )

        if pathway:
            if existing_p is None:
                stats["pathways_created"] += 1
            else:
                stats["pathways_existing"] += 1

        if rel:
            stats["relationships_created"] += 1

    db.commit()
    return stats
