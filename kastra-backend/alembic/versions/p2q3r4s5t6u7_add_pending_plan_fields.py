"""add pending_plan and sub_mpesa_checkout_id to organizations

Revision ID: p2q3r4s5t6u7
Revises: o1p2q3r4s5t6
Create Date: 2026-05-21

"""
from alembic import op
import sqlalchemy as sa

revision = "p2q3r4s5t6u7"
down_revision = "o1p2q3r4s5t6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("pending_plan", sa.String(20), nullable=True))
    op.add_column("organizations", sa.Column("sub_mpesa_checkout_id", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "sub_mpesa_checkout_id")
    op.drop_column("organizations", "pending_plan")
