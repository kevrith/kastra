"""add_organization_prefix

Revision ID: f2a0fe076c38
Revises: 56866bbe3527
Create Date: 2026-05-23 09:30:41.349315

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2a0fe076c38'
down_revision: Union[str, None] = '56866bbe3527'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add prefix column to organizations
    op.add_column('organizations', sa.Column('id_prefix', sa.String(10), nullable=True))
    
    # Generate prefixes for existing organizations
    conn = op.get_bind()
    orgs = conn.execute(sa.text("SELECT id, name FROM organizations")).fetchall()
    
    for org_id, org_name in orgs:
        # Generate prefix from organization name
        # Take first letters of each word, max 5 chars
        words = org_name.upper().split()
        if len(words) >= 2:
            prefix = ''.join(word[0] for word in words[:3])  # e.g., "Kastra Enterprises" -> "KE"
        else:
            prefix = org_name[:3].upper()  # e.g., "Acme" -> "ACM"
        
        # Ensure uniqueness by checking if prefix exists
        existing = conn.execute(
            sa.text("SELECT COUNT(*) FROM organizations WHERE id_prefix = :prefix"),
            {"prefix": prefix}
        ).scalar()
        
        if existing > 0:
            # Add number suffix
            prefix = f"{prefix}{existing + 1}"
        
        conn.execute(
            sa.text("UPDATE organizations SET id_prefix = :prefix WHERE id = :org_id"),
            {"prefix": prefix, "org_id": org_id}
        )
        print(f"Set prefix '{prefix}' for organization '{org_name}'")
    
    # Make column NOT NULL after populating
    op.alter_column('organizations', 'id_prefix', nullable=False)
    
    # Add unique constraint
    op.create_unique_constraint('uq_organizations_id_prefix', 'organizations', ['id_prefix'])


def downgrade() -> None:
    op.drop_constraint('uq_organizations_id_prefix', 'organizations')
    op.drop_column('organizations', 'id_prefix')
