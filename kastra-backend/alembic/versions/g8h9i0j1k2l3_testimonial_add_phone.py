"""add requested_phone to testimonials

Revision ID: g8h9i0j1k2l3
Revises: f6a7b8c9d0e1
Create Date: 2026-06-08 00:02:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "g8h9i0j1k2l3"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("testimonials", sa.Column("requested_phone", sa.String(30), nullable=True))


def downgrade():
    op.drop_column("testimonials", "requested_phone")
