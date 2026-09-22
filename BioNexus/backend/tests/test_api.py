import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.models import (
    Base,
    Compound,
    Protein,
    Gene,
    Pathway,
    BiologicalProcess,
    Relationship,
    Evidence,
)
from app.db.session import get_db

# Create an in-memory SQLite database with StaticPool for test suite isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh database tables for each test and clean up after."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_root_endpoint(client):
    """Verify root endpoint returns basic API meta."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "BioNexus API"
    assert "docs" in data


def test_health_endpoint(client):
    """Verify GET /api/health satisfies service and database status reporting."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["service"] == "BioNexus API"
    assert "database" in data


def test_compound_search_empty_structure(client):
    """Verify GET /api/compounds/search returns expected empty scaffold structure when DB is empty."""
    response = client.get("/api/compounds/search?q=curcumin")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "curcumin"
    assert data["total_matches"] == 0
    assert data["items"] == []
    assert "message" in data


def test_compound_search_validation(client):
    """Verify GET /api/compounds/search validates empty query param."""
    response = client.get("/api/compounds/search?q=")
    assert response.status_code == 422


def test_compound_search_with_data(client, db_session):
    """Verify compound search retrieves matched compounds from database."""
    test_compound = Compound(
        name="Capreomycin",
        canonical_id="SMR00001",
        pubchem_cid=3000502,
        smiles="CC1=C(NC(=O)C2CCCN2C(=O)...)C",
        molecular_weight=668.7,
    )
    db_session.add(test_compound)
    db_session.commit()

    response = client.get("/api/compounds/search?q=capreo")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "capreo"
    assert data["total_matches"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Capreomycin"
    assert data["items"][0]["molecular_weight"] == 668.7


def test_database_schema_models(db_session):
    """Verify all 7 database models and relationship/evidence linkages work."""
    # 1. Compound
    compound = Compound(name="Curcumin", canonical_id="CHEMBL25", molecular_weight=368.38)
    # 2. Protein
    protein = Protein(name="Epidermal Growth Factor Receptor", canonical_id="P00533")
    # 3. Gene
    gene = Gene(name="EGFR", canonical_id="NCBI_1956")
    # 4. Pathway
    pathway = Pathway(name="Signaling by EGFR", canonical_id="R-HSA-177929")
    # 5. Biological Process
    process = BiologicalProcess(name="Apoptotic process", canonical_id="GO:0006915")

    db_session.add_all([compound, protein, gene, pathway, process])
    db_session.commit()

    assert compound.id is not None
    assert protein.id is not None
    assert gene.id is not None
    assert pathway.id is not None
    assert process.id is not None

    # 6. Relationship
    rel = Relationship(
        source_type="compound",
        source_id=compound.id,
        relationship_type="inhibits",
        target_type="protein",
        target_id=protein.id,
    )
    db_session.add(rel)
    db_session.commit()
    assert rel.id is not None

    # 7. Evidence
    evidence = Evidence(
        relationship_id=rel.id,
        source_database="PubMed",
        source_record_id="28479212",
        evidence_type="experimental_assay",
        confidence=0.92,
        source_url="https://pubmed.ncbi.nlm.nih.gov/28479212/",
    )
    db_session.add(evidence)
    db_session.commit()
    assert evidence.id is not None

    # Verify relationship linkage
    assert len(rel.evidence_records) == 1
    assert rel.evidence_records[0].source_database == "PubMed"
