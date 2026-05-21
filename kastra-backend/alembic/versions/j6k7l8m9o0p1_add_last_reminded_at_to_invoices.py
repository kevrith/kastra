"""add last_reminded_at to invoices

Revision ID: j6k7l8m9o0p1
Revises: i5j6k7l8m9o0
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = "j6k7l8m9o0p1"
down_revision = "i5j6k7l8m9o0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("last_reminded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invoices", "last_reminded_at")
