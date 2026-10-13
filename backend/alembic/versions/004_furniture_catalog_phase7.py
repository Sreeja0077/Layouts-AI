"""furniture_catalog_phase7

Revision ID: 004_furniture_catalog_phase7
Revises: 003_version_publishing
Create Date: 2026-10-13 16:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '004_furniture_catalog_phase7'
down_revision: Union[str, None] = '003_version_publishing'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    # 1. Add Phase 7 verified catalog columns to existing furniture_catalog_items table
    op.add_column('furniture_catalog_items', sa.Column('subtype', sa.String(100), nullable=True))
    op.add_column('furniture_catalog_items', sa.Column('family_name', sa.String(255), nullable=True))
    op.add_column('furniture_catalog_items', sa.Column('family_type_name', sa.String(255), nullable=True))
    op.add_column('furniture_catalog_items', sa.Column('source_type', sa.String(50), server_default=sa.text("'REVIT_RFA'"), nullable=False))
    op.add_column('furniture_catalog_items', sa.Column('source_reference', sa.String(500), nullable=True))
    op.add_column('furniture_catalog_items', sa.Column('depth_m', sa.Numeric(6, 3), nullable=True))
    op.add_column('furniture_catalog_items', sa.Column('footprint_geometry_json', JSONType, server_default=sa.text("'{}'"), nullable=False))
    op.add_column('furniture_catalog_items', sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('furniture_catalog_items', sa.Column('is_verified', sa.Boolean(), server_default=sa.text('true'), nullable=False))
    op.add_column('furniture_catalog_items', sa.Column('metadata_json', JSONType, server_default=sa.text("'{}'"), nullable=False))
    op.add_column('furniture_catalog_items', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True))

    # Initialize depth_m with legacy height_m where depth_m is NULL
    op.execute("UPDATE furniture_catalog_items SET depth_m = height_m WHERE depth_m IS NULL")

    # 2. Create furniture_bundles table for Phase 7 Task 7.1 bundle schemas
    op.create_table(
        'furniture_bundles',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('components_json', JSONType, server_default=sa.text("'[]'"), nullable=False),
        sa.Column('default_arrangement', sa.String(100), server_default=sa.text("'STANDARD'"), nullable=False),
        sa.Column('orientation_rules_json', JSONType, server_default=sa.text("'{}'"), nullable=False),
        sa.Column('clearance_requirements_json', JSONType, server_default=sa.text("'{}'"), nullable=False),
        sa.Column('metadata_json', JSONType, server_default=sa.text("'{}'"), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_index('idx_bundles_category', 'furniture_bundles', ['category'])


def downgrade() -> None:
    op.drop_index('idx_bundles_category', table_name='furniture_bundles')
    op.drop_table('furniture_bundles')

    op.drop_column('furniture_catalog_items', 'updated_at')
    op.drop_column('furniture_catalog_items', 'metadata_json')
    op.drop_column('furniture_catalog_items', 'is_verified')
    op.drop_column('furniture_catalog_items', 'is_active')
    op.drop_column('furniture_catalog_items', 'footprint_geometry_json')
    op.drop_column('furniture_catalog_items', 'depth_m')
    op.drop_column('furniture_catalog_items', 'source_reference')
    op.drop_column('furniture_catalog_items', 'source_type')
    op.drop_column('furniture_catalog_items', 'family_type_name')
    op.drop_column('furniture_catalog_items', 'family_name')
    op.drop_column('furniture_catalog_items', 'subtype')
