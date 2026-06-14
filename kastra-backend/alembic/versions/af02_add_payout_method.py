"""add method column to affiliate_payouts

Revision ID: af02_add_payout_method
Revises: cn001_credit_delivery_notes
Create Date: 2026-06-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "af02_add_payout_method"
down_revision = "cn001_credit_delivery_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "affiliate_payouts",
        sa.Column("method", sa.String(10), nullable=False, server_default="manual"),
    )


def downgrade() -> None:
    op.drop_column("affiliate_payouts", "method")
