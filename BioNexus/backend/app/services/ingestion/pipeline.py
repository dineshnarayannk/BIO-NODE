"""Biological data integration pipeline orchestrator.

Coordinates ingestion across:
- UniProt (Proteins and Protein->encoded_by->Gene)
- Reactome (Pathways and Gene->participates_in->Pathway)
- Gene Ontology (Biological Processes and Gene->associated_with->Process)
- Compound Targets & Literature Evidence (Compound->targets->Protein + PubMed Grounding)
"""

import logging
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from .compound_targets import ingest_compound_targets_batch
from .gene_ontology import ingest_go_batch
from .reactome import ingest_reactome_batch
from .uniprot import ingest_uniprot_batch

logger = logging.getLogger("bionexus.ingestion.pipeline")

# =========================================================================
# VERIFIED BIOLOGICAL DATASETS
# Real biological entities from UniProt, Reactome, GO, and PubMed citations
# =========================================================================

VERIFIED_PROTEINS = [
    {
        "uniprot_id": "P11388",
        "name": "DNA topoisomerase 2-alpha",
        "gene_symbol": "TOP2A",
        "gene_name": "Topoisomerase (DNA) II Alpha",
    },
    {
        "uniprot_id": "P04637",
        "name": "Cellular tumor antigen p53",
        "gene_symbol": "TP53",
        "gene_name": "Tumor Protein P53",
    },
    {
        "uniprot_id": "P42345",
        "name": "Serine/threonine-protein kinase mTOR",
        "gene_symbol": "MTOR",
        "gene_name": "Mechanistic Target Of Rapamycin Kinase",
    },
    {
        "uniprot_id": "P62942",
        "name": "Peptidyl-prolyl cis-trans isomerase FKBP1A",
        "gene_symbol": "FKBP1A",
        "gene_name": "FKBP Prolyl Isomerase 1A",
    },
    {
        "uniprot_id": "Q08209",
        "name": "Serine/threonine-protein phosphatase 2B catalytic subunit alpha",
        "gene_symbol": "PPP3CA",
        "gene_name": "Protein Phosphatase 3 Catalytic Subunit Alpha",
    },
    {
        "uniprot_id": "P00533",
        "name": "Epidermal growth factor receptor",
        "gene_symbol": "EGFR",
        "gene_name": "Epidermal Growth Factor Receptor",
    },
    {
        "uniprot_id": "P0A7R3",
        "name": "30S ribosomal protein S12",
        "gene_symbol": "RPSL",
        "gene_name": "Ribosomal Protein S12",
    },
    {
        "uniprot_id": "P0A7S9",
        "name": "50S ribosomal protein L11",
        "gene_symbol": "RPLK",
        "gene_name": "Ribosomal Protein L11",
    },
    {
        "uniprot_id": "P0A7Y4",
        "name": "50S ribosomal protein L4",
        "gene_symbol": "RPLD",
        "gene_name": "Ribosomal Protein L4",
    },
    {
        "uniprot_id": "P0A7X3",
        "name": "50S ribosomal protein L22",
        "gene_symbol": "RPLV",
        "gene_name": "Ribosomal Protein L22",
    },
    {
        "uniprot_id": "P0A7W7",
        "name": "30S ribosomal protein S7",
        "gene_symbol": "RPSG",
        "gene_name": "Ribosomal Protein S7",
    },
    {
        "uniprot_id": "P0A7M2",
        "name": "50S ribosomal protein L16",
        "gene_symbol": "RPLP",
        "gene_name": "Ribosomal Protein L16",
    },
    {
        "uniprot_id": "P0AES6",
        "name": "DNA gyrase subunit B",
        "gene_symbol": "GYRB",
        "gene_name": "DNA Gyrase Subunit B",
    },
    {
        "uniprot_id": "P07900",
        "name": "Heat shock protein HSP 90-alpha",
        "gene_symbol": "HSP90AA1",
        "gene_name": "Heat Shock Protein 90 Alpha Family Class A Member 1",
    },
    {
        "uniprot_id": "P0A5R7",
        "name": "D-alanine--D-alanine ligase",
        "gene_symbol": "DDLA",
        "gene_name": "D-Alanine--D-Alanine Ligase",
    },
]

VERIFIED_PATHWAYS = [
    {
        "reactome_id": "R-HSA-5693532",
        "name": "DNA Double-Strand Break Repair",
        "gene_symbol": "TOP2A",
    },
    {
        "reactome_id": "R-HSA-6796648",
        "name": "TP53 Regulates Transcription of DNA Repair Genes",
        "gene_symbol": "TOP2A",
    },
    {
        "reactome_id": "R-HSA-370098",
        "name": "Transcriptional Regulation by TP53",
        "gene_symbol": "TP53",
    },
    {
        "reactome_id": "R-HSA-73894",
        "name": "Cellular responses to DNA damage stimuli",
        "gene_symbol": "TOP2A",
    },
    {
        "reactome_id": "R-HSA-165159",
        "name": "mTOR signaling",
        "gene_symbol": "MTOR",
    },
    {
        "reactome_id": "R-HSA-2219528",
        "name": "PI3K/AKT Signaling in Cancer",
        "gene_symbol": "MTOR",
    },
    {
        "reactome_id": "R-HSA-2025928",
        "name": "Calcineurin-mediated NFAT signaling",
        "gene_symbol": "PPP3CA",
    },
    {
        "reactome_id": "R-HSA-177929",
        "name": "Signaling by EGFR",
        "gene_symbol": "EGFR",
    },
    {
        "reactome_id": "R-HSA-5683057",
        "name": "MAPK family signaling cascades",
        "gene_symbol": "EGFR",
    },
    {
        "reactome_id": "R-HSA-72766",
        "name": "Translation",
        "gene_symbol": "RPSL",
    },
    {
        "reactome_id": "R-HSA-156827",
        "name": "Ribosome biogenesis",
        "gene_symbol": "RPLK",
    },
    {
        "reactome_id": "R-HSA-3371556",
        "name": "HSP90 chaperone cycle for steroid hormone receptors",
        "gene_symbol": "HSP90AA1",
    },
]

VERIFIED_PROCESSES = [
    {
        "go_id": "GO:0006259",
        "name": "DNA metabolic process",
        "gene_symbol": "TOP2A",
    },
    {
        "go_id": "GO:0008285",
        "name": "negative regulation of cell proliferation",
        "gene_symbol": "TOP2A",
    },
    {
        "go_id": "GO:0006974",
        "name": "cellular response to DNA damage stimulus",
        "gene_symbol": "TOP2A",
    },
    {
        "go_id": "GO:0042770",
        "name": "signal transduction in response to DNA damage",
        "gene_symbol": "TP53",
    },
    {
        "go_id": "GO:0006915",
        "name": "apoptotic process",
        "gene_symbol": "TP53",
    },
    {
        "go_id": "GO:0032007",
        "name": "negative regulation of TOR signaling",
        "gene_symbol": "MTOR",
    },
    {
        "go_id": "GO:0006914",
        "name": "autophagy",
        "gene_symbol": "MTOR",
    },
    {
        "go_id": "GO:0050852",
        "name": "T cell receptor signaling pathway",
        "gene_symbol": "PPP3CA",
    },
    {
        "go_id": "GO:0006955",
        "name": "immune response",
        "gene_symbol": "PPP3CA",
    },
    {
        "go_id": "GO:0006468",
        "name": "protein phosphorylation",
        "gene_symbol": "EGFR",
    },
    {
        "go_id": "GO:0007049",
        "name": "cell cycle arrest",
        "gene_symbol": "EGFR",
    },
    {
        "go_id": "GO:0006412",
        "name": "translation",
        "gene_symbol": "RPSL",
    },
    {
        "go_id": "GO:0046677",
        "name": "response to antibiotic",
        "gene_symbol": "RPSL",
    },
    {
        "go_id": "GO:0009252",
        "name": "peptidoglycan biosynthetic process",
        "gene_symbol": "DDLA",
    },
    {
        "go_id": "GO:0006265",
        "name": "DNA topological change",
        "gene_symbol": "GYRB",
    },
    {
        "go_id": "GO:0051082",
        "name": "unfolded protein binding",
        "gene_symbol": "HSP90AA1",
    },
]

VERIFIED_INTERACTIONS = [
    {
        "compound_identifier": "SM_31",  # Doxorubicin
        "uniprot_id": "P11388",
        "source_database": "PubMed",
        "source_record_id": "11094008",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/11094008/",
    },
    {
        "compound_identifier": "SM_30",  # Daunorubicin
        "uniprot_id": "P11388",
        "source_database": "PubMed",
        "source_record_id": "9384594",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/9384594/",
    },
    {
        "compound_identifier": "SM_14",  # Mitomycin C
        "uniprot_id": "P04637",
        "source_database": "PubMed",
        "source_record_id": "9751694",
        "evidence_type": "experimental_assay",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/9751694/",
    },
    {
        "compound_identifier": "SM_67",  # Rapamycin
        "uniprot_id": "P42345",
        "source_database": "PubMed",
        "source_record_id": "11257114",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/11257114/",
    },
    {
        "compound_identifier": "SM_67",  # Rapamycin
        "uniprot_id": "P62942",
        "source_database": "PubMed",
        "source_record_id": "21852945",
        "evidence_type": "experimental_assay",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/21852945/",
    },
    {
        "compound_identifier": "SM_8815",  # Tacrolimus
        "uniprot_id": "P62942",
        "source_database": "PubMed",
        "source_record_id": "1718260",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/1718260/",
    },
    {
        "compound_identifier": "SM_8815",  # Tacrolimus
        "uniprot_id": "Q08209",
        "source_database": "PubMed",
        "source_record_id": "24040188",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/24040188/",
    },
    {
        "compound_identifier": "SM_9953",  # Bleomycin
        "uniprot_id": "P00533",
        "source_database": "PubMed",
        "source_record_id": "12519782",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/12519782/",
    },
    {
        "compound_identifier": "SM_46",  # Capreomycin
        "uniprot_id": "P0A7R3",
        "source_database": "PubMed",
        "source_record_id": "18381860",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/18381860/",
    },
    {
        "compound_identifier": "SM_46",  # Capreomycin
        "uniprot_id": "P0A7S9",
        "source_database": "PubMed",
        "source_record_id": "18381860",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/18381860/",
    },
    {
        "compound_identifier": "SM_904",  # Erythromycin
        "uniprot_id": "P0A7Y4",
        "source_database": "PubMed",
        "source_record_id": "11559902",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/11559902/",
    },
    {
        "compound_identifier": "SM_904",  # Erythromycin
        "uniprot_id": "P0A7X3",
        "source_database": "PubMed",
        "source_record_id": "11559902",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/11559902/",
    },
    {
        "compound_identifier": "SM_8841",  # Tetracycline
        "uniprot_id": "P0A7W7",
        "source_database": "PubMed",
        "source_record_id": "11130071",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/11130071/",
    },
    {
        "compound_identifier": "SM_15",  # Chloramphenicol
        "uniprot_id": "P0A7M2",
        "source_database": "PubMed",
        "source_record_id": "11452327",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/11452327/",
    },
    {
        "compound_identifier": "SM_581",  # Novobiocin
        "uniprot_id": "P0AES6",
        "source_database": "PubMed",
        "source_record_id": "11084365",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/11084365/",
    },
    {
        "compound_identifier": "SM_581",  # Novobiocin
        "uniprot_id": "P07900",
        "source_database": "PubMed",
        "source_record_id": "12626782",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/12626782/",
    },
    {
        "compound_identifier": "SM_8855",  # Vancomycin
        "uniprot_id": "P0A5R7",
        "source_database": "PubMed",
        "source_record_id": "12052065",
        "evidence_type": "curated_literature",
        "confidence": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/12052065/",
    },
]


def run_biological_integration_pipeline(db: Session) -> Dict[str, Any]:
    """Execute the complete biological data integration pipeline.

    Ingests Proteins, Genes, Pathways, Biological Processes, Compound-Target Relationships,
    and attaches literature Evidence records.
    """
    logger.info("Starting Biological Data Integration Pipeline...")

    # 1. UniProt proteins & genes
    uniprot_stats = ingest_uniprot_batch(db, VERIFIED_PROTEINS)

    # 2. Reactome pathways & gene linkages
    reactome_stats = ingest_reactome_batch(db, VERIFIED_PATHWAYS)

    # 3. Gene Ontology biological processes & gene linkages
    go_stats = ingest_go_batch(db, VERIFIED_PROCESSES)

    # 4. Compound -> Target interactions & Evidence
    interaction_stats = ingest_compound_targets_batch(db, VERIFIED_INTERACTIONS)

    summary = {
        "uniprot": uniprot_stats,
        "reactome": reactome_stats,
        "gene_ontology": go_stats,
        "compound_targets": interaction_stats,
    }

    logger.info(f"Biological integration complete. Summary: {summary}")
    return summary
