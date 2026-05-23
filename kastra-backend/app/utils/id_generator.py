import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import SequenceCounter


async def next_id(db: AsyncSession, entity_type: str, organization_id: uuid.UUID) -> str:
    """Generate next sequential ID per org like QT-2026-001 or INV-2026-001."""
    from sqlalchemy.exc import IntegrityError
    
    year = datetime.now(timezone.utc).year
    prefix = "QT" if entity_type == "quotation" else "INV"

    # Try to fetch and lock counter
    result = await db.execute(
        select(SequenceCounter).where(
            SequenceCounter.organization_id == organization_id,
            SequenceCounter.entity_type == entity_type,
            SequenceCounter.year == year,
        ).with_for_update()
    )
    counter = result.scalar_one_or_none()

    if counter is None:
        # Create new counter - handle race condition
        counter = SequenceCounter(
            organization_id=organization_id,
            entity_type=entity_type,
            year=year,
            last_sequence_number=1,
        )
        db.add(counter)
        try:
            await db.flush()
            seq = 1
        except IntegrityError:
            # Another request created it, rollback and retry
            await db.rollback()
            result = await db.execute(
                select(SequenceCounter).where(
                    SequenceCounter.organization_id == organization_id,
                    SequenceCounter.entity_type == entity_type,
                    SequenceCounter.year == year,
                ).with_for_update()
            )
            counter = result.scalar_one()
            counter.last_sequence_number += 1
            seq = counter.last_sequence_number
    else:
        # Increment existing counter
        counter.last_sequence_number += 1
        seq = counter.last_sequence_number

    return f"{prefix}-{year}-{seq:03d}"
