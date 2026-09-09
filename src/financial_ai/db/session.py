"""Database connection and session factory supporting PostgreSQL with graceful fallback."""
import os
import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

from financial_ai.db.models import Base

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_PG_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/financial_db"
)
SQLITE_FALLBACK_URL = "sqlite:///./data/financial_fallback.db"

_engine = None
_SessionFactory = None


def get_engine():
    """Retrieve or initialize the SQLAlchemy engine."""
    global _engine, _SessionFactory
    if _engine is not None:
        return _engine

    db_url = os.getenv("DATABASE_URL", DEFAULT_PG_URL)
    try:
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            echo=False,
            future=True,
        )
        # Test connection
        with engine.connect() as conn:
            pass
        logger.info("Successfully connected to PostgreSQL at %s", db_url.split("@")[-1])
        _engine = engine
    except Exception as exc:
        logger.warning(
            "Could not connect to PostgreSQL (%s). Falling back to SQLite (%s) for local execution.",
            exc,
            SQLITE_FALLBACK_URL,
        )
        os.makedirs("./data", exist_ok=True)
        _engine = create_engine(
            SQLITE_FALLBACK_URL,
            connect_args={"check_same_thread": False},
            echo=False,
            future=True,
        )

    _SessionFactory = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager providing a transactional database session."""
    global _SessionFactory
    if _SessionFactory is None:
        get_engine()

    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Initialize database schema tables."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
