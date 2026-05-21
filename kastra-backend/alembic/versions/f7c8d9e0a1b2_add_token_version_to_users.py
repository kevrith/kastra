"""add_token_version_to_users

Revision ID: f7c8d9e0a1b2
Revises: da817823e711
Create Date: 2026-05-20 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f7c8d9e0a1b2'
down_revision: Union[str, None] = 'da817823e711'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=True))
    op.execute("UPDATE users SET token_version = 0 WHERE token_version IS NULL")
    op.alter_column('users', 'token_version', nullable=False)


def downgrade() -> None:
    op.drop_column('users', 'token_version')
