"""add project_description and quotation_notes table

Revision ID: v8w9x0y1z2a3
Revises: u7v8w9x0y1z2
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "v8w9x0y1z2a3"
down_revision = "u7v8w9x0y1z2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("quotations", sa.Column("project_description", sa.Text(), nullable=True))

    op.create_table(
        "quotation_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("quotation_id", sa.String(20), sa.ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_quotation_notes_quotation_id", "quotation_notes", ["quotation_id"])


def downgrade() -> None:
    op.drop_index("ix_quotation_notes_quotation_id", "quotation_notes")
    op.drop_table("quotation_notes")
    op.drop_column("quotations", "project_description")
