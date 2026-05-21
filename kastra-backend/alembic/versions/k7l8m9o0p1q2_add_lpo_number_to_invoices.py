"""add lpo_number to invoices

Revision ID: k7l8m9o0p1q2
Revises: j6k7l8m9o0p1
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = "k7l8m9o0p1q2"
down_revision = "j6k7l8m9o0p1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("lpo_number", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invoices", "lpo_number")
