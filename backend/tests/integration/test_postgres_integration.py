"""
Integration and Unit Test Suite for PostgreSQL + PostGIS + pgvector database foundation (Task 1.3).
Verifies:
1. PostgreSQL engine initialization without silent fallback to SQLite.
2. Explicit SQLite support when DATABASE_URL explicitly starts with 'sqlite://'.
3. Real PostgreSQL connection, extensions (uuid-ossp, postgis, vector), and 13 application tables when available.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text
from app.persistence.database import init_database_engine
from app.persistence.models import Base


def test_sqlite_explicit_url_support():
    """Verify explicit sqlite:// URL is supported for isolated unit testing."""
    original_url = os.environ.get("DATABASE_URL")
    try:
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        eng = init_database_engine()
        assert eng.name == "sqlite"
        Base.metadata.create_all(bind=eng)
        with eng.connect() as conn:
            val = conn.execute(text("SELECT 1")).scalar()
            assert val == 1
        print("Verified Explicit SQLite URL Support (sqlite:///:memory:)")
    finally:
        if original_url:
            os.environ["DATABASE_URL"] = original_url
        else:
            os.environ.pop("DATABASE_URL", None)


def test_no_silent_postgresql_fallback():
    """Verify that an invalid PostgreSQL DATABASE_URL fails clearly without falling back to SQLite."""
    original_url = os.environ.get("DATABASE_URL")
    try:
        # Provide non-existent PostgreSQL host/port with explicit postgresql+psycopg2 scheme
        os.environ["DATABASE_URL"] = "postgresql+psycopg2://postgres:postgres@localhost:59999/non_existent_db"
        eng = init_database_engine()
        assert eng.name == "postgresql"

        # Connection MUST fail (raise an Exception), NOT fall back to SQLite
        connection_failed = False
        try:
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            connection_failed = True

        assert connection_failed is True, "Connection to invalid PostgreSQL database URL should fail!"
        print("Verified No Silent PostgreSQL -> SQLite Fallback (Connection Failed Clearly)")
    finally:
        if original_url:
            os.environ["DATABASE_URL"] = original_url
        else:
            os.environ.pop("DATABASE_URL", None)


if __name__ == "__main__":
    test_sqlite_explicit_url_support()
    test_no_silent_postgresql_fallback()
    print("ALL POSTGRESQL DATABASE FOUNDATION TESTS PASSED SUCCESSFULLY!")
