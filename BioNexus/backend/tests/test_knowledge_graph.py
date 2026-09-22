"""Unit and integration tests for Step 5: Knowledge Graph Construction."""

import networkx as nx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.models import (
    Base,
    Compound,
)
from app.db.session import get_db
from app.main import app
from app.services.graph.graph_builder import (
    build_compound_graph,
    build_full_knowledge_graph,
    get_graph_statistics,
    graph_to_response,
)
from app.services.graph.graph_queries import (
    get_compound_graph_by_id,
    get_compound_subgraph,
    get_full_graph_statistics,
)
from app.services.ingestion.pipeline import run_biological_integration_pipeline

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db():
    """Create a pristine in-memory SQLite database for graph testing."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_client(test_db):
    """FastAPI TestClient with test database override."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_compound_graph_construction(test_db):
    """Test building a NetworkX DiGraph for a single natural compound."""
    # 1. Seed compound
    compound = Compound(
        name="Doxorubicin",
        canonical_id="SM_31",
        pubchem_cid=31703,
        smiles="OCC(=O)...",
        molecular_weight=543.52,
    )
    test_db.add(compound)
    test_db.commit()

    # 2. Run biological integration pipeline
    run_biological_integration_pipeline(test_db)

    # 3. Build compound graph
    G = build_compound_graph(test_db, compound)
    assert isinstance(G, nx.DiGraph)

    # Verify nodes and metadata
    compound_node_id = f"compound:{compound.id}"
    assert G.has_node(compound_node_id)
    c_data = G.nodes[compound_node_id]
    assert c_data["name"] == "Doxorubicin"
    assert c_data["canonical_id"] == "SM_31"
    assert c_data["entity_type"] == "compound"
    assert c_data["metadata"]["pubchem_cid"] == 31703

    # Verify protein node exists
    protein_nodes = [n for n, d in G.nodes(data=True) if d.get("entity_type") == "protein"]
    assert len(protein_nodes) >= 1

    # Verify edges and evidence
    assert G.number_of_edges() >= 1
    for u, v, data in G.edges(data=True):
        assert "relationship_type" in data
        assert "is_documented" in data
        assert data["is_documented"] is True


def test_graph_statistics(test_db):
    """Test graph metrics calculation."""
    compound = Compound(name="Doxorubicin", canonical_id="SM_31")
    test_db.add(compound)
    test_db.commit()
    run_biological_integration_pipeline(test_db)

    G = build_compound_graph(test_db, compound)
    stats = get_graph_statistics(G)

    assert stats.node_count == G.number_of_nodes()
    assert stats.edge_count == G.number_of_edges()
    assert "compound" in stats.node_types
    assert "protein" in stats.node_types
    assert "gene" in stats.node_types
    assert "pathway" in stats.node_types
    assert "biological_process" in stats.node_types
    assert "targets" in stats.relationship_types
    assert stats.connected_components >= 1


def test_empty_compound_graph(test_db):
    """Test building a graph for an orphan compound with no targets."""
    compound = Compound(name="Isolated Compound", canonical_id="SM_ORPHAN_99")
    test_db.add(compound)
    test_db.commit()

    G = build_compound_graph(test_db, compound)
    assert G.number_of_nodes() == 1
    assert G.number_of_edges() == 0

    stats = get_graph_statistics(G)
    assert stats.node_count == 1
    assert stats.edge_count == 0
    assert stats.node_types.get("compound") == 1
    assert stats.connected_components == 1


def test_full_knowledge_graph_construction(test_db):
    """Test full multi-compound knowledge graph construction from database."""
    c1 = Compound(name="Doxorubicin", canonical_id="SM_31")
    c2 = Compound(name="Rapamycin", canonical_id="SM_67")
    c3 = Compound(name="Capreomycin", canonical_id="SM_46")
    test_db.add_all([c1, c2, c3])
    test_db.commit()

    run_biological_integration_pipeline(test_db)

    full_stats = get_full_graph_statistics(test_db)
    assert full_stats.node_count > 0
    assert full_stats.edge_count > 0
    assert full_stats.node_types.get("compound", 0) >= 3
    assert full_stats.node_types.get("protein", 0) >= 4


def test_compound_graph_api_endpoint(test_client, test_db):
    """Test GET /api/compounds/{compound_id}/graph endpoint."""
    compound = Compound(name="Doxorubicin", canonical_id="SM_31", smiles="OCC(=O)...", molecular_weight=543.52)
    test_db.add(compound)
    test_db.commit()
    run_biological_integration_pipeline(test_db)

    # 1. Success query by numeric ID
    res = test_client.get(f"/api/compounds/{compound.id}/graph")
    assert res.status_code == 200
    data = res.json()

    assert data["compound"]["name"] == "Doxorubicin"
    assert len(data["nodes"]) >= 1
    assert len(data["edges"]) >= 1
    assert data["statistics"]["node_count"] == len(data["nodes"])
    assert data["statistics"]["edge_count"] == len(data["edges"])

    # Check evidence attached to edges
    target_edges = [e for e in data["edges"] if e["relationship_type"] == "targets"]
    assert len(target_edges) >= 1
    assert len(target_edges[0]["evidence"]) >= 1
    assert target_edges[0]["evidence"][0]["source_record_id"] == "11094008"

    # 2. Success query by canonical ID
    res_canon = test_client.get("/api/compounds/SM_31/graph")
    assert res_canon.status_code == 200
    assert res_canon.json()["compound"]["canonical_id"] == "SM_31"

    # 3. 404 for non-existent compound
    res_404 = test_client.get("/api/compounds/999999/graph")
    assert res_404.status_code == 404
