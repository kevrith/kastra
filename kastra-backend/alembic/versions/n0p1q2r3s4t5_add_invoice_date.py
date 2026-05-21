"""add invoice_date to invoices

Revision ID: n0p1q2r3s4t5
Revises: m9o0p1q2r3s4
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = "n0p1q2r3s4t5"
down_revision = "m9o0p1q2r3s4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("invoice_date", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invoices", "invoice_date")
