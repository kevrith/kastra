"""fix_sequence_counters_primary_key

Revision ID: 4f2f00067280
Revises: 77727c417e3d
Create Date: 2026-05-23 09:15:06.501224

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4f2f00067280'
down_revision: Union[str, None] = '77727c417e3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old primary key constraint
    op.drop_constraint('sequence_counters_pkey', 'sequence_counters', type_='primary')
    
    # Create new primary key with organization_id included
    op.create_primary_key('sequence_counters_pkey', 'sequence_counters', ['organization_id', 'entity_type', 'year'])


def downgrade() -> None:
    # Revert to old primary key (not recommended, but for completeness)
    op.drop_constraint('sequence_counters_pkey', 'sequence_counters', type_='primary')
    op.create_primary_key('sequence_counters_pkey', 'sequence_counters', ['entity_type', 'year'])
