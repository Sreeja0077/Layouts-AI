"""
Initial PostGIS & Platform Schema Migration.

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
    # Upgrade operations: Enable PostGIS & vector extensions, create initial tables
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "postgis"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')


def downgrade() -> None:
    # Downgrade operations
    pass
