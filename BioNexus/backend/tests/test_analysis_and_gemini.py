"""Tests for Steps 6-9: Graph Analysis, Biological Analysis, Provenance, and Gemini LLM Explanation."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.models import Base, Compound
from app.db.session import get_db
from app.main import app
from app.services.analysis.biological_analysis import analyze_compound_biology
from app.services.analysis.graph_analysis import analyze_compound_graph
from app.services.ingestion.pipeline import run_biological_integration_pipeline
from app.services.llm.gemini import generate_compound_explanation

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db():
    """Create in-memory SQLite database for analysis testing."""
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


def test_graph_analysis_service(test_db):
    """Step 6: Test computational graph analysis with NetworkX."""
    compound = Compound(name="Doxorubicin", canonical_id="SM_31", smiles="OCC(=O)...", molecular_weight=543.52)
    test_db.add(compound)
    test_db.commit()
    run_biological_integration_pipeline(test_db)

    analysis = analyze_compound_graph(test_db, compound)

    assert analysis.compound.name == "Doxorubicin"
    assert analysis.total_nodes >= 5
    assert analysis.total_edges >= 4
    assert len(analysis.central_nodes) >= 1
    assert any(cn.canonical_id == "TOP2A" for cn in analysis.central_nodes)

    # Check path traversals
    assert len(analysis.paths) >= 1
    path_types = [p.path_type for p in analysis.paths]
    assert "compound_to_protein" in path_types
    assert "compound_to_pathway" in path_types or "compound_to_biological_process" in path_types


def test_biological_analysis_service(test_db):
    """Step 7: Test biological interpretation and pathway mapping without fabricated statistics."""
    compound = Compound(name="Doxorubicin", canonical_id="SM_31")
    test_db.add(compound)
    test_db.commit()
    run_biological_integration_pipeline(test_db)

    bio_analysis = analyze_compound_biology(test_db, compound)

    assert bio_analysis.target_protein_count >= 1
    assert bio_analysis.associated_gene_count >= 1
    assert len(bio_analysis.connected_pathways) >= 1
    assert len(bio_analysis.connected_processes) >= 1
    assert "No statistical p-values" in bio_analysis.scientific_note


def test_gemini_fallback_explanation():
    """Step 9: Test Gemini grounded fallback explanation when API key is unconfigured."""
    context = {
        "compound": {"name": "Doxorubicin", "canonical_id": "SM_31", "molecular_weight": 543.52},
        "target_proteins": [{"name": "DNA topoisomerase 2-alpha", "canonical_id": "P11388"}],
        "associated_genes": [{"name": "TOP2A", "canonical_id": "TOP2A"}],
        "pathways": [{"name": "DNA Double-Strand Break Repair", "canonical_id": "R-HSA-5693532"}],
        "biological_processes": [{"name": "DNA metabolic process", "canonical_id": "GO:0006259"}],
        "evidence": [{"source_database": "PubMed", "source_record_id": "11094008"}],
    }

    import asyncio

    explanation = asyncio.run(generate_compound_explanation(context))

    assert explanation.compound_name == "Doxorubicin"
    assert "Doxorubicin" in explanation.explanation
    assert len(explanation.documented_findings) >= 1
    assert len(explanation.graph_derived_findings) >= 1
    assert len(explanation.evidence_citations) >= 1
    assert "scientific_limitations" in explanation.model_dump()


def test_analysis_and_explanation_endpoints(test_client, test_db):
    """Test full API endpoints for Steps 6, 7, 8, and 9."""
    compound = Compound(name="Doxorubicin", canonical_id="SM_31", smiles="OCC(=O)...", molecular_weight=543.52)
    test_db.add(compound)
    test_db.commit()
    run_biological_integration_pipeline(test_db)

    # 1. GET /api/compounds/{compound_id}/analysis
    res_analysis = test_client.get(f"/api/compounds/{compound.id}/analysis")
    assert res_analysis.status_code == 200
    data_a = res_analysis.json()
    assert data_a["compound"]["name"] == "Doxorubicin"
    assert len(data_a["central_nodes"]) >= 1

    # 2. GET /api/compounds/{compound_id}/biological-analysis
    res_bio = test_client.get(f"/api/compounds/{compound.id}/biological-analysis")
    assert res_bio.status_code == 200
    data_b = res_bio.json()
    assert len(data_b["connected_pathways"]) >= 1
    assert len(data_b["connected_processes"]) >= 1

    # 3. GET /api/compounds/{compound_id}/provenance
    res_prov = test_client.get(f"/api/compounds/{compound.id}/provenance")
    assert res_prov.status_code == 200
    data_p = res_prov.json()
    assert data_p["total_documented_relationships"] >= 1
    assert data_p["total_graph_derived_relationships"] >= 1
    assert data_p["documented_evidence"][0]["relationship_type"] == "DOCUMENTED"

    # 4. POST /api/compounds/{compound_id}/explanation
    res_exp = test_client.post(f"/api/compounds/{compound.id}/explanation", json={})
    assert res_exp.status_code == 200
    data_e = res_exp.json()
    assert data_e["compound_name"] == "Doxorubicin"
    assert len(data_e["explanation"]) > 0

    # 5. 404 for non-existent compound
    res_404 = test_client.get("/api/compounds/999999/analysis")
    assert res_404.status_code == 404
