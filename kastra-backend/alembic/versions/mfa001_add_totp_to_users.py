"""add TOTP two-factor columns to users

Revision ID: mfa001_add_totp
Revises: rls002_rls_sweep
Create Date: 2026-09-02 00:00:00.000000

Backward compatible: every column is nullable or has a server default, so the
previous release keeps working against this schema. `totp_enabled` defaults to
false, which means existing users are unaffected until they opt in.
"""
import sqlalchemy as sa
from alembic import op

revision = "mfa001_add_totp"
down_revision = "rls002_rls_sweep"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The secret is encrypted application-side (EncryptedString), hence Text
    # rather than a fixed-width base32 column.
    op.add_column("users", sa.Column("totp_secret", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("totp_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("totp_backup_codes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "totp_backup_codes")
    op.drop_column("users", "totp_confirmed_at")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
