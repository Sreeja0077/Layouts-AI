"""
Database connection, session management, and dependency injection.
PostgreSQL + PostGIS is the authoritative application source of truth.
Explicit SQLite engine creation is reserved strictly for isolated unit tests when DATABASE_URL starts with 'sqlite://'.
"""

import os
from typing import Generator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Database connection URL (defaults to PostgreSQL 16 container)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres_secure_password@localhost:5432/layouts_ai"
)


def init_database_engine():
    """
    Initialize SQLAlchemy engine.
    Authoritative PostgreSQL engine with pool_pre_ping enabled.
    Explicit SQLite support is active only when DATABASE_URL starts with 'sqlite://'.
    No silent fallback to SQLite occurs if PostgreSQL or driver is unavailable.
    """
    url = os.getenv("DATABASE_URL", DATABASE_URL)
    if url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    # Authoritative PostgreSQL engine
    try:
        return create_engine(
            url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    except (ImportError, ModuleNotFoundError) as exc:
        raise RuntimeError(
            f"PostgreSQL DBAPI driver (psycopg2) is missing or broken: {str(exc)}"
        ) from exc


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
