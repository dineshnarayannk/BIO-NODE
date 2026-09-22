"""Pydantic schemas for biological compounds, proteins, genes, pathways, processes, and evidence."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CompoundSummary(BaseModel):
    """Summary structure for a biological compound entity."""

    id: Optional[str] = None
    name: str
    canonical_id: Optional[str] = None
    pubchem_cid: Optional[int] = None
    formula: Optional[str] = None
    smiles: Optional[str] = None
    molecular_weight: Optional[float] = None
    source: Optional[str] = None


class ProteinSummary(BaseModel):
    """Summary representation of a Protein target entity."""

    id: int
    name: str
    canonical_id: str  # UniProt accession (e.g. P11388)
    relationship_type: Optional[str] = "targets"
    created_at: Optional[datetime] = None


class GeneSummary(BaseModel):
    """Summary representation of an encoding Gene entity."""

    id: int
    name: str
    canonical_id: str  # Gene symbol (e.g. TOP2A)
    source_protein_id: Optional[int] = None
    created_at: Optional[datetime] = None


class PathwaySummary(BaseModel):
    """Summary representation of a biological Pathway entity."""

    id: int
    name: str
    canonical_id: str  # Reactome ID (e.g. R-HSA-5693532)
    source_gene_symbol: Optional[str] = None
    created_at: Optional[datetime] = None


class BiologicalProcessSummary(BaseModel):
    """Summary representation of a Biological Process (Gene Ontology) entity."""

    id: int
    name: str
    canonical_id: str  # GO ID (e.g. GO:0006259)
    source_gene_symbol: Optional[str] = None
    created_at: Optional[datetime] = None


class EvidenceSummary(BaseModel):
    """Summary representation of a literature Evidence grounding record."""

    id: int
    relationship_id: int
    source_database: str
    source_record_id: Optional[str] = None  # e.g. PMID
    evidence_type: Optional[str] = None
    confidence: Optional[float] = None
    source_url: Optional[str] = None
    retrieved_at: Optional[datetime] = None


class CompoundDetailResponse(BaseModel):
    """Detailed response payload for a single compound with biological graph linkages."""

    compound: CompoundSummary
    target_proteins: List[ProteinSummary] = Field(default_factory=list)
    associated_genes: List[GeneSummary] = Field(default_factory=list)
    pathways: List[PathwaySummary] = Field(default_factory=list)
    biological_processes: List[BiologicalProcessSummary] = Field(default_factory=list)
    evidence: List[EvidenceSummary] = Field(default_factory=list)


class CompoundSearchResponse(BaseModel):
    """Response payload for compound search query."""

    query: str
    total_matches: int = 0
    items: List[CompoundSummary] = Field(default_factory=list)
    message: str = "Query executed against biological knowledge base."
    metadata: Dict[str, Any] = Field(default_factory=dict)
