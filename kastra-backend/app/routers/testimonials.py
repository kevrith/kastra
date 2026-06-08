import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.testimonial import Testimonial

router = APIRouter(prefix="/api/testimonials", tags=["testimonials"])


class TestimonialOut(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    text: str
    stars: int
    sort_order: int

    model_config = {"from_attributes": True}


@router.get("", response_model=list[TestimonialOut])
async def list_testimonials(db: AsyncSession = Depends(get_db)):
    """Public endpoint — returns active testimonials for the landing page."""
    result = await db.execute(
        select(Testimonial)
        .where(Testimonial.is_active == True)  # noqa: E712
        .order_by(Testimonial.sort_order, Testimonial.created_at)
    )
    return result.scalars().all()
