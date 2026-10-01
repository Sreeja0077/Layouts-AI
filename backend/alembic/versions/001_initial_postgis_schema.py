"""
Initial PostGIS & Application Schema Migration.

Revision ID: 001_initial_postgis_schema
Revises: 
Create Date: 2026-09-30 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial_postgis_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enable required PostgreSQL extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "postgis"')

    # 2. Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 3. Create projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('client_name', sa.String(255)),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 4. Create floor_plans table
    op.create_table(
        'floor_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('building_name', sa.String(255)),
        sa.Column('floor_number', sa.Integer(), server_default=sa.text('1')),
        sa.Column('current_working_revision_id', postgresql.UUID(as_uuid=True)),
        sa.Column('current_published_revision_id', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 5. Create floor_plan_source_versions table
    op.create_table(
        'floor_plan_source_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('floor_plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floor_plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_no', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('file_storage_path', sa.String(1024), nullable=False),
        sa.Column('ifc_export_metadata', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 6. Create regions table with PostGIS polygon_geom
    op.execute('''
        CREATE TABLE IF NOT EXISTS regions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            floor_plan_id UUID NOT NULL REFERENCES floor_plans(id) ON DELETE CASCADE,
            name VARCHAR(255) DEFAULT 'Selected Region',
            polygon_geom GEOMETRY(Polygon, 0) NOT NULL,
            polygon_json JSONB NOT NULL,
            area_sqm NUMERIC(10, 2) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 7. Create furniture_catalog_items table
    op.execute('''
        CREATE TABLE IF NOT EXISTS furniture_catalog_items (
            id VARCHAR(100) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(100) NOT NULL,
            width_m NUMERIC(6, 3) NOT NULL,
            height_m NUMERIC(6, 3) NOT NULL,
            clearance_json JSONB NOT NULL DEFAULT '{"front": 0.8, "back": 0.5, "sides": 0.2}'::jsonb,
            aliases JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 8. Create requirement_sets table
    op.create_table(
        'requirement_sets',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('floor_plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floor_plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('region_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('regions.id', ondelete='SET NULL')),
        sa.Column('status', sa.String(50), server_default=sa.text("'DRAFT'")),
        sa.Column('spec_json', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 9. Create clarification_questions table
    op.create_table(
        'clarification_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('requirement_set_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('requirement_sets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_json', postgresql.JSONB(), nullable=False),
        sa.Column('user_answer', sa.Text()),
        sa.Column('is_blocking', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('answered_at', sa.DateTime(timezone=True))
    )

    # 10. Create layout_suggestions table
    op.create_table(
        'layout_suggestions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('floor_plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floor_plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('region_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('regions.id', ondelete='SET NULL')),
        sa.Column('strategy_name', sa.String(255), nullable=False),
        sa.Column('score', sa.Numeric(5, 2), server_default=sa.text('0.0')),
        sa.Column('placed_objects_json', postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column('metrics_json', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column('explanation', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 11. Create revisions table
    op.create_table(
        'revisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('floor_plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floor_plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('base_revision_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('revisions.id')),
        sa.Column('version_no', sa.Integer(), nullable=False),
        sa.Column('operations_json', postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column('snapshot_json', postgresql.JSONB()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 12. Create validation_results table
    op.create_table(
        'validation_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('revision_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('revisions.id', ondelete='CASCADE')),
        sa.Column('suggestion_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('layout_suggestions.id', ondelete='CASCADE')),
        sa.Column('is_valid', sa.Boolean(), nullable=False),
        sa.Column('violations_json', postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 13. Create approvals table
    op.create_table(
        'approvals',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('floor_plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('floor_plans.id', ondelete='CASCADE'), nullable=False),
        sa.Column('revision_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('revisions.id'), nullable=False),
        sa.Column('stage', sa.String(50), nullable=False),
        sa.Column('decision', sa.String(50), nullable=False),
        sa.Column('comment', sa.Text()),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 14. Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('action', sa.String(255), nullable=False),
        sa.Column('entity_ref', sa.String(255), nullable=False),
        sa.Column('details_json', postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 15. Create spatial, GIN & B-tree indexes
    op.execute('CREATE INDEX IF NOT EXISTS idx_regions_geom ON regions USING GIST (polygon_geom)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_req_spec_json ON requirement_sets USING GIN (spec_json)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_rev_ops_json ON revisions USING GIN (operations_json)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_suggestions_floor_plan ON layout_suggestions(floor_plan_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_approvals_revision ON approvals(revision_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_catalog_category ON furniture_catalog_items(category)')


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('approvals')
    op.drop_table('validation_results')
    op.drop_table('revisions')
    op.drop_table('layout_suggestions')
    op.drop_table('clarification_questions')
    op.drop_table('requirement_sets')
    op.drop_table('furniture_catalog_items')
    op.drop_table('regions')
    op.drop_table('floor_plan_source_versions')
    op.drop_table('floor_plans')
    op.drop_table('projects')
    op.drop_table('users')
