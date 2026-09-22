"""Database schema initialization utility for TiDB Cloud / MySQL.

Executes Base.metadata.create_all() to create missing tables safely.
Does NOT drop or reset existing tables.
"""

import sys
import logging
from typing import Optional
from sqlalchemy.engine import Engine
from .models import Base, Compound, Protein, Gene, Pathway, BiologicalProcess, Relationship, Evidence
from .session import get_engine
from ..core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bionexus.db.init")


def init_db(engine: Optional[Engine] = None) -> bool:
    """Create all BioNexus database tables if they do not exist."""
    target_engine = engine or get_engine()
    if target_engine is None:
        logger.error(
            "Cannot initialize database tables: Database engine is not configured. "
            "Please set DATABASE_URL or DB_HOST in your .env file."
        )
        return False

    try:
        logger.info(f"Initializing BioNexus database schema on {settings.get_masked_db_url()}...")
        # create_all will only create tables that do not already exist; will not drop or overwrite data
        Base.metadata.create_all(bind=target_engine)
        logger.info("BioNexus database schema initialization completed successfully.")
        return True
    except Exception as e:
        # Sanitize error output to avoid logging secrets
        err_msg = str(e).split("@")[-1] if "@" in str(e) else str(e)
        logger.error(f"Error during database initialization: {err_msg}")
        return False


if __name__ == "__main__":
    success = init_db()
    sys.exit(0 if success else 1)
