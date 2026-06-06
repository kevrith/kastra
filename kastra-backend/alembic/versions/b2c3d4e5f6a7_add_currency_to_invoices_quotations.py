"""add currency and exchange_rate to invoices and quotations

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("invoices", "quotations"):
        op.add_column(table, sa.Column("currency", sa.String(length=3), nullable=False, server_default="KES"))
        op.add_column(table, sa.Column("exchange_rate", sa.Numeric(12, 6), nullable=False, server_default="1"))


def downgrade() -> None:
    for table in ("invoices", "quotations"):
        op.drop_column(table, "exchange_rate")
        op.drop_column(table, "currency")
