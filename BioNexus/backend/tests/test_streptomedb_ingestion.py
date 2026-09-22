import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Compound
from app.services.ingestion.streptomedb import (
    StreptomeDBIngester,
    NormalizedCompound,
    IngestionSummary,
)

SAMPLE_SDF_BLOCK = """Capreomycin
 OpenBabel09132418383D 

 47 48  0  0  1  0  0  0  0  0999 V2000
    4.3215   -6.3370    7.6730 N   0  0  0  0  0  0  0  0  0  0  0  0
M  END
>  <canonical_smiles>
NCCC[C@@H](CC(=O)NC[C@@H]1NC(=O)[C@H](CO)NC(=O)[C@@H](N)CNC(=O)C(NC(=O)/C(=C\\NC(=O)N)/NC1=O)C1CCN=C(N1)N)N

>  <name>
Capreomycin

>  <compound_id>
46

>  <molwt>
668.70586

>  <HBD>
14

>  <HBA>
22

>  <rotatable bonds>
12

>  <pubchem cid>
135483770

>  <organisms>
Streptomyces capreolus

>  <pmids>
12909358

>  <activities>
Antitubercular

>  <synthesizing routes>
non-ribosomal peptide
$$$$
"""

SAMPLE_SDF_BLOCK_MISSING_FIELDS = """Unknown Metabolite
 OpenBabel

 10 10  0  0  0  0  0  0  0  0999 V2000
M  END
>  <compound_id>
99999

>  <pubchem cid>
None

>  <molwt>
invalid_float
$$$$
"""


@pytest.fixture(scope="function")
def test_db_session():
    """Isolated SQLite database session for ingestion unit tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_parse_sdf_block():
    """Verify property tag extraction from SDF text block."""
    props = StreptomeDBIngester.parse_sdf_block(SAMPLE_SDF_BLOCK)
    assert props["_title"] == "Capreomycin"
    assert props["name"] == "Capreomycin"
    assert props["compound_id"] == "46"
    assert props["pubchem cid"] == "135483770"
    assert props["molwt"] == "668.70586"
    assert "NCCC" in props["canonical_smiles"]
    assert props["organisms"] == "Streptomyces capreolus"


def test_normalize_record_complete():
    """Verify clean normalization of complete SDF record."""
    props = StreptomeDBIngester.parse_sdf_block(SAMPLE_SDF_BLOCK)
    norm = StreptomeDBIngester.normalize_record(props)

    assert norm is not None
    assert norm.name == "Capreomycin"
    assert norm.canonical_id == "SM_46"
    assert norm.pubchem_cid == 135483770
    assert norm.molecular_weight == 668.70586
    assert norm.smiles.startswith("NCCC")
    assert norm.raw_metadata["source_database"] == "StreptomeDB"
    assert norm.raw_metadata["organisms"] == "Streptomyces capreolus"


def test_normalize_record_missing_fields():
    """Verify robust handling of 'None' strings and invalid numeric values."""
    props = StreptomeDBIngester.parse_sdf_block(SAMPLE_SDF_BLOCK_MISSING_FIELDS)
    norm = StreptomeDBIngester.normalize_record(props)

    assert norm is not None
    assert norm.canonical_id == "SM_99999"
    assert norm.name == "Unknown Metabolite"
    assert norm.pubchem_cid is None
    assert norm.molecular_weight is None
    assert norm.smiles is None


def test_normalize_record_no_id():
    """Verify record without compound_id is skipped safely."""
    norm = StreptomeDBIngester.normalize_record({"name": "NoIDCompound"})
    assert norm is None


def test_ingestion_insertion_and_update(test_db_session):
    """Verify batch insertion and update deduplication in database."""
    ingester = StreptomeDBIngester()
    summary = IngestionSummary(file_path="memory_test")

    props = StreptomeDBIngester.parse_sdf_block(SAMPLE_SDF_BLOCK)
    norm1 = StreptomeDBIngester.normalize_record(props)
    assert norm1 is not None

    # First insert
    ingester._process_batch(test_db_session, [norm1], summary, dry_run=False)
    assert summary.records_inserted == 1
    assert summary.records_updated == 0

    # Query DB to verify
    stmt = select(Compound).where(Compound.canonical_id == "SM_46")
    c = test_db_session.execute(stmt).scalar_one_or_none()
    assert c is not None
    assert c.name == "Capreomycin"
    assert c.pubchem_cid == 135483770

    # Modify and re-process (update)
    norm1_modified = NormalizedCompound(
        name="Capreomycin Sulfate",
        canonical_id="SM_46",
        pubchem_cid=135483770,
        smiles=norm1.smiles,
        molecular_weight=768.8,
    )
    ingester._process_batch(test_db_session, [norm1_modified], summary, dry_run=False)
    assert summary.records_updated == 1

    # Verify update in DB
    test_db_session.expire_all()
    c_updated = test_db_session.execute(stmt).scalar_one()
    assert c_updated.name == "Capreomycin Sulfate"
    assert c_updated.molecular_weight == 768.8
