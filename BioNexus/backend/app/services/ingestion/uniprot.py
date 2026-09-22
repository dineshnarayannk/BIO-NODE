"""UniProt protein ingestion and protein-to-gene relationship service.

Parses protein records, normalizes UniProt accessions, creates or updates
Protein and Gene entities, and establishes 'encoded_by' relationships.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...db.models import Gene, Protein, Relationship
from ..normalization import normalize_gene_symbol, normalize_uniprot_id

logger = logging.getLogger("bionexus.ingestion.uniprot")


def ingest_protein_record(
    db: Session,
    uniprot_id: str,
    name: str,
    gene_symbol: Optional[str] = None,
    gene_name: Optional[str] = None,
) -> Tuple[Optional[Protein], Optional[Gene], Optional[Relationship]]:
    """Safely ingest a single Protein and its encoding Gene into the database.

    Deduplicates entities by canonical_id.
    Creates a 'protein -> encoded_by -> gene' relationship if gene is present.

    Returns:
        (protein_entity, gene_entity, relationship_entity)
    """
    canon_protein_id = normalize_uniprot_id(uniprot_id)
    if not canon_protein_id:
        logger.warning(f"Invalid UniProt ID provided: {uniprot_id}")
        return None, None, None

    cleaned_name = name.strip() if name else f"Protein {canon_protein_id}"

    # 1. Lookup or create Protein
    protein = db.execute(
        select(Protein).where(Protein.canonical_id == canon_protein_id)
    ).scalar_one_or_none()

    if protein is None:
        protein = Protein(
            name=cleaned_name,
            canonical_id=canon_protein_id,
        )
        db.add(protein)
        db.flush()  # get protein.id
    else:
        # Update name if previously generic
        if protein.name.startswith("Protein ") and not cleaned_name.startswith("Protein "):
            protein.name = cleaned_name
            db.flush()

    gene = None
    rel = None

    # 2. Lookup or create Gene if provided
    if gene_symbol:
        canon_gene_id = normalize_gene_symbol(gene_symbol)
        if canon_gene_id:
            gene_display_name = gene_name.strip() if gene_name else canon_gene_id
            gene = db.execute(
                select(Gene).where(Gene.canonical_id == canon_gene_id)
            ).scalar_one_or_none()

            if gene is None:
                gene = Gene(
                    name=gene_display_name,
                    canonical_id=canon_gene_id,
                )
                db.add(gene)
                db.flush()

            # 3. Create 'protein -> encoded_by -> gene' relationship if not exists
            rel = db.execute(
                select(Relationship).where(
                    Relationship.source_type == "protein",
                    Relationship.source_id == protein.id,
                    Relationship.relationship_type == "encoded_by",
                    Relationship.target_type == "gene",
                    Relationship.target_id == gene.id,
                )
            ).scalar_one_or_none()

            if rel is None:
                rel = Relationship(
                    source_type="protein",
                    source_id=protein.id,
                    relationship_type="encoded_by",
                    target_type="gene",
                    target_id=gene.id,
                )
                db.add(rel)
                db.flush()

    return protein, gene, rel


def ingest_uniprot_batch(
    db: Session,
    records: List[Dict[str, Any]],
) -> Dict[str, int]:
    """Ingest a batch of verified UniProt protein definitions.

    Expected record keys:
      - 'uniprot_id' (e.g. 'P11388')
      - 'name' (e.g. 'DNA topoisomerase 2-alpha')
      - 'gene_symbol' (e.g. 'TOP2A')
      - 'gene_name' (e.g. 'Topoisomerase (DNA) II Alpha')
    """
    stats = {
        "proteins_created": 0,
        "proteins_existing": 0,
        "genes_created": 0,
        "genes_existing": 0,
        "relationships_created": 0,
        "relationships_existing": 0,
        "invalid_records": 0,
    }

    for item in records:
        uniprot_id = item.get("uniprot_id")
        name = item.get("name")
        gene_symbol = item.get("gene_symbol")
        gene_name = item.get("gene_name")

        if not uniprot_id or not normalize_uniprot_id(uniprot_id):
            stats["invalid_records"] += 1
            continue

        existing_p = db.execute(
            select(Protein).where(Protein.canonical_id == normalize_uniprot_id(uniprot_id))
        ).scalar_one_or_none()

        existing_g = None
        if gene_symbol and normalize_gene_symbol(gene_symbol):
            existing_g = db.execute(
                select(Gene).where(Gene.canonical_id == normalize_gene_symbol(gene_symbol))
            ).scalar_one_or_none()

        protein, gene, rel = ingest_protein_record(
            db,
            uniprot_id=uniprot_id,
            name=name,
            gene_symbol=gene_symbol,
            gene_name=gene_name,
        )

        if protein:
            if existing_p is None:
                stats["proteins_created"] += 1
            else:
                stats["proteins_existing"] += 1

        if gene:
            if existing_g is None:
                stats["genes_created"] += 1
            else:
                stats["genes_existing"] += 1

        if rel:
            stats["relationships_created"] += 1

    db.commit()
    return stats
