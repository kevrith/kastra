"""add_project_id_to_expenses

Revision ID: 77727c417e3d
Revises: x0y1z2a3b4c5
Create Date: 2026-05-23 01:03:35.225482

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '77727c417e3d'
down_revision: Union[str, None] = 'x0y1z2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('expenses', sa.Column('project_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_expenses_project_id', 'expenses', 'projects', ['project_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_expenses_project_id', 'expenses', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_expenses_project_id', 'expenses')
    op.drop_constraint('fk_expenses_project_id', 'expenses', type_='foreignkey')
    op.drop_column('expenses', 'project_id')
