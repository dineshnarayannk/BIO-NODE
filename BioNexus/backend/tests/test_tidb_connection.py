"""Integration and connectivity verification tests for TiDB Cloud / database backend."""

import pytest
from sqlalchemy import text
from app.core.config import settings
from app.db.session import check_db_connectivity, get_engine
from app.db.init_db import init_db


def test_db_connectivity_helper():
    """Verify check_db_connectivity returns a valid status string without crashing."""
    status, detail = check_db_connectivity()
    assert status in ("connected", "disconnected", "unconfigured")
    if status == "unconfigured":
        assert detail is not None


@pytest.mark.skipif(
    not settings.get_database_url(),
    reason="TiDB Cloud database URL not configured in environment",
)
def test_tidb_cloud_live_connection():
    """Live integration test executing SELECT 1 against configured TiDB database."""
    engine = get_engine()
    assert engine is not None

    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.skipif(
    not settings.get_database_url(),
    reason="TiDB Cloud database URL not configured in environment",
)
def test_tidb_cloud_table_initialization():
    """Live integration test creating BioNexus tables on TiDB Cloud."""
    success = init_db()
    assert success is True
