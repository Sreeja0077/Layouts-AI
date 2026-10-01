"""
Unit test for database connection and session injection (Task 1.3).
Verifies get_db() session generator, health probe, and SQLAlchemy table binding.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Set SQLite in-memory database URL for offline testing
import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import text
from app.persistence.database import check_db_health, engine, get_db
from app.persistence.models import Base


def test_database_connection_and_session():
    # Create tables in memory SQLite for test execution
    Base.metadata.create_all(bind=engine)

    # Verify database health check probe
    assert check_db_health() is True, "Database health check probe failed!"

    # Verify get_db session generator
    db_gen = get_db()
    db = next(db_gen)
    try:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        db_gen.close()


if __name__ == "__main__":
    test_database_connection_and_session()
    print("ALL DATABASE CONNECTION & SESSION TESTS PASSED SUCCESSFULLY!")
