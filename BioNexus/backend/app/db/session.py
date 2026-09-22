"""Database connectivity and session management for TiDB Cloud / MySQL using SQLAlchemy 2.x."""

import logging
from typing import Generator, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from ..core.config import settings

logger = logging.getLogger("bionexus.db")

_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker] = None


def get_engine() -> Optional[Engine]:
    """Get or lazily initialize the SQLAlchemy Engine."""
    global _engine, _SessionFactory
    if _engine is not None:
        return _engine

    db_url = settings.get_database_url()
    if not db_url:
        return None

    try:
        connect_args = settings.get_ssl_connect_args()
        # If SQLite (testing), pool settings are different
        if db_url.startswith("sqlite"):
            _engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
            )
        else:
            _engine = create_engine(
                db_url,
                connect_args=connect_args,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_recycle=settings.DB_POOL_RECYCLE,
                pool_pre_ping=True,
            )
        _SessionFactory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_engine,
        )
        logger.info(f"Database engine initialized with {settings.get_masked_db_url()}")
        return _engine
    except Exception as e:
        logger.error(f"Failed to initialize database engine: {e}")
        return None


def get_session_factory() -> Optional[sessionmaker]:
    """Get session factory, ensuring engine is initialized."""
    global _SessionFactory
    if _SessionFactory is None:
        get_engine()
    return _SessionFactory


def get_db() -> Generator[Optional[Session], None, None]:
    """FastAPI dependency yielding a database session for request lifecycle."""
    factory = get_session_factory()
    if factory is None:
        yield None
        return

    session: Session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_connectivity() -> Tuple[str, Optional[str]]:
    """Verify database connectivity with a lightweight SELECT 1 query.

    Returns:
        (status, detail)
        status: "connected" | "disconnected" | "unconfigured"
    """
    engine = get_engine()
    if engine is None:
        return "unconfigured", "No database credentials or URL configured"

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            val = result.scalar()
            if val == 1:
                return "connected", None
            return "disconnected", "Unexpected query result"
    except Exception as e:
        # Sanitize error message to prevent leaking credentials
        err_msg = str(e).split("@")[-1] if "@" in str(e) else str(e)
        logger.warning(f"Database connectivity check failed: {err_msg}")
        return "disconnected", f"Database unreachable: {type(e).__name__}"
