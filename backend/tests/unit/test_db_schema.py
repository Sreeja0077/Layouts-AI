"""
Unit test for PostgreSQL + PostGIS database schema ORM models (Task 1.3).
Verifies SQLAlchemy model metadata and table definitions for all 13 application entities.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Set SQLite in-memory DB for offline unit testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.persistence.models import (
    Approval,
    AuditLogModel,
    Base,
    ClarificationQuestionModel,
    FloorPlan,
    FloorPlanSourceVersionModel,
    FurnitureCatalogItemModel,
    LayoutSuggestionModel,
    Project,
    Region,
    RequirementSetModel,
    Revision,
    User,
    ValidationResultModel,
)


def test_db_models_metadata():
    tables = Base.metadata.tables
    expected_tables = {
        "users",
        "projects",
        "floor_plans",
        "floor_plan_source_versions",
        "regions",
        "furniture_catalog_items",
        "requirement_sets",
        "clarification_questions",
        "layout_suggestions",
        "revisions",
        "validation_results",
        "approvals",
        "audit_logs",
    }
    for table_name in expected_tables:
        assert table_name in tables, f"Missing table {table_name} in ORM metadata!"

    # Verify foreign key relationships exist
    assert "floor_plan_id" in tables["regions"].columns
    assert "project_id" in tables["floor_plans"].columns
    assert "revision_id" in tables["approvals"].columns
    assert "requirement_set_id" in tables["clarification_questions"].columns

    print(f"Verified {len(expected_tables)} ORM tables in SQLAlchemy metadata: {sorted(list(expected_tables))}")


if __name__ == "__main__":
    test_db_models_metadata()
    print("ALL DATABASE ORM SCHEMA TESTS PASSED SUCCESSFULLY!")
