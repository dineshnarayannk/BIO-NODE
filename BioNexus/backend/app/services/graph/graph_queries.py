"""Graph query services for retrieving compound subgraphs and whole-network statistics."""

import logging
from typing import Optional
import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...db.models import Compound
from .graph_builder import (
    build_compound_graph,
    build_full_knowledge_graph,
    get_graph_statistics,
    graph_to_response,
)
from .graph_models import CompoundGraphResponse, GraphStatistics

logger = logging.getLogger("bionexus.graph.queries")


def _find_compound(db: Session, compound_id: str) -> Optional[Compound]:
    """Helper to query compound by numeric primary key or canonical_id."""
    if compound_id.isdigit():
        c = db.execute(select(Compound).where(Compound.id == int(compound_id))).scalar_one_or_none()
        if c:
            return c
    return db.execute(select(Compound).where(Compound.canonical_id == compound_id)).scalar_one_or_none()


def get_compound_graph_by_id(
    db: Session,
    compound_id: str,
) -> Optional[CompoundGraphResponse]:
    """Retrieve the full biological knowledge graph for a single compound as a structured response."""
    compound = _find_compound(db, compound_id)
    if not compound:
        return None

    G = build_compound_graph(db, compound)
    return graph_to_response(G, compound=compound)


def get_compound_subgraph(
    db: Session,
    compound_id: str,
) -> Optional[nx.DiGraph]:
    """Retrieve raw NetworkX DiGraph for a specific compound."""
    compound = _find_compound(db, compound_id)
    if not compound:
        return None
    return build_compound_graph(db, compound)


def get_full_graph_statistics(db: Session) -> GraphStatistics:
    """Compute overall graph metrics across the entire database knowledge graph."""
    G = build_full_knowledge_graph(db)
    return get_graph_statistics(G)
