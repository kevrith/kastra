"""add complimentary_ends_at and complimentary_reason to organizations

Revision ID: s5t6u7v8w9x0
Revises: r4s5t6u7v8w9
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa

revision = "s5t6u7v8w9x0"
down_revision = "r4s5t6u7v8w9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("complimentary_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("organizations", sa.Column("complimentary_reason", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "complimentary_ends_at")
    op.drop_column("organizations", "complimentary_reason")
