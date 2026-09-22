"""Pydantic schemas for Graph Analysis, Biological Analysis, Evidence Provenance, and Gemini Explanations."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .compound import CompoundSummary, EvidenceSummary


# ============================================================================
# Step 6: Graph Analysis Models
# ============================================================================


class CentralityScore(BaseModel):
    """Node centrality metric in knowledge graph."""

    node_id: str
    db_id: int
    name: str
    canonical_id: str
    entity_type: str
    degree_centrality: float
    betweenness_centrality: float
    connectivity_label: str  # e.g. "highly connected node", "high centrality node"


class GraphPath(BaseModel):
    """Directed traversal path from compound to downstream biological entities."""

    path_type: str  # "compound_to_protein", "compound_to_gene", "compound_to_pathway", "compound_to_process"
    nodes: List[str]  # e.g. ["compound:2712", "protein:1", "gene:1", "pathway:1"]
    node_names: List[str]  # e.g. ["Doxorubicin", "DNA topoisomerase 2-alpha", "TOP2A", "DNA Double-Strand Break Repair"]
    length: int
    is_documented_direct: bool  # True only if path length == 1 (direct relationship)


class ConvergencePoint(BaseModel):
    """Convergence point where multiple upstream biological entities converge."""

    node_id: str
    db_id: int
    name: str
    canonical_id: str
    entity_type: str
    in_degree: int
    incoming_sources: List[str]


class GraphAnalysisResponse(BaseModel):
    """Computational graph analysis results using NetworkX."""

    compound: CompoundSummary
    total_nodes: int
    total_edges: int
    central_nodes: List[CentralityScore] = Field(default_factory=list)
    convergence_points: List[ConvergencePoint] = Field(default_factory=list)
    paths: List[GraphPath] = Field(default_factory=list)
    relationship_distribution: Dict[str, int] = Field(default_factory=dict)
    connected_components: int = 1
    summary: str


# ============================================================================
# Step 7: Biological / Pathway Analysis Models
# ============================================================================


class BiologicalPathwaySummary(BaseModel):
    """Pathway biological profile."""

    pathway_id: int
    canonical_id: str  # Reactome ID
    name: str
    mediating_genes: List[str] = Field(default_factory=list)
    mediating_proteins: List[str] = Field(default_factory=list)


class BiologicalProcessDetail(BaseModel):
    """Biological process (GO) detail."""

    process_id: int
    canonical_id: str  # GO ID
    name: str
    mediating_genes: List[str] = Field(default_factory=list)


class BiologicalAnalysisResponse(BaseModel):
    """Biological and pathway interpretation from verified knowledge graph."""

    compound: CompoundSummary
    target_protein_count: int
    associated_gene_count: int
    connected_pathways: List[BiologicalPathwaySummary] = Field(default_factory=list)
    connected_processes: List[BiologicalProcessDetail] = Field(default_factory=list)
    pathway_convergence: List[str] = Field(default_factory=list)
    process_convergence: List[str] = Field(default_factory=list)
    analysis_type: str = "descriptive_biological_analysis"
    scientific_note: str = (
        "Descriptive qualitative analysis derived from verified UniProt, Reactome, and Gene Ontology annotations. "
        "No statistical p-values or enrichment scores are fabricated."
    )


# ============================================================================
# Step 8: Evidence / Provenance Models
# ============================================================================


class EvidenceInsight(BaseModel):
    """Evidence-grounded finding distinguishing documented from graph-derived relationships."""

    finding: str
    relationship_type: str  # "DOCUMENTED" or "GRAPH_DERIVED"
    source_entity: str
    target_entity: str
    supporting_path: List[str] = Field(default_factory=list)
    evidence_records: List[EvidenceSummary] = Field(default_factory=list)


class CompoundEvidenceResponse(BaseModel):
    """Comprehensive evidence and provenance response."""

    compound: CompoundSummary
    total_documented_relationships: int
    total_graph_derived_relationships: int
    documented_evidence: List[EvidenceInsight] = Field(default_factory=list)
    graph_derived_insights: List[EvidenceInsight] = Field(default_factory=list)


# ============================================================================
# Step 9: Gemini Explanation Models
# ============================================================================


class GeminiExplanationRequest(BaseModel):
    """Optional request parameters for Gemini explanation."""

    focus_area: Optional[str] = None  # e.g. "pathways", "mechanism_of_action", "evidence"


class GeminiExplanationResponse(BaseModel):
    """Evidence-grounded natural language explanation generated by Gemini."""

    compound_name: str
    canonical_id: str
    explanation: str
    documented_findings: List[str] = Field(default_factory=list)
    graph_derived_findings: List[str] = Field(default_factory=list)
    evidence_citations: List[str] = Field(default_factory=list)
    scientific_limitations: str
    model_used: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
