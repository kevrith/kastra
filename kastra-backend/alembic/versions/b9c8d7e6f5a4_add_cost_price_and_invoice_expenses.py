"""add cost_price to products and invoice_items, invoice_id to expenses

Revision ID: b9c8d7e6f5a4
Revises: 9ac2341af6e2
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa

revision = "b9c8d7e6f5a4"
down_revision = "9ac2341af6e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("cost_price", sa.Numeric(15, 2), nullable=True, server_default="0"))
    op.add_column("invoice_items", sa.Column("cost_price", sa.Numeric(15, 2), nullable=True, server_default="0"))
    op.add_column(
        "expenses",
        sa.Column(
            "invoice_id",
            sa.String(20),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_expenses_invoice_id", "expenses", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_expenses_invoice_id", table_name="expenses")
    op.drop_column("expenses", "invoice_id")
    op.drop_column("invoice_items", "cost_price")
    op.drop_column("products", "cost_price")
