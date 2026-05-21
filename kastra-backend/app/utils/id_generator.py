import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import SequenceCounter


async def next_id(db: AsyncSession, entity_type: str, organization_id: uuid.UUID) -> str:
    """Generate next sequential ID per org like QT-2026-001 or INV-2026-001."""
    year = datetime.now(timezone.utc).year
    prefix = "QT" if entity_type == "quotation" else "INV"

    result = await db.execute(
        select(SequenceCounter).where(
            SequenceCounter.organization_id == organization_id,
            SequenceCounter.entity_type == entity_type,
            SequenceCounter.year == year,
        ).with_for_update()
    )
    counter = result.scalar_one_or_none()

    if counter is None:
        counter = SequenceCounter(
            organization_id=organization_id,
            entity_type=entity_type,
            year=year,
            last_sequence_number=1,
        )
        db.add(counter)
        seq = 1
    else:
        counter.last_sequence_number += 1
        seq = counter.last_sequence_number

    return f"{prefix}-{year}-{seq:03d}"
