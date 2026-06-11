"""add affiliate system

Revision ID: af01_add_affiliate_system
Revises: c4d5e6f7a8b9
Create Date: 2026-06-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "af01_add_affiliate_system"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "affiliates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("payout_phone", sa.String(20), nullable=False),
        sa.Column("paystack_recipient_code", sa.String(100), nullable=True),
        sa.Column("balance_ksh", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_earned_ksh", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_paid_ksh", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "affiliate_referrals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("affiliate_id", UUID(as_uuid=True), sa.ForeignKey("affiliates.id"), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "affiliate_commissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("affiliate_id", UUID(as_uuid=True), sa.ForeignKey("affiliates.id"), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("amount_ksh", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "uq_affiliate_commission_month",
        "affiliate_commissions",
        ["affiliate_id", "organization_id", "month"],
    )

    op.create_table(
        "affiliate_payouts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("affiliate_id", UUID(as_uuid=True), sa.ForeignKey("affiliates.id"), nullable=False),
        sa.Column("amount_ksh", sa.Numeric(12, 2), nullable=False),
        sa.Column("payout_phone", sa.String(20), nullable=False),
        sa.Column("paystack_transfer_code", sa.String(100), nullable=True),
        sa.Column("paystack_reference", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("failure_reason", sa.Text, nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("affiliate_payouts")
    op.drop_table("affiliate_commissions")
    op.drop_table("affiliate_referrals")
    op.drop_table("affiliates")
