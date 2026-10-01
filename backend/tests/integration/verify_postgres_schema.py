"""
Verification script for real PostgreSQL + PostGIS database migration and schema (MVP).
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
        # 1. Verify PostgreSQL Extensions (uuid-ossp, postgis)
        ext_result = conn.execute(text("SELECT extname FROM pg_extension")).fetchall()
        extensions = [row[0] for row in ext_result]
        print(f"Installed PostgreSQL extensions: {extensions}")

        required_extensions = ["uuid-ossp", "postgis"]
        for ext in required_extensions:
            assert ext in extensions, f"Required extension '{ext}' missing in PostgreSQL!"
        print("Verified extensions: uuid-ossp, postgis")

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

        # 4. Verify Migration Indexes & Access Methods
        idx_query = text("""
            SELECT i.relname AS index_name, am.amname AS access_method
            FROM pg_index x
            JOIN pg_class i ON i.oid = x.indexrelid
            JOIN pg_am am ON i.relam = am.oid
            JOIN pg_namespace n ON n.oid = i.relnamespace
            WHERE n.nspname = 'public';
        """)
        idx_results = conn.execute(idx_query).fetchall()
        index_map = {row[0]: row[1] for row in idx_results}
        print(f"Verified {len(index_map)} indexes in public schema.")

        expected_indexes = {
            "idx_regions_geom": "gist",
            "idx_req_spec_json": "gin",
            "idx_rev_ops_json": "gin",
            "idx_suggestions_floor_plan": "btree",
            "idx_approvals_revision": "btree",
            "idx_catalog_category": "btree",
        }

        for idx_name, expected_am in expected_indexes.items():
            assert idx_name in index_map, f"Expected index '{idx_name}' missing!"
            actual_am = index_map[idx_name]
            assert actual_am == expected_am, (
                f"Index '{idx_name}' expected method '{expected_am}', got '{actual_am}'"
            )
            print(f"Verified index '{idx_name}' ({expected_am.upper()})")

    print("ALL REAL POSTGRESQL MIGRATION & SCHEMA VERIFICATIONS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    verify_postgres_schema()
