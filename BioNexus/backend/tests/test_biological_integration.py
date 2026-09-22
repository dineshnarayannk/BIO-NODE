"""Unit and integration tests for Step 4: Biological Data Integration."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.models import (
    Base,
    BiologicalProcess,
    Compound,
    Evidence,
    Gene,
    Pathway,
    Protein,
    Relationship,
)
from app.db.session import get_db
from app.main import app
from app.services.ingestion.compound_targets import ingest_compound_target_interaction
from app.services.ingestion.gene_ontology import ingest_process_record
from app.services.ingestion.pipeline import run_biological_integration_pipeline
from app.services.ingestion.reactome import ingest_pathway_record
from app.services.ingestion.uniprot import ingest_protein_record
from app.services.normalization import (
    normalize_gene_symbol,
    normalize_go_id,
    normalize_reactome_id,
    normalize_uniprot_id,
)

# SQLite in-memory test database fixture
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db():
    """Create a pristine in-memory SQLite test database for isolated testing."""
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
    """FastAPI TestClient with overridden get_db dependency."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ============================================================================
# Phase B: Identifier Normalization Unit Tests
# ============================================================================


def test_normalize_uniprot_id():
    """Test canonical UniProt accession validation and prefix normalization."""
    assert normalize_uniprot_id("P11388") == "P11388"
    assert normalize_uniprot_id("uniprot:p00533") == "P00533"
    assert normalize_uniprot_id("UP:Q08209") == "Q08209"
    assert normalize_uniprot_id("  P0A7R3  ") == "P0A7R3"

    # Invalid IDs
    assert normalize_uniprot_id("") is None
    assert normalize_uniprot_id(None) is None
    assert normalize_uniprot_id("INVALID_ID_TOO_LONG") is None
    assert normalize_uniprot_id("12345") is None


def test_normalize_gene_symbol():
    """Test gene symbol validation and formatting."""
    assert normalize_gene_symbol("top2a") == "TOP2A"
    assert normalize_gene_symbol("EGFR") == "EGFR"
    assert normalize_gene_symbol("hgnc:TP53") == "TP53"
    assert normalize_gene_symbol("gene:rpsL") == "RPSL"

    # Invalid symbols
    assert normalize_gene_symbol("") is None
    assert normalize_gene_symbol(None) is None
    assert normalize_gene_symbol("$$$$") is None


def test_normalize_reactome_id():
    """Test Reactome identifier normalization."""
    assert normalize_reactome_id("R-HSA-5693532") == "R-HSA-5693532"
    assert normalize_reactome_id("reactome:r-hsa-165159") == "R-HSA-165159"
    assert normalize_reactome_id("R-MMU-123456") == "R-MMU-123456"

    # Invalid Reactome IDs
    assert normalize_reactome_id("") is None
    assert normalize_reactome_id(None) is None
    assert normalize_reactome_id("KEGG:00010") is None


def test_normalize_go_id():
    """Test Gene Ontology identifier normalization."""
    assert normalize_go_id("GO:0006259") == "GO:0006259"
    assert normalize_go_id("go:0006915") == "GO:0006915"
    assert normalize_go_id("6259") == "GO:0006259"
    assert normalize_go_id("0008285") == "GO:0008285"

    # Invalid GO IDs
    assert normalize_go_id("") is None
    assert normalize_go_id(None) is None
    assert normalize_go_id("NOT_A_GO_ID") is None


# ============================================================================
# Phase C: Ingestion Services & Deduplication Tests
# ============================================================================


def test_uniprot_ingestion_and_deduplication(test_db):
    """Test protein and gene entity creation with duplicate prevention."""
    protein1, gene1, rel1 = ingest_protein_record(
        test_db,
        uniprot_id="P11388",
        name="DNA topoisomerase 2-alpha",
        gene_symbol="TOP2A",
        gene_name="Topoisomerase II Alpha",
    )
    test_db.commit()

    assert protein1 is not None
    assert protein1.canonical_id == "P11388"
    assert gene1 is not None
    assert gene1.canonical_id == "TOP2A"
    assert rel1 is not None
    assert rel1.relationship_type == "encoded_by"

    # Ingest duplicate protein record
    protein2, gene2, rel2 = ingest_protein_record(
        test_db,
        uniprot_id="P11388",
        name="DNA topoisomerase 2-alpha (duplicate)",
        gene_symbol="TOP2A",
    )
    test_db.commit()

    assert protein2.id == protein1.id
    assert gene2.id == gene1.id
    # Ensure total protein count in table remains 1
    assert test_db.query(Protein).count() == 1
    assert test_db.query(Gene).count() == 1
    assert test_db.query(Relationship).count() == 1


def test_reactome_ingestion(test_db):
    """Test pathway entity creation and gene-to-pathway relationship."""
    pathway, rel = ingest_pathway_record(
        test_db,
        reactome_id="R-HSA-5693532",
        name="DNA Double-Strand Break Repair",
        gene_symbol="TOP2A",
    )
    test_db.commit()

    assert pathway is not None
    assert pathway.canonical_id == "R-HSA-5693532"
    assert rel is not None
    assert rel.relationship_type == "participates_in"
    assert test_db.query(Pathway).count() == 1


def test_gene_ontology_ingestion(test_db):
    """Test biological process entity creation and gene-to-process relationship."""
    process, rel = ingest_process_record(
        test_db,
        go_id="GO:0006259",
        name="DNA metabolic process",
        gene_symbol="TOP2A",
    )
    test_db.commit()

    assert process is not None
    assert process.canonical_id == "GO:0006259"
    assert rel is not None
    assert rel.relationship_type == "associated_with"
    assert test_db.query(BiologicalProcess).count() == 1


def test_compound_target_and_evidence_ingestion(test_db):
    """Test compound target relationship and PubMed evidence grounding."""
    # Seed compound and protein
    compound = Compound(name="Doxorubicin", canonical_id="SM_31")
    protein = Protein(name="DNA topoisomerase 2-alpha", canonical_id="P11388")
    test_db.add_all([compound, protein])
    test_db.commit()

    rel, ev = ingest_compound_target_interaction(
        test_db,
        compound_identifier="SM_31",
        uniprot_id="P11388",
        source_database="PubMed",
        source_record_id="11094008",
        evidence_type="curated_literature",
        confidence=None,
    )
    test_db.commit()

    assert rel is not None
    assert rel.relationship_type == "targets"
    assert rel.source_id == compound.id
    assert rel.target_id == protein.id

    assert ev is not None
    assert ev.source_record_id == "11094008"
    assert ev.confidence is None  # Never fabricated
    assert ev.source_url == "https://pubmed.ncbi.nlm.nih.gov/11094008/"


# ============================================================================
# Phase G: API Integration Endpoints Tests
# ============================================================================


def test_compound_biological_endpoints(test_client, test_db):
    """Test complete end-to-end traversal from Compound to Process via API."""
    # 1. Seed a compound
    compound = Compound(name="Doxorubicin", canonical_id="SM_31", smiles="CC(=O)C1...", molecular_weight=543.5)
    test_db.add(compound)
    test_db.commit()

    # 2. Run full integration pipeline
    summary = run_biological_integration_pipeline(test_db)
    assert summary["uniprot"]["proteins_created"] > 0

    # 3. Test GET /api/compounds/{compound_id}
    res = test_client.get(f"/api/compounds/{compound.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["compound"]["name"] == "Doxorubicin"
    assert len(data["target_proteins"]) >= 1
    assert data["target_proteins"][0]["canonical_id"] == "P11388"
    assert len(data["associated_genes"]) >= 1
    assert data["associated_genes"][0]["canonical_id"] == "TOP2A"
    assert len(data["pathways"]) >= 1
    assert len(data["biological_processes"]) >= 1
    assert len(data["evidence"]) >= 1
    assert data["evidence"][0]["source_record_id"] == "11094008"

    # 4. Test GET /api/compounds/{compound_id}/proteins
    res_p = test_client.get(f"/api/compounds/{compound.id}/proteins")
    assert res_p.status_code == 200
    assert len(res_p.json()) >= 1
    assert res_p.json()[0]["canonical_id"] == "P11388"

    # 5. Test GET /api/compounds/{compound_id}/genes
    res_g = test_client.get(f"/api/compounds/{compound.id}/genes")
    assert res_g.status_code == 200
    assert any(g["canonical_id"] == "TOP2A" for g in res_g.json())

    # 6. Test GET /api/compounds/{compound_id}/pathways
    res_pw = test_client.get(f"/api/compounds/{compound.id}/pathways")
    assert res_pw.status_code == 200
    assert any("DNA Double-Strand Break Repair" in pw["name"] for pw in res_pw.json())

    # 7. Test GET /api/compounds/{compound_id}/processes
    res_bp = test_client.get(f"/api/compounds/{compound.id}/processes")
    assert res_bp.status_code == 200
    assert any("DNA metabolic process" in bp["name"] for bp in res_bp.json())

    # 8. Test GET /api/compounds/{compound_id}/evidence
    res_ev = test_client.get(f"/api/compounds/{compound.id}/evidence")
    assert res_ev.status_code == 200
    assert any(ev["source_record_id"] == "11094008" for ev in res_ev.json())

    # 9. Test 404 for non-existent compound
    res_404 = test_client.get("/api/compounds/999999")
    assert res_404.status_code == 404
