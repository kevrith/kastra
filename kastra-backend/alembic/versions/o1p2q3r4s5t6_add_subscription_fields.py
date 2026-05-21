"""add subscription fields to organizations

Revision ID: o1p2q3r4s5t6
Revises: n0p1q2r3s4t5
Create Date: 2026-05-21

"""
from alembic import op
import sqlalchemy as sa

revision = "o1p2q3r4s5t6"
down_revision = "n0p1q2r3s4t5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("plan", sa.String(20), nullable=False, server_default="free"))
    op.add_column("organizations", sa.Column("plan_status", sa.String(20), nullable=False, server_default="active"))
    op.add_column("organizations", sa.Column("billing_cycle_start", sa.DateTime(timezone=True), nullable=True))
    op.add_column("organizations", sa.Column("next_billing_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("organizations", sa.Column("invoices_this_month", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("organizations", sa.Column("quotations_this_month", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("organizations", sa.Column("ocr_scans_this_month", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("organizations", sa.Column("counters_reset_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "counters_reset_at")
    op.drop_column("organizations", "ocr_scans_this_month")
    op.drop_column("organizations", "quotations_this_month")
    op.drop_column("organizations", "invoices_this_month")
    op.drop_column("organizations", "next_billing_date")
    op.drop_column("organizations", "billing_cycle_start")
    op.drop_column("organizations", "plan_status")
    op.drop_column("organizations", "plan")
