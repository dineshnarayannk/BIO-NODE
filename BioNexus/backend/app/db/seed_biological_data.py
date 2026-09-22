"""Seed script for Step 4 Biological Data Integration.

Ingests verified UniProt proteins, NCBI/HGNC genes, Reactome pathways,
Gene Ontology biological processes, Compound-to-Target relationships,
and literature Evidence citations into TiDB Cloud.
"""

import logging
import sys
from app.db.session import get_session_factory
from app.services.ingestion.pipeline import run_biological_integration_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("bionexus.seed_biological_data")


def main():
    logger.info("Initializing database session factory...")
    factory = get_session_factory()
    if not factory:
        logger.error("Database connection factory could not be established. Check .env configuration.")
        sys.exit(1)

    with factory() as db:
        try:
            summary = run_biological_integration_pipeline(db)
            logger.info("Biological data integration completed successfully!")
            print("\n=== BioNexus Step 4: Biological Data Integration Summary ===")
            print(f"UniProt Ingestion: {summary['uniprot']}")
            print(f"Reactome Ingestion: {summary['reactome']}")
            print(f"Gene Ontology Ingestion: {summary['gene_ontology']}")
            print(f"Compound Targets & Evidence: {summary['compound_targets']}")
            print("============================================================\n")
        except Exception as e:
            logger.error(f"Biological data integration pipeline failed: {e}", exc_info=True)
            db.rollback()
            sys.exit(1)


if __name__ == "__main__":
    main()
