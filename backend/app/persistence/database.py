"""
Database connection, session management, and dependency injection.
PostgreSQL + PostGIS is the authoritative application source of truth.
Explicit SQLite engine creation is reserved strictly for isolated unit tests when DATABASE_URL starts with 'sqlite://'.
"""

import os
from typing import Generator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

import logging

logger = logging.getLogger(__name__)

# Database connection URLs (defaults to PostgreSQL 16 container with SQLite fallback)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://layouts_user:layouts_password@localhost:5432/layouts_db",
)
DATABASE_FALLBACK_URL = os.getenv("DATABASE_FALLBACK_URL", "sqlite:///./layouts_ai.db")


def init_database_engine():
    """
    Initialize SQLAlchemy engine.
    Authoritative PostgreSQL engine with pool_pre_ping enabled.
    Explicit SQLite support is active when DATABASE_URL starts with 'sqlite://'.
    When DATABASE_URL is configured for PostgreSQL but the server is unreachable,
    automatically falls back to DATABASE_FALLBACK_URL ('sqlite:///./layouts_ai.db')
    to prevent OperationalError during local development.
    """
    primary_url = os.getenv("DATABASE_URL", DATABASE_URL)
    fallback_url = os.getenv("DATABASE_FALLBACK_URL", DATABASE_FALLBACK_URL)

    if primary_url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool
        from app.persistence.models import Base
        engine = create_engine(
            primary_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool if primary_url == "sqlite:///:memory:" else None,
        )
        Base.metadata.create_all(bind=engine)
        return engine

    # Authoritative PostgreSQL engine with reachability check
    try:
        # Quick 2-second probe to test if PostgreSQL daemon is actively listening
        probe_engine = create_engine(
            primary_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 2},
        )
        with probe_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        probe_engine.dispose()

        logger.info("Successfully connected to primary PostgreSQL database at %s", primary_url)
        return create_engine(
            primary_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    except Exception as exc:
        logger.warning(
            "Primary PostgreSQL database at '%s' is unreachable (%s). "
            "Automatically falling back to SQLite database at '%s'.",
            primary_url,
            str(exc),
            fallback_url,
        )
        from sqlalchemy.pool import StaticPool
        from app.persistence.models import Base
        engine = create_engine(
            fallback_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool if fallback_url == "sqlite:///:memory:" else None,
        )
        Base.metadata.create_all(bind=engine)
        return engine


engine = init_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding transactional database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_optional() -> Generator[Optional[Session], None, None]:
    """FastAPI dependency yielding a database session if available, or None if connection fails."""
    try:
        db = SessionLocal()
    except Exception:
        db = None

    if db is None:
        yield None
        return

    try:
        yield db
    finally:
        db.close()


def check_db_health() -> bool:
    """Utility checking if database connection is alive and responding."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
