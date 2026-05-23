import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.models.invoice import SequenceCounter


async def next_id(db: AsyncSession, entity_type: str, organization_id: uuid.UUID) -> str:
    """Generate next sequential ID per org like QT-2026-001 or INV-2026-001."""
    year = datetime.now(timezone.utc).year
    prefix = "QT" if entity_type == "quotation" else "INV"

    # Use PostgreSQL's INSERT ... ON CONFLICT to atomically get or create counter
    stmt = insert(SequenceCounter).values(
        organization_id=organization_id,
        entity_type=entity_type,
        year=year,
        last_sequence_number=1,
    ).on_conflict_do_update(
        index_elements=['organization_id', 'entity_type', 'year'],
        set_={'last_sequence_number': SequenceCounter.last_sequence_number + 1}
    ).returning(SequenceCounter.last_sequence_number)

    result = await db.execute(stmt)
    seq = result.scalar_one()

    return f"{prefix}-{year}-{seq:03d}"
