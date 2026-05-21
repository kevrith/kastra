"""add discounts, charges, wht, deposit to invoices and quotations

Revision ID: m9o0p1q2r3s4
Revises: l8m9o0p1q2r3
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "m9o0p1q2r3s4"
down_revision = "l8m9o0p1q2r3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Per-item discount on invoice_items
    op.add_column("invoice_items", sa.Column("discount_pct", sa.Numeric(5, 2), nullable=False, server_default="0"))
    # Per-item discount on quotation_items
    op.add_column("quotation_items", sa.Column("discount_pct", sa.Numeric(5, 2), nullable=False, server_default="0"))

    # Invoice-level fields
    for col in [
        sa.Column("discount_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("total_discount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("charges_total", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("wht_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("wht_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("deposit_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
    ]:
        op.add_column("invoices", col)

    # Quotation-level fields (no deposit — quotations don't receive payments)
    for col in [
        sa.Column("discount_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("total_discount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("charges_total", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("wht_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("wht_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
    ]:
        op.add_column("quotations", col)

    # invoice_charges table
    op.create_table(
        "invoice_charges",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", sa.String(20), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("vat_exempt", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_charges_invoice_id", "invoice_charges", ["invoice_id"])

    # quotation_charges table
    op.create_table(
        "quotation_charges",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("quotation_id", sa.String(20), sa.ForeignKey("quotations.id"), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("vat_exempt", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotation_charges_quotation_id", "quotation_charges", ["quotation_id"])


def downgrade() -> None:
    op.drop_index("ix_quotation_charges_quotation_id", table_name="quotation_charges")
    op.drop_table("quotation_charges")
    op.drop_index("ix_invoice_charges_invoice_id", table_name="invoice_charges")
    op.drop_table("invoice_charges")

    for col in ["discount_pct", "total_discount", "charges_total", "wht_pct", "wht_amount"]:
        op.drop_column("quotations", col)

    for col in ["discount_pct", "total_discount", "charges_total", "wht_pct", "wht_amount", "deposit_amount"]:
        op.drop_column("invoices", col)

    op.drop_column("quotation_items", "discount_pct")
    op.drop_column("invoice_items", "discount_pct")
