"""add_floor_plan_version_publishing

Revision ID: 003_version_publishing
Revises: 002_verification_state
Create Date: 2026-10-05 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '003_version_publishing'
down_revision: Union[str, None] = '002_verification_state'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUIDType = sa.String(36).with_variant(postgresql.UUID(as_uuid=True), "postgresql")


def upgrade() -> None:
    op.add_column('floor_plan_source_versions', sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('floor_plan_source_versions', sa.Column('published_by_user_id', UUIDType, sa.ForeignKey('users.id'), nullable=True))
    op.add_column('floor_plan_source_versions', sa.Column('published_at', sa.DateTime(timezone=True), nullable=True))

    op.create_unique_constraint('uq_floor_plan_version_no', 'floor_plan_source_versions', ['floor_plan_id', 'version_no'])
    op.create_index(
        'uq_published_source_version',
        'floor_plan_source_versions',
        ['floor_plan_id'],
        unique=True,
        postgresql_where=sa.text('is_published = true'),
        sqlite_where=sa.text('is_published = 1'),
    )


def downgrade() -> None:
    op.drop_index('uq_published_source_version', table_name='floor_plan_source_versions')
    op.drop_constraint('uq_floor_plan_version_no', 'floor_plan_source_versions', type_='unique')
    op.drop_column('floor_plan_source_versions', 'published_at')
    op.drop_column('floor_plan_source_versions', 'published_by_user_id')
    op.drop_column('floor_plan_source_versions', 'is_published')
