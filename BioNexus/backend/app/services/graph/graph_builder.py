"""NetworkX graph construction service for BioNexus Knowledge Graph.

Builds directed graph representations from verified TiDB Cloud entities,
relationships, and grounding evidence. Preserves strict distinction between
directly documented biological relationships and derived graph paths.
"""

from collections import Counter
import logging
from typing import Any, Dict, List, Optional
import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...db.models import (
    BiologicalProcess,
    Compound,
    Evidence,
    Gene,
    Pathway,
    Protein,
    Relationship,
)
from ...schemas.compound import CompoundSummary
from .graph_models import (
    CompoundGraphResponse,
    GraphEdge,
    GraphEvidence,
    GraphNode,
    GraphStatistics,
)

logger = logging.getLogger("bionexus.graph.builder")


def _node_key(entity_type: str, db_id: int) -> str:
    """Generate canonical graph node key."""
    return f"{entity_type.lower()}:{db_id}"


def build_compound_graph(
    db: Session,
    compound: Compound,
) -> nx.DiGraph:
    """Construct a NetworkX DiGraph for a specific natural compound.

    Traverses:
    Compound -> Targets -> Protein -> Encoded_by -> Gene -> Participates_in / Associated_with -> Pathway / BiologicalProcess
    Preserves all node attributes and edge evidence.
    """
    G = nx.DiGraph()

    # 1. Add Compound Node
    compound_key = _node_key("compound", compound.id)
    G.add_node(
        compound_key,
        db_id=compound.id,
        canonical_id=compound.canonical_id,
        name=compound.name,
        entity_type="compound",
        metadata={
            "pubchem_cid": compound.pubchem_cid,
            "smiles": compound.smiles,
            "molecular_weight": compound.molecular_weight,
        },
    )

    # 2. Query target protein relationships
    protein_rels = db.execute(
        select(Relationship).where(
            Relationship.source_type == "compound",
            Relationship.source_id == compound.id,
            Relationship.relationship_type == "targets",
            Relationship.target_type == "protein",
        )
    ).scalars().all()

    protein_ids = [rel.target_id for rel in protein_rels]
    rel_ids = [rel.id for rel in protein_rels]

    # Fetch evidence for compound -> protein relationships
    evidence_map: Dict[int, List[Evidence]] = {}
    if rel_ids:
        evidence_records = db.execute(
            select(Evidence).where(Evidence.relationship_id.in_(rel_ids))
        ).scalars().all()
        for ev in evidence_records:
            evidence_map.setdefault(ev.relationship_id, []).append(ev)

    # Fetch proteins
    if protein_ids:
        proteins = db.execute(
            select(Protein).where(Protein.id.in_(protein_ids))
        ).scalars().all()
        protein_dict = {p.id: p for p in proteins}

        for rel in protein_rels:
            p = protein_dict.get(rel.target_id)
            if not p:
                continue
            prot_key = _node_key("protein", p.id)
            if not G.has_node(prot_key):
                G.add_node(
                    prot_key,
                    db_id=p.id,
                    canonical_id=p.canonical_id,
                    name=p.name,
                    entity_type="protein",
                    metadata={},
                )

            # Edge evidence
            ev_list = [
                GraphEvidence(
                    id=e.id,
                    source_database=e.source_database,
                    source_record_id=e.source_record_id,
                    evidence_type=e.evidence_type,
                    confidence=e.confidence,
                    source_url=e.source_url,
                    retrieved_at=e.retrieved_at,
                )
                for e in evidence_map.get(rel.id, [])
            ]

            G.add_edge(
                compound_key,
                prot_key,
                id=f"rel:{rel.id}",
                relationship_id=rel.id,
                relationship_type=rel.relationship_type,
                is_documented=True,
                evidence=ev_list,
            )

    # 3. Query protein -> gene relationships
    gene_ids: List[int] = []
    if protein_ids:
        gene_rels = db.execute(
            select(Relationship).where(
                Relationship.source_type == "protein",
                Relationship.source_id.in_(protein_ids),
                Relationship.relationship_type == "encoded_by",
                Relationship.target_type == "gene",
            )
        ).scalars().all()

        gene_ids = [rel.target_id for rel in gene_rels]
        if gene_ids:
            genes = db.execute(
                select(Gene).where(Gene.id.in_(gene_ids))
            ).scalars().all()
            gene_dict = {g.id: g for g in genes}

            for rel in gene_rels:
                g = gene_dict.get(rel.target_id)
                if not g:
                    continue
                gene_key = _node_key("gene", g.id)
                if not G.has_node(gene_key):
                    G.add_node(
                        gene_key,
                        db_id=g.id,
                        canonical_id=g.canonical_id,
                        name=g.name,
                        entity_type="gene",
                        metadata={},
                    )

                prot_key = _node_key("protein", rel.source_id)
                G.add_edge(
                    prot_key,
                    gene_key,
                    id=f"rel:{rel.id}",
                    relationship_id=rel.id,
                    relationship_type=rel.relationship_type,
                    is_documented=True,
                    evidence=[],
                )

    # 4. Query gene -> pathway relationships
    if gene_ids:
        pathway_rels = db.execute(
            select(Relationship).where(
                Relationship.source_type == "gene",
                Relationship.source_id.in_(gene_ids),
                Relationship.relationship_type == "participates_in",
                Relationship.target_type == "pathway",
            )
        ).scalars().all()

        pathway_ids = [rel.target_id for rel in pathway_rels]
        if pathway_ids:
            pathways = db.execute(
                select(Pathway).where(Pathway.id.in_(pathway_ids))
            ).scalars().all()
            pathway_dict = {pw.id: pw for pw in pathways}

            for rel in pathway_rels:
                pw = pathway_dict.get(rel.target_id)
                if not pw:
                    continue
                pw_key = _node_key("pathway", pw.id)
                if not G.has_node(pw_key):
                    G.add_node(
                        pw_key,
                        db_id=pw.id,
                        canonical_id=pw.canonical_id,
                        name=pw.name,
                        entity_type="pathway",
                        metadata={},
                    )

                gene_key = _node_key("gene", rel.source_id)
                G.add_edge(
                    gene_key,
                    pw_key,
                    id=f"rel:{rel.id}",
                    relationship_id=rel.id,
                    relationship_type=rel.relationship_type,
                    is_documented=True,
                    evidence=[],
                )

    # 5. Query gene -> biological process relationships
    if gene_ids:
        bp_rels = db.execute(
            select(Relationship).where(
                Relationship.source_type == "gene",
                Relationship.source_id.in_(gene_ids),
                Relationship.relationship_type == "associated_with",
                Relationship.target_type == "biological_process",
            )
        ).scalars().all()

        bp_ids = [rel.target_id for rel in bp_rels]
        if bp_ids:
            processes = db.execute(
                select(BiologicalProcess).where(BiologicalProcess.id.in_(bp_ids))
            ).scalars().all()
            bp_dict = {bp.id: bp for bp in processes}

            for rel in bp_rels:
                bp = bp_dict.get(rel.target_id)
                if not bp:
                    continue
                bp_key = _node_key("biological_process", bp.id)
                if not G.has_node(bp_key):
                    G.add_node(
                        bp_key,
                        db_id=bp.id,
                        canonical_id=bp.canonical_id,
                        name=bp.name,
                        entity_type="biological_process",
                        metadata={},
                    )

                gene_key = _node_key("gene", rel.source_id)
                G.add_edge(
                    gene_key,
                    bp_key,
                    id=f"rel:{rel.id}",
                    relationship_id=rel.id,
                    relationship_type=rel.relationship_type,
                    is_documented=True,
                    evidence=[],
                )

    return G


def build_full_knowledge_graph(db: Session) -> nx.DiGraph:
    """Build the entire BioNexus knowledge graph from all entities and relationships in TiDB."""
    G = nx.DiGraph()

    # Load all relationships
    relationships = db.execute(select(Relationship)).scalars().all()
    if not relationships:
        return G

    rel_ids = [r.id for r in relationships]
    evidences = db.execute(
        select(Evidence).where(Evidence.relationship_id.in_(rel_ids))
    ).scalars().all()

    evidence_map: Dict[int, List[Evidence]] = {}
    for ev in evidences:
        evidence_map.setdefault(ev.relationship_id, []).append(ev)

    # Entity maps
    compounds = {c.id: c for c in db.execute(select(Compound)).scalars().all()}
    proteins = {p.id: p for p in db.execute(select(Protein)).scalars().all()}
    genes = {g.id: g for g in db.execute(select(Gene)).scalars().all()}
    pathways = {pw.id: pw for pw in db.execute(select(Pathway)).scalars().all()}
    processes = {bp.id: bp for bp in db.execute(select(BiologicalProcess)).scalars().all()}

    entity_lookups = {
        "compound": compounds,
        "protein": proteins,
        "gene": genes,
        "pathway": pathways,
        "biological_process": processes,
    }

    for rel in relationships:
        source_dict = entity_lookups.get(rel.source_type.lower())
        target_dict = entity_lookups.get(rel.target_type.lower())

        if not source_dict or not target_dict:
            continue

        src_entity = source_dict.get(rel.source_id)
        tgt_entity = target_dict.get(rel.target_id)

        if not src_entity or not tgt_entity:
            continue

        src_key = _node_key(rel.source_type, src_entity.id)
        tgt_key = _node_key(rel.target_type, tgt_entity.id)

        if not G.has_node(src_key):
            G.add_node(
                src_key,
                db_id=src_entity.id,
                canonical_id=src_entity.canonical_id,
                name=src_entity.name,
                entity_type=rel.source_type.lower(),
                metadata={},
            )

        if not G.has_node(tgt_key):
            G.add_node(
                tgt_key,
                db_id=tgt_entity.id,
                canonical_id=tgt_entity.canonical_id,
                name=tgt_entity.name,
                entity_type=rel.target_type.lower(),
                metadata={},
            )

        ev_list = [
            GraphEvidence(
                id=e.id,
                source_database=e.source_database,
                source_record_id=e.source_record_id,
                evidence_type=e.evidence_type,
                confidence=e.confidence,
                source_url=e.source_url,
                retrieved_at=e.retrieved_at,
            )
            for e in evidence_map.get(rel.id, [])
        ]

        G.add_edge(
            src_key,
            tgt_key,
            id=f"rel:{rel.id}",
            relationship_id=rel.id,
            relationship_type=rel.relationship_type,
            is_documented=True,
            evidence=ev_list,
        )

    return G


def get_graph_statistics(G: nx.DiGraph) -> GraphStatistics:
    """Calculate summary statistics for a NetworkX knowledge graph."""
    node_count = G.number_of_nodes()
    edge_count = G.number_of_edges()

    node_types: Counter = Counter()
    for _, data in G.nodes(data=True):
        etype = data.get("entity_type", "unknown")
        node_types[etype] += 1

    rel_types: Counter = Counter()
    for _, _, data in G.edges(data=True):
        rtype = data.get("relationship_type", "unknown")
        rel_types[rtype] += 1

    connected_components = nx.number_weakly_connected_components(G) if node_count > 0 else 0

    return GraphStatistics(
        node_count=node_count,
        edge_count=edge_count,
        node_types=dict(node_types),
        relationship_types=dict(rel_types),
        connected_components=connected_components,
    )


def graph_to_response(
    G: nx.DiGraph,
    compound: Optional[Compound] = None,
) -> CompoundGraphResponse:
    """Convert a NetworkX graph into Cytoscape.js compatible response payload."""
    nodes: List[GraphNode] = []
    for node_id, data in G.nodes(data=True):
        nodes.append(
            GraphNode(
                id=node_id,
                db_id=data.get("db_id", 0),
                canonical_id=data.get("canonical_id", ""),
                name=data.get("name", ""),
                entity_type=data.get("entity_type", "unknown"),
                metadata=data.get("metadata", {}),
            )
        )

    edges: List[GraphEdge] = []
    for u, v, data in G.edges(data=True):
        edges.append(
            GraphEdge(
                id=data.get("id", f"edge:{u}->{v}"),
                source=u,
                target=v,
                relationship_type=data.get("relationship_type", "related_to"),
                relationship_id=data.get("relationship_id", 0),
                is_documented=data.get("is_documented", True),
                evidence=data.get("evidence", []),
            )
        )

    stats = get_graph_statistics(G)

    compound_summary = None
    if compound:
        compound_summary = CompoundSummary(
            id=str(compound.id),
            name=compound.name,
            canonical_id=compound.canonical_id,
            pubchem_cid=compound.pubchem_cid,
            smiles=compound.smiles,
            molecular_weight=compound.molecular_weight,
            source=f"StreptomeDB (canonical_id: {compound.canonical_id})",
        )

    return CompoundGraphResponse(
        compound=compound_summary,
        nodes=nodes,
        edges=edges,
        statistics=stats,
    )
