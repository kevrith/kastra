"""add procurement: purchase orders, notes, goods receipts, supplier bills, price history

Revision ID: p1q2r3s4t5u6
Revises: af02_add_payout_method
Create Date: 2026-06-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "p1q2r3s4t5u6"
down_revision = "af02_add_payout_method"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_request_id", UUID(as_uuid=True), sa.ForeignKey("supplier_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("portal_token", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="KES"),
        sa.Column("expected_delivery", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("supplier_notes", sa.Text, nullable=True),
        sa.Column("subtotal", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("confirmed_total", sa.Numeric(15, 2), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_purchase_orders_organization_id", "purchase_orders", ["organization_id"])
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
    op.create_index("ix_purchase_orders_status", "purchase_orders", ["status"])
    op.create_index("ix_purchase_orders_created_at", "purchase_orders", ["created_at"])
    op.create_index("ix_purchase_orders_portal_token", "purchase_orders", ["portal_token"], unique=True)

    op.create_table(
        "purchase_order_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("purchase_order_id", sa.String(20), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("ordered_qty", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("ordered_unit_price", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("confirmed_qty", sa.Numeric(10, 2), nullable=True),
        sa.Column("confirmed_unit_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("received_qty", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("line_total", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer, server_default="0"),
    )
    op.create_index("ix_purchase_order_items_purchase_order_id", "purchase_order_items", ["purchase_order_id"])

    op.create_table(
        "purchase_order_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("purchase_order_id", sa.String(20), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("author_type", sa.String(20), nullable=False, server_default="buyer"),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_purchase_order_notes_purchase_order_id", "purchase_order_notes", ["purchase_order_id"])

    op.create_table(
        "goods_receipts",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("purchase_order_id", sa.String(20), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("received_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("received_date", sa.Date, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_goods_receipts_organization_id", "goods_receipts", ["organization_id"])
    op.create_index("ix_goods_receipts_purchase_order_id", "goods_receipts", ["purchase_order_id"])

    op.create_table(
        "goods_receipt_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("goods_receipt_id", sa.String(20), sa.ForeignKey("goods_receipts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purchase_order_item_id", UUID(as_uuid=True), sa.ForeignKey("purchase_order_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer, server_default="0"),
    )
    op.create_index("ix_goods_receipt_items_goods_receipt_id", "goods_receipt_items", ["goods_receipt_id"])

    op.create_table(
        "supplier_bills",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("purchase_order_id", sa.String(20), sa.ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("goods_receipt_id", sa.String(20), sa.ForeignKey("goods_receipts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("supplier_ref", sa.String(100), nullable=True),
        sa.Column("bill_date", sa.Date, nullable=False),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("subtotal", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("amount_paid", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="unpaid"),
        sa.Column("match_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("match_notes", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_supplier_bills_organization_id", "supplier_bills", ["organization_id"])
    op.create_index("ix_supplier_bills_supplier_id", "supplier_bills", ["supplier_id"])
    op.create_index("ix_supplier_bills_status", "supplier_bills", ["status"])
    op.create_index("ix_supplier_bills_due_date", "supplier_bills", ["due_date"])

    op.create_table(
        "supplier_price_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("source_po_id", sa.String(20), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_supplier_price_history_org_supplier", "supplier_price_history", ["organization_id", "supplier_id"])
    op.create_index("ix_supplier_price_history_lookup", "supplier_price_history", ["supplier_id", "description"])


def downgrade() -> None:
    op.drop_table("supplier_price_history")
    op.drop_table("supplier_bills")
    op.drop_table("goods_receipt_items")
    op.drop_table("goods_receipts")
    op.drop_table("purchase_order_notes")
    op.drop_table("purchase_order_items")
    op.drop_table("purchase_orders")
