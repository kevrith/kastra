import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.client import Client
from app.models.testimonial import Testimonial
from app.models.user import User
from app.services.email_service import send_testimonial_request_email

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


class TestimonialRequestIn(BaseModel):
    client_id: uuid.UUID
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    role_hint: str | None = None


class TestimonialRequestOut(BaseModel):
    message: str
    whatsapp_link: str | None = None


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


@router.post("/request", response_model=TestimonialRequestOut)
async def request_testimonial(
    payload: TestimonialRequestIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Org user requests a testimonial from one of their clients."""
    if not payload.email and not payload.phone:
        raise HTTPException(400, "Provide at least an email or phone number")

    result = await db.execute(
        select(Client).where(
            Client.id == payload.client_id,
            Client.organization_id == current_user.organization_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Client not found")

    token = secrets.token_urlsafe(32)
    from app.config import settings
    form_url = f"{settings.primary_frontend_url}/testimonial/{token}"

    t = Testimonial(
        id=uuid.uuid4(),
        name=payload.name.strip(),
        role=payload.role_hint or None,
        status="pending",
        request_token=token,
        requested_email=payload.email,
        requested_phone=payload.phone.strip() if payload.phone else None,
        requested_at=datetime.now(timezone.utc),
        consent=False,
        is_active=True,
        sort_order=0,
    )
    db.add(t)
    await db.commit()

    if payload.email:
        await send_testimonial_request_email(payload.email, payload.name.strip(), form_url)

    whatsapp_link: str | None = None
    if payload.phone:
        from urllib.parse import quote
        msg = (
            f"Hi {payload.name.strip()}, we'd love to hear your feedback! "
            f"Please share a quick testimonial (2 min): {form_url}"
        )
        whatsapp_link = f"https://wa.me/{payload.phone.strip().lstrip('+').replace(' ', '')}?text={quote(msg)}"

    contact = payload.email or payload.phone
    return TestimonialRequestOut(
        message=f"Request sent to {contact}",
        whatsapp_link=whatsapp_link,
    )
