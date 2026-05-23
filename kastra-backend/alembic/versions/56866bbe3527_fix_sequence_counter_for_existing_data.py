"""fix_sequence_counter_for_existing_data

Revision ID: 56866bbe3527
Revises: a34e0c6695b8
Create Date: 2026-05-23 09:24:05.660039

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '56866bbe3527'
down_revision: Union[str, None] = 'a34e0c6695b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    
    print("Fixing sequence counters to match existing quotations and invoices...")
    
    # For each organization, find the max sequence number from existing quotations
    # and update the counter accordingly
    
    # Get all organizations
    orgs = conn.execute(sa.text("SELECT id FROM organizations")).fetchall()
    
    for (org_id,) in orgs:
        # Find max quotation number for this org in 2026
        max_qt = conn.execute(sa.text("""
            SELECT MAX(CAST(SUBSTRING(id FROM '[0-9]+$') AS INTEGER))
            FROM quotations
            WHERE organization_id = :org_id
              AND id LIKE 'QT-2026-%'
        """), {"org_id": org_id}).scalar()
        
        if max_qt:
            # Update or insert counter
            existing = conn.execute(sa.text("""
                SELECT 1 FROM sequence_counters
                WHERE organization_id = :org_id
                  AND entity_type = 'quotation'
                  AND year = 2026
            """), {"org_id": org_id}).scalar()
            
            if existing:
                conn.execute(sa.text("""
                    UPDATE sequence_counters
                    SET last_sequence_number = :max_num
                    WHERE organization_id = :org_id
                      AND entity_type = 'quotation'
                      AND year = 2026
                """), {"org_id": org_id, "max_num": max_qt})
                print(f"Updated quotation counter for org {org_id} to {max_qt}")
            else:
                conn.execute(sa.text("""
                    INSERT INTO sequence_counters (organization_id, entity_type, year, last_sequence_number)
                    VALUES (:org_id, 'quotation', 2026, :max_num)
                """), {"org_id": org_id, "max_num": max_qt})
                print(f"Created quotation counter for org {org_id} with value {max_qt}")
        
        # Same for invoices
        max_inv = conn.execute(sa.text("""
            SELECT MAX(CAST(SUBSTRING(id FROM '[0-9]+$') AS INTEGER))
            FROM invoices
            WHERE organization_id = :org_id
              AND id LIKE 'INV-2026-%'
        """), {"org_id": org_id}).scalar()
        
        if max_inv:
            existing = conn.execute(sa.text("""
                SELECT 1 FROM sequence_counters
                WHERE organization_id = :org_id
                  AND entity_type = 'invoice'
                  AND year = 2026
            """), {"org_id": org_id}).scalar()
            
            if existing:
                conn.execute(sa.text("""
                    UPDATE sequence_counters
                    SET last_sequence_number = :max_num
                    WHERE organization_id = :org_id
                      AND entity_type = 'invoice'
                      AND year = 2026
                """), {"org_id": org_id, "max_num": max_inv})
                print(f"Updated invoice counter for org {org_id} to {max_inv}")
            else:
                conn.execute(sa.text("""
                    INSERT INTO sequence_counters (organization_id, entity_type, year, last_sequence_number)
                    VALUES (:org_id, 'invoice', 2026, :max_num)
                """), {"org_id": org_id, "max_num": max_inv})
                print(f"Created invoice counter for org {org_id} with value {max_inv}")
    
    print("Sequence counters fixed successfully!")


def downgrade() -> None:
    # No downgrade needed
    pass
