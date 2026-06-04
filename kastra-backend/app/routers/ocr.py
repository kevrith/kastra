import base64
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.models.user import User
from app.utils.plan_limits import get_limits

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


def _maybe_reset_counters(org) -> None:
    now = datetime.now(timezone.utc)
    reset_at = org.counters_reset_at
    if reset_at is None or (now.year > reset_at.year or now.month > reset_at.month):
        org.invoices_this_month = 0
        org.quotations_this_month = 0
        org.ocr_scans_this_month = 0
        org.ai_calls_this_month = 0
        org.counters_reset_at = now

_SYSTEM = """You are a receipt/quotation data extraction assistant for a Kenyan business platform.
Extract line items, client name, and any notes from the provided image.
Always respond with valid JSON only — no markdown, no explanation.
Amounts should be numbers (no currency symbols).
If you cannot read a field clearly, omit it rather than guessing."""

_PROMPT = """Extract the following from this receipt, quotation, or invoice image:
1. Line items: description, quantity, unit_price
2. Client/customer details: name, phone number, email address (each if visible)
3. Document date (the invoice/receipt/quotation date, if visible) in YYYY-MM-DD format
4. Any notes, terms, or instructions (if visible)

Respond ONLY with this JSON structure:
{
  "client_name": "string or null",
  "client_phone": "string or null",
  "client_email": "string or null",
  "receipt_date": "YYYY-MM-DD or null",
  "notes": "string or null",
  "items": [
    {
      "description": "string",
      "quantity": number,
      "unit_price": number
    }
  ]
}"""


class OcrScanRequest(BaseModel):
    image_base64: str  # base64-encoded image data
    media_type: str = "image/jpeg"  # image/jpeg | image/png | image/webp


class OcrItem(BaseModel):
    description: str
    quantity: float
    unit_price: float


class OcrScanResponse(BaseModel):
    client_name: str | None
    client_phone: str | None = None
    client_email: str | None = None
    receipt_date: str | None = None
    notes: str | None
    items: list[OcrItem]


@router.post("/scan", response_model=OcrScanResponse)
async def scan_receipt(
    req: OcrScanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Enforce plan OCR limit
    org_result = await db.execute(select(Organization).where(Organization.id == current_user.organization_id))
    org = org_result.scalar_one_or_none()
    if org:
        limits = get_limits(org.plan)
        _maybe_reset_counters(org)
        cap = limits["ocr_scans_per_month"]
        if cap != -1 and org.ocr_scans_this_month >= cap:
            raise HTTPException(
                status_code=402,
                detail=f"OCR scan limit reached ({cap}/month on {org.plan} plan). Upgrade for more scans.",
            )

    if not settings.anthropic_api_key:
        raise HTTPException(503, "OCR service not configured. Set ANTHROPIC_API_KEY in backend .env.")

    try:
        import anthropic as _anthropic
    except ImportError:
        raise HTTPException(503, "OCR service unavailable. Run: pip install anthropic")

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if req.media_type not in allowed_types:
        raise HTTPException(400, f"Unsupported media type. Use: {', '.join(allowed_types)}")

    try:
        base64.b64decode(req.image_base64, validate=True)
    except Exception:
        raise HTTPException(400, "Invalid base64 image data.")

    client = _anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": req.media_type,
                                "data": req.image_base64,
                            },
                        },
                        {"type": "text", "text": _PROMPT},
                    ],
                }
            ],
        )
    except _anthropic.APIError as e:
        raise HTTPException(502, f"OCR service error: {str(e)}")

    raw = message.content[0].text.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to find JSON block in response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
        else:
            raise HTTPException(502, "OCR returned unreadable data. Try a clearer image.")

    items = []
    for it in data.get("items", []):
        desc = str(it.get("description", "")).strip()
        if not desc:
            continue
        try:
            qty = float(it.get("quantity", 1))
            price = float(it.get("unit_price", 0))
        except (TypeError, ValueError):
            qty, price = 1.0, 0.0
        items.append(OcrItem(description=desc, quantity=qty, unit_price=price))

    if org:
        org.ocr_scans_this_month += 1
        await db.commit()

    return OcrScanResponse(
        client_name=data.get("client_name") or None,
        client_phone=data.get("client_phone") or None,
        client_email=data.get("client_email") or None,
        receipt_date=data.get("receipt_date") or None,
        notes=data.get("notes") or None,
        items=items,
    )
