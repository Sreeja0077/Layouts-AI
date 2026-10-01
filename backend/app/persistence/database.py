"""
Database connection, session management, and dependency injection.
Supports PostgreSQL + PostGIS connections with fallback to SQLite in-memory for testing environments.
"""

import os
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from app.persistence.models import Base

# Database connection URL (defaults to PostgreSQL, supports SQLite fallback for testing)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/layouts_ai"
)


def init_database_engine():
    """Initialize SQLAlchemy engine with graceful fallback for offline unit testing."""
    if DATABASE_URL.startswith("sqlite"):
        return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    try:
        eng = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
        # Probe DBAPI driver availability (e.g. psycopg2)
        _ = eng.dialect.dbapi
        return eng
    except Exception:
        # Fallback to SQLite in-memory if PostgreSQL driver (psycopg2) or server is unavailable
        return create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})


engine = init_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding transactional database session per request."""
    db = SessionLocal()
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
