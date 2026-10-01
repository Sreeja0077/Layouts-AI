"""
Unit test for PostgreSQL + PostGIS database schema ORM models (Task 0.5).
Verifies SQLAlchemy model metadata and table definitions.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.persistence.models import (
    Base,
    User,
    Project,
    FloorPlan,
    Region,
    RequirementSetModel,
    LayoutSuggestionModel,
    Revision,
    Approval,
)


def test_db_models_metadata():
    tables = Base.metadata.tables
    expected_tables = {
        "users",
        "projects",
        "floor_plans",
        "regions",
        "requirement_sets",
        "layout_suggestions",
        "revisions",
        "approvals",
    }
    for table_name in expected_tables:
        assert table_name in tables, f"Missing table {table_name} in ORM metadata!"

    # Verify foreign key relationships exist
    assert "floor_plan_id" in tables["regions"].columns
    assert "project_id" in tables["floor_plans"].columns
    assert "revision_id" in tables["approvals"].columns

    print(f"Verified {len(expected_tables)} ORM tables in SQLAlchemy metadata: {sorted(list(expected_tables))}")


if __name__ == "__main__":
    test_db_models_metadata()
    print("ALL DATABASE ORM SCHEMA TESTS PASSED SUCCESSFULLY!")
