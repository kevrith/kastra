import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.testimonial import Testimonial

router = APIRouter(prefix="/api/testimonials", tags=["testimonials"])


class TestimonialOut(BaseModel):
    id: uuid.UUID
    name: str
    role: str | None
    text: str | None
    stars: int | None
    sort_order: int

    model_config = {"from_attributes": True}


class TestimonialSubmit(BaseModel):
    name: str
    role: str
    text: str
    stars: int
    consent: bool


@router.get("", response_model=list[TestimonialOut])
async def list_testimonials(db: AsyncSession = Depends(get_db)):
    """Public endpoint — only approved + active testimonials for the landing page."""
    result = await db.execute(
        select(Testimonial)
        .where(Testimonial.is_active == True, Testimonial.status == "approved")  # noqa: E712
        .order_by(Testimonial.sort_order, Testimonial.created_at)
    )
    return result.scalars().all()


@router.get("/form/{token}")
async def get_testimonial_form(token: str, db: AsyncSession = Depends(get_db)):
    """Return pre-fill data for the customer testimonial form."""
    result = await db.execute(
        select(Testimonial).where(Testimonial.request_token == token)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Invalid or expired link")
    if t.submitted_at is not None:
        raise HTTPException(410, "already_submitted")
    if t.status != "pending":
        raise HTTPException(410, "link_expired")
    return {"name": t.name, "role_hint": t.role or ""}


@router.post("/form/{token}")
async def submit_testimonial(
    token: str,
    payload: TestimonialSubmit,
    db: AsyncSession = Depends(get_db),
):
    """Customer submits their testimonial via the unique link."""
    result = await db.execute(
        select(Testimonial).where(Testimonial.request_token == token)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(404, "Invalid or expired link")
    if t.submitted_at is not None:
        raise HTTPException(410, "already_submitted")
    if t.status != "pending":
        raise HTTPException(410, "link_expired")
    if not payload.consent:
        raise HTTPException(422, "Consent is required to submit a testimonial")

    t.name = payload.name.strip()
    t.role = payload.role.strip()
    t.text = payload.text.strip()
    t.stars = max(1, min(5, payload.stars))
    t.consent = True
    t.submitted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Thank you! Your testimonial has been received and is under review."}
