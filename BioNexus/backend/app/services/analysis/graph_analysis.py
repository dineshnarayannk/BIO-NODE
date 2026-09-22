"""Computational graph analysis service using NetworkX.

Computes degree/betweenness centrality, path traversals from compound to biological entities,
and convergence points using neutral, objective terminology.
"""

from collections import Counter
import logging
from typing import Any, Dict, List, Optional
import networkx as nx
from sqlalchemy.orm import Session
from ...db.models import Compound
from ...schemas.analysis import (
    CentralityScore,
    ConvergencePoint,
    GraphAnalysisResponse,
    GraphPath,
)
from ...schemas.compound import CompoundSummary
from ..graph.graph_builder import build_compound_graph

logger = logging.getLogger("bionexus.analysis.graph")


def analyze_compound_graph(
    db: Session,
    compound: Compound,
) -> GraphAnalysisResponse:
    """Perform computational network analysis on a compound-centric knowledge graph."""
    G = build_compound_graph(db, compound)
    node_count = G.number_of_nodes()
    edge_count = G.number_of_edges()

    compound_summary = CompoundSummary(
        id=str(compound.id),
        name=compound.name,
        canonical_id=compound.canonical_id,
        pubchem_cid=compound.pubchem_cid,
        smiles=compound.smiles,
        molecular_weight=compound.molecular_weight,
        source=f"StreptomeDB (canonical_id: {compound.canonical_id})",
    )

    if node_count <= 1:
        return GraphAnalysisResponse(
            compound=compound_summary,
            total_nodes=node_count,
            total_edges=edge_count,
            central_nodes=[],
            convergence_points=[],
            paths=[],
            relationship_distribution={},
            connected_components=1 if node_count == 1 else 0,
            summary=f"Compound '{compound.name}' has no documented biological target connections in the database.",
        )

    # 1. Degree Centrality & Betweenness Centrality
    deg_centrality = nx.degree_centrality(G)
    # Betweenness on directed graph
    between_centrality = nx.betweenness_centrality(G, normalized=True)

    central_nodes: List[CentralityScore] = []
    for node_id, d_score in sorted(deg_centrality.items(), key=lambda x: (x[1], between_centrality.get(x[0], 0)), reverse=True):
        node_data = G.nodes[node_id]
        b_score = between_centrality.get(node_id, 0.0)

        # Neutral descriptive label
        if d_score >= 0.5 or b_score >= 0.2:
            label = "high centrality node"
        elif d_score >= 0.25:
            label = "highly connected node"
        else:
            label = "peripheral graph node"

        central_nodes.append(
            CentralityScore(
                node_id=node_id,
                db_id=node_data.get("db_id", 0),
                name=node_data.get("name", ""),
                canonical_id=node_data.get("canonical_id", ""),
                entity_type=node_data.get("entity_type", "unknown"),
                degree_centrality=round(d_score, 4),
                betweenness_centrality=round(b_score, 4),
                connectivity_label=label,
            )
        )

    # 2. Path Traversals from Compound
    compound_node_id = f"compound:{compound.id}"
    paths: List[GraphPath] = []

    for target_node in G.nodes():
        if target_node == compound_node_id:
            continue
        try:
            if nx.has_path(G, compound_node_id, target_node):
                all_simple_paths = list(nx.all_simple_paths(G, compound_node_id, target_node, cutoff=5))
                for p in all_simple_paths:
                    target_type = G.nodes[target_node].get("entity_type", "unknown")
                    path_names = [G.nodes[n].get("name", n) for n in p]
                    length = len(p) - 1

                    path_type_label = f"compound_to_{target_type}"
                    paths.append(
                        GraphPath(
                            path_type=path_type_label,
                            nodes=p,
                            node_names=path_names,
                            length=length,
                            is_documented_direct=(length == 1),
                        )
                    )
        except Exception as e:
            logger.debug(f"Path query error between {compound_node_id} and {target_node}: {e}")

    # 3. Convergence Detection (Nodes with in-degree > 1 in the compound graph)
    convergence_points: List[ConvergencePoint] = []
    for node_id in G.nodes():
        in_deg = G.in_degree(node_id)
        if in_deg > 1:
            predecessors = list(G.predecessors(node_id))
            pred_names = [G.nodes[pred].get("name", pred) for pred in predecessors]
            node_data = G.nodes[node_id]
            convergence_points.append(
                ConvergencePoint(
                    node_id=node_id,
                    db_id=node_data.get("db_id", 0),
                    name=node_data.get("name", ""),
                    canonical_id=node_data.get("canonical_id", ""),
                    entity_type=node_data.get("entity_type", "unknown"),
                    in_degree=in_deg,
                    incoming_sources=pred_names,
                )
            )

    # 4. Relationship Distribution
    rel_dist: Counter = Counter()
    for _, _, data in G.edges(data=True):
        rtype = data.get("relationship_type", "unknown")
        rel_dist[rtype] += 1

    conn_components = nx.number_weakly_connected_components(G)

    # Summary string
    summary = (
        f"Graph contains {node_count} nodes and {edge_count} directed edges. "
        f"Compound connects to {len([n for n in central_nodes if n.entity_type == 'protein'])} target protein(s) "
        f"and spans {len([n for n in central_nodes if n.entity_type == 'pathway'])} pathway(s) and "
        f"{len([n for n in central_nodes if n.entity_type == 'biological_process'])} biological process(es)."
    )

    return GraphAnalysisResponse(
        compound=compound_summary,
        total_nodes=node_count,
        total_edges=edge_count,
        central_nodes=central_nodes,
        convergence_points=convergence_points,
        paths=paths,
        relationship_distribution=dict(rel_dist),
        connected_components=conn_components,
        summary=summary,
    )
