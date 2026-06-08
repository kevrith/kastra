"""merge multiple heads

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8, c1d2e3f4a5b6, z1a2b3c4d5e6
Create Date: 2026-06-08 00:00:00.000000
"""
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = ("c3d4e5f6a7b8", "c1d2e3f4a5b6", "z1a2b3c4d5e6")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
