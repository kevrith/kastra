"""add is_trial and trial_ends_at to organizations

Revision ID: q3r4s5t6u7v8
Revises: p2q3r4s5t6u7
Create Date: 2026-05-21

"""
from alembic import op
import sqlalchemy as sa

revision = "q3r4s5t6u7v8"
down_revision = "p2q3r4s5t6u7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("is_trial", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("organizations", sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "trial_ends_at")
    op.drop_column("organizations", "is_trial")
