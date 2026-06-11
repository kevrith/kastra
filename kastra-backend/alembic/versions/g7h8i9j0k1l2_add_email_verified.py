"""add email_verified to users

Revision ID: g7h8i9j0k1l2
Revises: af01_add_affiliate_system
Create Date: 2026-06-11

Existing users are backfilled as verified (server_default='true') so no
one gets locked out.  New signups created by the app explicitly set
email_verified=False and must click the activation link.
"""
from alembic import op
import sqlalchemy as sa

revision = "g7h8i9j0k1l2"
down_revision = "af01_add_affiliate_system"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add with TRUE default so every existing row is treated as verified.
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="true"),
    )
    # Change the DB default to FALSE so new rows that don't pass the value
    # explicitly get the right default.
    op.alter_column("users", "email_verified", server_default="false")


def downgrade() -> None:
    op.drop_column("users", "email_verified")
