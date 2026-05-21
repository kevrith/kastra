"""add accepted_at to quotations

Revision ID: u7v8w9x0y1z2
Revises: t6u7v8w9x0y1
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = "u7v8w9x0y1z2"
down_revision = "t6u7v8w9x0y1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("quotations", sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("quotations", "accepted_at")
