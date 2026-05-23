import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import SequenceCounter


async def next_id(db: AsyncSession, entity_type: str, organization_id: uuid.UUID) -> str:
    """Generate next sequential ID per org like QT-2026-001 or INV-2026-001."""
    from sqlalchemy.exc import IntegrityError
    import logging
    
    logger = logging.getLogger(__name__)
    year = datetime.now(timezone.utc).year
    prefix = "QT" if entity_type == "quotation" else "INV"

    logger.info(f"Generating {entity_type} ID for org {organization_id}, year {year}")

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
        logger.info(f"Counter not found, creating new one for org {organization_id}")
        # Create new counter - handle race condition with merge
        counter = SequenceCounter(
            organization_id=organization_id,
            entity_type=entity_type,
            year=year,
            last_sequence_number=0,  # Start at 0, will increment to 1
        )
        try:
            db.add(counter)
            await db.flush()
            logger.info(f"Counter created successfully for org {organization_id}")
        except IntegrityError as e:
            logger.warning(f"IntegrityError creating counter for org {organization_id}: {e}")
            # Counter was created by another request, fetch it
            await db.rollback()
            # Re-fetch in a new transaction context
            result = await db.execute(
                select(SequenceCounter).where(
                    SequenceCounter.organization_id == organization_id,
                    SequenceCounter.entity_type == entity_type,
                    SequenceCounter.year == year,
                ).with_for_update()
            )
            counter = result.scalar_one_or_none()
            if counter is None:
                logger.error(f"Counter still not found after rollback for org {organization_id}")
                # Still not found, something is wrong - create it anyway
                counter = SequenceCounter(
                    organization_id=organization_id,
                    entity_type=entity_type,
                    year=year,
                    last_sequence_number=0,
                )
                db.add(counter)
                await db.flush()
    else:
        logger.info(f"Counter found for org {organization_id}, current value: {counter.last_sequence_number}")
    
    # Increment counter
    counter.last_sequence_number += 1
    seq = counter.last_sequence_number
    logger.info(f"Generated ID: {prefix}-{year}-{seq:03d} for org {organization_id}")

    return f"{prefix}-{year}-{seq:03d}"
