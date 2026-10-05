"""add_floor_plan_verification_state

Revision ID: 002_verification_state
Revises: 001_initial_postgis_schema
Create Date: 2026-10-05 11:37:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002_verification_state'
down_revision: Union[str, None] = '001_initial_postgis_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONType = sa.JSON().with_variant(postgresql.JSONB, "postgresql")
UUIDType = sa.String(36).with_variant(postgresql.UUID(as_uuid=True), "postgresql")


def upgrade() -> None:
    op.add_column('floor_plan_source_versions', sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='PENDING'))
    op.add_column('floor_plan_source_versions', sa.Column('verification_report', JSONType, nullable=True))
    op.add_column('floor_plan_source_versions', sa.Column('reviewer_user_id', UUIDType, sa.ForeignKey('users.id'), nullable=True))
    op.add_column('floor_plan_source_versions', sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('floor_plan_source_versions', sa.Column('rejection_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('floor_plan_source_versions', 'rejection_reason')
    op.drop_column('floor_plan_source_versions', 'verified_at')
    op.drop_column('floor_plan_source_versions', 'reviewer_user_id')
    op.drop_column('floor_plan_source_versions', 'verification_report')
    op.drop_column('floor_plan_source_versions', 'verification_status')
