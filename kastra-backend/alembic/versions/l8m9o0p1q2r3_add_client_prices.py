"""add client_prices table

Revision ID: l8m9o0p1q2r3
Revises: k7l8m9o0p1q2
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "l8m9o0p1q2r3"
down_revision = "k7l8m9o0p1q2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_prices",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "client_id", "description", name="uq_client_price"),
    )
    op.create_index("ix_client_prices_org_client", "client_prices", ["organization_id", "client_id"])


def downgrade() -> None:
    op.drop_index("ix_client_prices_org_client", table_name="client_prices")
    op.drop_table("client_prices")
