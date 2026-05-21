"""add_vat_exempt_to_quotation_and_invoice_items

Revision ID: g3h4i5j6k7l8
Revises: f2a3b4c5d6e7
Create Date: 2026-05-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g3h4i5j6k7l8"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "quotation_items",
        sa.Column("vat_exempt", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "invoice_items",
        sa.Column("vat_exempt", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("invoice_items", "vat_exempt")
    op.drop_column("quotation_items", "vat_exempt")
