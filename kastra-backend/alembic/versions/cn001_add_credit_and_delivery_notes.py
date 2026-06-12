"""add credit_notes, delivery_notes tables + invoices.amount_credited

Revision ID: cn001_credit_delivery_notes
Revises: bf002_products_backfill
Create Date: 2026-06-12 00:00:00.000000

Credit notes are the KRA-compliant way to correct or reverse an invoice that
has already been issued (eTIMS invoices cannot be edited or deleted).
invoices.amount_credited tracks the total credited against an invoice so
balance due = grand_total - wht - deposit - amount_paid - amount_credited.
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "cn001_credit_delivery_notes"
down_revision = "bf002_products_backfill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("amount_credited", sa.Numeric(15, 2), nullable=False, server_default="0"),
    )

    op.create_table(
        "credit_notes",
        sa.Column("id", sa.String(length=30), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("invoice_id", sa.String(length=20), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="issued"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="KES"),
        sa.Column("exchange_rate", sa.Numeric(12, 6), nullable=False, server_default="1"),
        sa.Column("subtotal", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("vat_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("grand_total", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("etims_cu_invoice_no", sa.String(length=50), nullable=True),
        sa.Column("etims_rcpt_sign", sa.Text(), nullable=True),
        sa.Column("etims_int_data", sa.Text(), nullable=True),
        sa.Column("etims_submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_credit_notes_organization_id", "credit_notes", ["organization_id"])
    op.create_index("ix_credit_notes_invoice_id", "credit_notes", ["invoice_id"])
    op.create_index("ix_credit_notes_client_id", "credit_notes", ["client_id"])

    op.create_table(
        "credit_note_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("credit_note_id", sa.String(length=30), sa.ForeignKey("credit_notes.id"), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(15, 2), nullable=False),
        sa.Column("vat_exempt", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
    )
    op.create_index("ix_credit_note_items_credit_note_id", "credit_note_items", ["credit_note_id"])

    op.create_table(
        "delivery_notes",
        sa.Column("id", sa.String(length=30), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("invoice_id", sa.String(length=20), sa.ForeignKey("invoices.id"), nullable=True),
        sa.Column("quotation_id", sa.String(length=20), sa.ForeignKey("quotations.id"), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("lpo_number", sa.String(length=100), nullable=True),
        sa.Column("delivery_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("vehicle_reg", sa.String(length=30), nullable=True),
        sa.Column("driver_name", sa.String(length=150), nullable=True),
        sa.Column("received_by", sa.String(length=150), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="issued"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_delivery_notes_organization_id", "delivery_notes", ["organization_id"])
    op.create_index("ix_delivery_notes_invoice_id", "delivery_notes", ["invoice_id"])
    op.create_index("ix_delivery_notes_client_id", "delivery_notes", ["client_id"])

    op.create_table(
        "delivery_note_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("delivery_note_id", sa.String(length=30), sa.ForeignKey("delivery_notes.id"), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
    )
    op.create_index("ix_delivery_note_items_delivery_note_id", "delivery_note_items", ["delivery_note_id"])

    # Match rls001: deny direct PostgREST access; the API connects as postgres
    # which bypasses RLS.
    for table in ("credit_notes", "credit_note_items", "delivery_notes", "delivery_note_items"):
        op.execute(f"ALTER TABLE IF EXISTS public.{table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("delivery_note_items")
    op.drop_table("delivery_notes")
    op.drop_table("credit_note_items")
    op.drop_table("credit_notes")
    op.drop_column("invoices", "amount_credited")
