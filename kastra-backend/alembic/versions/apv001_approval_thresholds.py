"""add spend-approval thresholds and approval state

Revision ID: apv001_approvals
Revises: mfa001_add_totp
Create Date: 2026-09-02 00:00:00.000000

Segregation of duties: a purchase order or invoice at or above the
organisation's threshold needs a second person's approval before it goes out.

Backward compatible. Both thresholds default to NULL, which means "no approval
step", so existing organisations behave exactly as before until they opt in.
invoices.approval_status carries a server default of 'approved' so rows written
by the previous release are valid.
"""
import sqlalchemy as sa
from alembic import op

revision = "apv001_approvals"
down_revision = "mfa001_add_totp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("po_approval_threshold", sa.Numeric(15, 2), nullable=True))
    op.add_column("organizations", sa.Column("invoice_approval_threshold", sa.Numeric(15, 2), nullable=True))

    op.add_column("purchase_orders", sa.Column("approved_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("purchase_orders", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_purchase_orders_approved_by_users", "purchase_orders", "users", ["approved_by"], ["id"]
    )

    # Who raised the invoice — needed to enforce that the approver is someone
    # else. Nullable: pre-existing rows and automated (recurring) runs have none.
    op.add_column("invoices", sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_invoices_created_by_users", "invoices", "users", ["created_by"], ["id"])
    op.add_column(
        "invoices",
        sa.Column("approval_status", sa.String(20), nullable=False, server_default="approved"),
    )
    op.add_column("invoices", sa.Column("approved_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("invoices", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_invoices_approved_by_users", "invoices", "users", ["approved_by"], ["id"]
    )
    op.create_index("ix_invoices_approval_status", "invoices", ["approval_status"])


def downgrade() -> None:
    op.drop_index("ix_invoices_approval_status", table_name="invoices")
    op.drop_constraint("fk_invoices_approved_by_users", "invoices", type_="foreignkey")
    op.drop_column("invoices", "approved_at")
    op.drop_column("invoices", "approved_by")
    op.drop_column("invoices", "approval_status")
    op.drop_constraint("fk_invoices_created_by_users", "invoices", type_="foreignkey")
    op.drop_column("invoices", "created_by")

    op.drop_constraint("fk_purchase_orders_approved_by_users", "purchase_orders", type_="foreignkey")
    op.drop_column("purchase_orders", "approved_at")
    op.drop_column("purchase_orders", "approved_by")

    op.drop_column("organizations", "invoice_approval_threshold")
    op.drop_column("organizations", "po_approval_threshold")
