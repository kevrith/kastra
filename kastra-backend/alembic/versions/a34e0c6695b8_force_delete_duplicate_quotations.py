"""force_delete_duplicate_quotations

Revision ID: a34e0c6695b8
Revises: 1f739b662efe
Create Date: 2026-05-23 09:22:44.903527

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a34e0c6695b8'
down_revision: Union[str, None] = '1f739b662efe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    
    # Delete all quotations and invoices for organization db10428e-036a-4615-aac1-9498ac8ff6ef
    # This is the test org that has corrupted data
    org_id = 'db10428e-036a-4615-aac1-9498ac8ff6ef'
    
    print(f"Cleaning up data for organization {org_id}")
    
    # Delete quotation items first (foreign key)
    result = conn.execute(sa.text("""
        DELETE FROM quotation_items 
        WHERE quotation_id IN (
            SELECT id FROM quotations WHERE organization_id = :org_id
        )
    """), {"org_id": org_id})
    print(f"Deleted {result.rowcount} quotation items")
    
    # Delete quotation charges
    result = conn.execute(sa.text("""
        DELETE FROM quotation_charges 
        WHERE quotation_id IN (
            SELECT id FROM quotations WHERE organization_id = :org_id
        )
    """), {"org_id": org_id})
    print(f"Deleted {result.rowcount} quotation charges")
    
    # Delete quotations
    result = conn.execute(sa.text("""
        DELETE FROM quotations WHERE organization_id = :org_id
    """), {"org_id": org_id})
    print(f"Deleted {result.rowcount} quotations")
    
    # Reset sequence counter for this org
    conn.execute(sa.text("""
        UPDATE sequence_counters 
        SET last_sequence_number = 0 
        WHERE organization_id = :org_id AND entity_type = 'quotation'
    """), {"org_id": org_id})
    print(f"Reset sequence counter for organization {org_id}")


def downgrade() -> None:
    # No downgrade - data cleanup is one-way
    pass
