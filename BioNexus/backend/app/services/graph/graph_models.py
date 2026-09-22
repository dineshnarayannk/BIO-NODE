"""Graph data models and response schemas for BioNexus Knowledge Graph."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from ...schemas.compound import CompoundSummary


class GraphEvidence(BaseModel):
    """Grounding evidence attached to a biological graph edge."""

    id: int
    source_database: str
    source_record_id: Optional[str] = None
    evidence_type: Optional[str] = None
    confidence: Optional[float] = None
    source_url: Optional[str] = None
    retrieved_at: Optional[datetime] = None


class GraphNode(BaseModel):
    """Node in the BioNexus biological knowledge graph."""

    id: str  # e.g. "compound:2712", "protein:1", "gene:1"
    db_id: int
    canonical_id: str
    name: str
    entity_type: str  # "compound", "protein", "gene", "pathway", "biological_process"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Directed edge in the BioNexus biological knowledge graph."""

    id: str  # e.g. "rel:44"
    source: str  # source node id
    target: str  # target node id
    relationship_type: str  # "targets", "encoded_by", "participates_in", "associated_with"
    relationship_id: int
    is_documented: bool = True
    evidence: List[GraphEvidence] = Field(default_factory=list)


class GraphStatistics(BaseModel):
    """Graph summary metrics."""

    node_count: int = 0
    edge_count: int = 0
    node_types: Dict[str, int] = Field(default_factory=dict)
    relationship_types: Dict[str, int] = Field(default_factory=dict)
    connected_components: int = 0


class CompoundGraphResponse(BaseModel):
    """Structured graph response suitable for Cytoscape.js biological visualization."""

    compound: Optional[CompoundSummary] = None
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    statistics: GraphStatistics = Field(default_factory=GraphStatistics)
