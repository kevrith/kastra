"""merge heads

Revision ID: 9ac2341af6e2
Revises: f2a0fe076c38, z1a2b3c4d5e6
Create Date: 2026-05-23 18:51:02.972013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9ac2341af6e2'
down_revision: Union[str, None] = ('f2a0fe076c38', 'z1a2b3c4d5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
