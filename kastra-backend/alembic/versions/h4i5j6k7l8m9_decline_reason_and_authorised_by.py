"""add_decline_reason_to_quotations_and_authorised_by_to_organizations

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
Create Date: 2026-05-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h4i5j6k7l8m9"
down_revision: Union[str, None] = "g3h4i5j6k7l8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "quotations",
        sa.Column("decline_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("authorised_by", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("quotations", "decline_reason")
    op.drop_column("organizations", "authorised_by")
