"""Biological entity identifier normalization service.

Provides canonical normalization for UniProt protein accessions, HGNC/NCBI gene symbols,
Reactome pathway IDs, and Gene Ontology (GO) terms.
"""

import re
from typing import Optional

# Regular expressions for canonical biological identifiers
UNIPROT_REGEX = re.compile(
    r"^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$",
    re.IGNORECASE,
)
REACTOME_REGEX = re.compile(r"^R-[A-Z]{3}-[0-9]+(\.[0-9]+)?$", re.IGNORECASE)
GO_REGEX = re.compile(r"^GO:[0-9]{7}$", re.IGNORECASE)
GENE_SYMBOL_REGEX = re.compile(r"^[A-Z0-9_\-\.]{1,30}$", re.IGNORECASE)


def normalize_uniprot_id(raw_id: Optional[str]) -> Optional[str]:
    """Normalize and validate a UniProt accession identifier (e.g., 'P00533', 'P11388').

    Strips whitespace and uppercase prefixes/suffixes.
    Returns canonical uppercase accession or None if invalid.
    """
    if not raw_id:
        return None
    cleaned = str(raw_id).strip().upper()
    # Remove common prefixes like 'UNIPROT:' or 'ACC:'
    if cleaned.startswith("UNIPROT:"):
        cleaned = cleaned.replace("UNIPROT:", "").strip()
    if cleaned.startswith("UP:"):
        cleaned = cleaned.replace("UP:", "").strip()

    # Match primary accession format
    # UniProt format: 6 or 10 characters alphanumeric
    if UNIPROT_REGEX.match(cleaned):
        return cleaned
    return None


def normalize_gene_symbol(raw_symbol: Optional[str]) -> Optional[str]:
    """Normalize a gene symbol / HGNC / NCBI identifier (e.g., 'EGFR', 'TOP2A', 'rpsL').

    Returns standard uppercase gene symbol or None if invalid.
    """
    if not raw_symbol:
        return None
    cleaned = str(raw_symbol).strip().upper()
    if cleaned.startswith("GENE:"):
        cleaned = cleaned.replace("GENE:", "").strip()
    if cleaned.startswith("HGNC:"):
        cleaned = cleaned.replace("HGNC:", "").strip()

    if not cleaned:
        return None

    if GENE_SYMBOL_REGEX.match(cleaned):
        return cleaned
    return None


def normalize_reactome_id(raw_id: Optional[str]) -> Optional[str]:
    """Normalize a Reactome pathway identifier (e.g., 'R-HSA-1640170', 'reactome:R-HSA-72766').

    Returns standard Reactome identifier (e.g. 'R-HSA-1640170') or None if invalid.
    """
    if not raw_id:
        return None
    cleaned = str(raw_id).strip().upper()
    if cleaned.startswith("REACTOME:"):
        cleaned = cleaned.replace("REACTOME:", "").strip()

    if REACTOME_REGEX.match(cleaned):
        return cleaned
    return None


def normalize_go_id(raw_id: Optional[str]) -> Optional[str]:
    """Normalize a Gene Ontology identifier (e.g., 'GO:0006915', '0006915').

    Returns standard 'GO:0000000' formatted string or None if invalid.
    """
    if not raw_id:
        return None
    cleaned = str(raw_id).strip().upper()
    if not cleaned.startswith("GO:"):
        if cleaned.isdigit() and len(cleaned) <= 7:
            cleaned = f"GO:{cleaned.zfill(7)}"
        else:
            return None

    if GO_REGEX.match(cleaned):
        return cleaned
    return None
