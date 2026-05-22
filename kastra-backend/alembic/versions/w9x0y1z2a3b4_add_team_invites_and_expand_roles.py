"""add team invites and expand roles

Revision ID: w9x0y1z2a3b4
Revises: v8w9x0y1z2a3
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "w9x0y1z2a3b4"
down_revision = "v8w9x0y1z2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add invite fields to users table
    op.add_column("users", sa.Column("invite_token", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("invite_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("invited_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("users", sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True))
    
    op.create_index("ix_users_invite_token", "users", ["invite_token"])


def downgrade() -> None:
    op.drop_index("ix_users_invite_token", "users")
    op.drop_column("users", "invited_at")
    op.drop_column("users", "invited_by")
    op.drop_column("users", "invite_token_expires_at")
    op.drop_column("users", "invite_token")
