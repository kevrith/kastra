"""add subscription_payments and admin_audit_log

Revision ID: r4s5t6u7v8w9
Revises: q3r4s5t6u7v8
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "r4s5t6u7v8w9"
down_revision = "q3r4s5t6u7v8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("org_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("amount_kes", sa.Integer, nullable=False),
        sa.Column("plan", sa.String(20), nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=False),
        sa.Column("reference", sa.String(150), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sub_payments_org", "subscription_payments", ["organization_id"])
    op.create_index("ix_sub_payments_created", "subscription_payments", ["created_at"])

    op.create_table(
        "admin_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target_org_id", sa.String(36), nullable=False),
        sa.Column("target_org_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("details", sa.Text, nullable=True),
        sa.Column("performed_by", sa.String(50), nullable=False, server_default="superadmin"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_log_created", "admin_audit_log", ["created_at"])
    op.create_index("ix_audit_log_org", "admin_audit_log", ["target_org_id"])


def downgrade() -> None:
    op.drop_table("subscription_payments")
    op.drop_table("admin_audit_log")
