"""cleanup_orphaned_quotations

Revision ID: 1f739b662efe
Revises: 4f2f00067280
Create Date: 2026-05-23 09:19:14.953116

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1f739b662efe'
down_revision: Union[str, None] = '4f2f00067280'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Delete orphaned quotations that have no items (failed during creation)
    conn = op.get_bind()
    
    # Find quotations with no items
    orphaned = conn.execute(sa.text("""
        SELECT q.id FROM quotations q
        LEFT JOIN quotation_items qi ON q.id = qi.quotation_id
        WHERE qi.id IS NULL
    """)).fetchall()
    
    if orphaned:
        orphaned_ids = [row[0] for row in orphaned]
        print(f"Deleting {len(orphaned_ids)} orphaned quotations: {orphaned_ids}")
        
        # Delete orphaned quotations
        for qid in orphaned_ids:
            conn.execute(sa.text("DELETE FROM quotations WHERE id = :id"), {"id": qid})
    
    # Reset sequence counters to match actual data
    conn.execute(sa.text("""
        UPDATE sequence_counters sc
        SET last_sequence_number = COALESCE(
            (SELECT MAX(CAST(SUBSTRING(q.id FROM '[0-9]+$') AS INTEGER))
             FROM quotations q
             WHERE q.organization_id = sc.organization_id
               AND EXTRACT(YEAR FROM q.created_at) = sc.year),
            0
        )
        WHERE sc.entity_type = 'quotation'
    """))
    
    conn.execute(sa.text("""
        UPDATE sequence_counters sc
        SET last_sequence_number = COALESCE(
            (SELECT MAX(CAST(SUBSTRING(i.id FROM '[0-9]+$') AS INTEGER))
             FROM invoices i
             WHERE i.organization_id = sc.organization_id
               AND EXTRACT(YEAR FROM i.created_at) = sc.year),
            0
        )
        WHERE sc.entity_type = 'invoice'
    """))


def downgrade() -> None:
    # No downgrade - data cleanup is one-way
    pass
