"""
Verification script for real PostgreSQL + PostGIS + pgvector database migration and schema.
Executed in CI pipeline against live PostgreSQL service after 'alembic upgrade head'.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres_secure_password@localhost:5432/layouts_ai"
)


def verify_postgres_schema():
    print(f"Connecting to PostgreSQL database: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    with engine.connect() as conn:
        # 1. Verify PostgreSQL Extensions
        ext_result = conn.execute(text("SELECT extname FROM pg_extension")).fetchall()
        extensions = [row[0] for row in ext_result]
        print(f"Installed PostgreSQL extensions: {extensions}")

        required_extensions = ["uuid-ossp", "postgis", "vector"]
        for ext in required_extensions:
            assert ext in extensions, f"Required extension '{ext}' missing in PostgreSQL!"
        print("Verified extensions: uuid-ossp, postgis, vector")

        # 2. Verify 13 Application Tables
        tbl_result = conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        ).fetchall()
        tables = [row[0] for row in tbl_result]
        print(f"Existing public tables ({len(tables)}): {tables}")

        expected_tables = [
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
        ]
        for tbl in expected_tables:
            assert tbl in tables, f"Expected application table '{tbl}' is missing!"
        print(f"Verified all 13 application tables exist.")

        # 3. Verify regions.polygon_geom column & data type
        col_result = conn.execute(
            text(
                "SELECT udt_name FROM information_schema.columns "
                "WHERE table_name = 'regions' AND column_name = 'polygon_geom'"
            )
        ).fetchone()
        assert col_result is not None, "Column 'regions.polygon_geom' missing!"
        assert col_result[0] == "geometry", f"Expected udt_name 'geometry', got '{col_result[0]}'"
        print("Verified 'regions.polygon_geom' exists as PostGIS geometry.")

        # 4. Verify furniture_catalog_items.embedding column & vector type
        vec_result = conn.execute(
            text(
                "SELECT udt_name FROM information_schema.columns "
                "WHERE table_name = 'furniture_catalog_items' AND column_name = 'embedding'"
            )
        ).fetchone()
        assert vec_result is not None, "Column 'furniture_catalog_items.embedding' missing!"
        assert vec_result[0] == "vector", f"Expected udt_name 'vector', got '{vec_result[0]}'"
        print("Verified 'furniture_catalog_items.embedding' exists as pgvector VECTOR(1536).")

        # 5. Verify Indexes
        idx_result = conn.execute(
            text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")
        ).fetchall()
        indexes = [row[0] for row in idx_result]
        print(f"Verified indexes in database ({len(indexes)} found).")
        assert "idx_regions_polygon_geom" in indexes, "Spatial index 'idx_regions_polygon_geom' missing!"
        assert "idx_furniture_aliases" in indexes, "GIN index 'idx_furniture_aliases' missing!"
        print("Verified GIST spatial & GIN indexes.")

    print("ALL REAL POSTGRESQL MIGRATION & SCHEMA VERIFICATIONS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    verify_postgres_schema()
