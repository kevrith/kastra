"""encrypt credential columns — widen to TEXT for encrypted storage

Revision ID: a2b3c4d5e6f7
Revises: z1a2b3c4d5e6
Create Date: 2026-06-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "a2b3c4d5e6f7"
down_revision = "z1a2b3c4d5e6"
branch_labels = None
depends_on = None

COLUMNS = [
    "paystack_secret_key",
    "mpesa_consumer_key",
    "mpesa_consumer_secret",
    "mpesa_passkey",
    "etims_auth_token",
]


def upgrade():
    for col in COLUMNS:
        op.alter_column(
            "organizations",
            col,
            existing_type=sa.String(255),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade():
    for col in COLUMNS:
        op.alter_column(
            "organizations",
            col,
            existing_type=sa.Text(),
            type_=sa.String(255),
            existing_nullable=True,
        )
