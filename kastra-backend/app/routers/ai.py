import base64
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.client import Client
from app.models.expense import Expense
from app.models.invoice import Invoice
from app.models.organization import Organization
from app.models.user import User
from app.utils.plan_limits import get_limits

router = APIRouter(prefix="/api/ai", tags=["ai"])

# Cached system prompt for Haiku (re-used across all non-vision calls)
_SYSTEM = (
    "You are a financial assistant for a Kenyan small business management platform. "
    "Always respond with valid JSON only — no markdown, no explanation, no code fences."
)


def _get_client(api_key: str):
    try:
        import anthropic as _anthropic
        return _anthropic.Anthropic(api_key=api_key)
    except ImportError:
        raise HTTPException(503, "AI service unavailable. Run: pip install anthropic")


def _maybe_reset_counters(org) -> None:
    now = datetime.now(timezone.utc)
    reset_at = org.counters_reset_at
    if reset_at is None or (now.year > reset_at.year or now.month > reset_at.month):
        org.invoices_this_month = 0
        org.quotations_this_month = 0
        org.ocr_scans_this_month = 0
        org.ai_calls_this_month = 0
        org.counters_reset_at = now


async def _check_ai_access(org: Organization) -> None:
    """Raise 402/503 if AI features aren't available or limit is hit."""
    if not settings.anthropic_api_key:
        raise HTTPException(503, "AI service not configured. Set ANTHROPIC_API_KEY in backend .env.")
    limits = get_limits(org.plan)
    if not limits["ai_features"]:
        raise HTTPException(402, f"AI features are not available on the {org.plan} plan. Upgrade to Starter or higher.")
    cap = limits["ai_calls_per_month"]
    if cap != -1 and org.ai_calls_this_month >= cap:
        raise HTTPException(
            402,
            f"AI call limit reached ({cap}/month on {org.plan} plan). Upgrade for more AI calls.",
        )


async def _get_org(user: User, db: AsyncSession) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == user.organization_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(404, "Organization not found")
    _maybe_reset_counters(org)
    return org


# ─────────────────────────────────────────────
# 1. Suggest invoice line items for a client
# ─────────────────────────────────────────────

class SuggestItemsRequest(BaseModel):
    client_id: uuid.UUID
    count: int = 5


class SuggestedItem(BaseModel):
    description: str
    quantity: float
    unit_price: float


class SuggestItemsResponse(BaseModel):
    items: list[SuggestedItem]


@router.post("/suggest-items", response_model=SuggestItemsResponse)
async def suggest_items(
    req: SuggestItemsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org = await _get_org(current_user, db)
    await _check_ai_access(org)

    # Fetch last 10 invoices for this client (with items)
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.items))
        .where(
            and_(
                Invoice.organization_id == org.id,
                Invoice.client_id == req.client_id,
            )
        )
        .order_by(Invoice.created_at.desc())
        .limit(10)
    )
    invoices = result.scalars().all()

    if not invoices:
        return SuggestItemsResponse(items=[])

    # Build a compact history string
    history_lines = []
    for inv in invoices:
        for it in inv.items:
            history_lines.append(
                f"- {it.description} | qty {float(it.quantity)} | KES {float(it.unit_price)}"
            )
    history = "\n".join(history_lines[:60])  # cap to avoid huge prompts

    client_result = await db.execute(select(Client).where(Client.id == req.client_id))
    client = client_result.scalar_one_or_none()
    client_name = client.name if client else "this client"

    prompt = (
        f"Here are the past invoice line items for {client_name}:\n{history}\n\n"
        f"Suggest the {req.count} most likely line items they will order again. "
        "Use realistic quantities and prices based on the history. "
        "Return JSON: {\"items\": [{\"description\": str, \"quantity\": number, \"unit_price\": number}]}"
    )

    ai = _get_client(settings.anthropic_api_key)
    try:
        message = ai.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        raise HTTPException(502, f"AI service error: {e}")

    try:
        data = json.loads(message.content[0].text.strip())
    except Exception:
        raise HTTPException(502, "AI returned unreadable data.")

    items = []
    for it in data.get("items", []):
        try:
            items.append(SuggestedItem(
                description=str(it["description"]).strip(),
                quantity=float(it.get("quantity", 1)),
                unit_price=float(it.get("unit_price", 0)),
            ))
        except (KeyError, TypeError, ValueError):
            continue

    org.ai_calls_this_month += 1
    await db.commit()
    return SuggestItemsResponse(items=items)


# ─────────────────────────────────────────────
# 2. Categorize expense from receipt image
# ─────────────────────────────────────────────

_EXPENSE_CATEGORIES = [
    "rent", "salaries", "utilities", "supplies", "materials",
    "labour", "lunch", "transport", "fuel", "other",
]

_EXPENSE_SYSTEM = (
    "You are a receipt data extraction assistant for a Kenyan business platform. "
    "Extract expense details from the receipt image. "
    "Always respond with valid JSON only — no markdown, no explanation."
)

_EXPENSE_PROMPT = (
    "Extract the following from this receipt image:\n"
    "1. vendor: business/store name\n"
    "2. amount: total amount paid (number, no currency symbol)\n"
    "3. date: date on receipt in YYYY-MM-DD format (null if not visible)\n"
    "4. description: brief description of what was purchased\n"
    "5. category: best matching category from this list: "
    + ", ".join(_EXPENSE_CATEGORIES)
    + "\n\n"
    "Return JSON: {\"vendor\": str|null, \"amount\": number|null, \"date\": str|null, "
    "\"description\": str, \"category\": str}"
)


class CategorizeExpenseRequest(BaseModel):
    image_base64: str
    media_type: str = "image/jpeg"


class CategorizeExpenseResponse(BaseModel):
    vendor: str | None
    amount: float | None
    date: str | None
    description: str
    category: str


@router.post("/categorize-expense", response_model=CategorizeExpenseResponse)
async def categorize_expense(
    req: CategorizeExpenseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org = await _get_org(current_user, db)
    await _check_ai_access(org)

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if req.media_type not in allowed_types:
        raise HTTPException(400, f"Unsupported media type. Use: {', '.join(allowed_types)}")
    try:
        base64.b64decode(req.image_base64, validate=True)
    except Exception:
        raise HTTPException(400, "Invalid base64 image data.")

    ai = _get_client(settings.anthropic_api_key)
    try:
        message = ai.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=_EXPENSE_SYSTEM,
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
                        {"type": "text", "text": _EXPENSE_PROMPT},
                    ],
                }
            ],
        )
    except Exception as e:
        raise HTTPException(502, f"AI service error: {e}")

    raw = message.content[0].text.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
        else:
            raise HTTPException(502, "AI returned unreadable data. Try a clearer image.")

    category = data.get("category", "other")
    if category not in _EXPENSE_CATEGORIES:
        category = "other"

    amount_raw = data.get("amount")
    amount = None
    if amount_raw is not None:
        try:
            amount = float(amount_raw)
        except (TypeError, ValueError):
            amount = None

    org.ai_calls_this_month += 1
    await db.commit()

    return CategorizeExpenseResponse(
        vendor=data.get("vendor") or None,
        amount=amount,
        date=data.get("date") or None,
        description=str(data.get("description", "")).strip() or "Expense",
        category=category,
    )


# ─────────────────────────────────────────────
# 3. Cash flow forecast (30-day)
# ─────────────────────────────────────────────

class CashFlowForecastResponse(BaseModel):
    summary: str
    overdue_amount: float
    expected_inflow_30d: float
    expected_outflow_30d: float
    net_30_days: float
    warnings: list[str]


@router.get("/cash-flow-forecast", response_model=CashFlowForecastResponse)
async def cash_flow_forecast(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org = await _get_org(current_user, db)
    await _check_ai_access(org)

    now = datetime.now(timezone.utc)
    in_30 = now + timedelta(days=30)

    # Overdue invoices (unpaid/partial, due_date < now)
    overdue_result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.organization_id == org.id,
                Invoice.payment_status.in_(["unpaid", "partial"]),
                Invoice.due_date < now,
            )
        )
    )
    overdue_invoices = overdue_result.scalars().all()
    overdue_amount = sum(float(i.grand_total) - float(i.amount_paid) for i in overdue_invoices)

    # Invoices due in next 30 days (expected inflow)
    upcoming_result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.organization_id == org.id,
                Invoice.payment_status.in_(["unpaid", "partial"]),
                Invoice.due_date >= now,
                Invoice.due_date <= in_30,
            )
        )
    )
    upcoming_invoices = upcoming_result.scalars().all()
    expected_inflow = sum(float(i.grand_total) - float(i.amount_paid) for i in upcoming_invoices)

    # Average monthly expenses (last 3 months)
    three_months_ago = now - timedelta(days=90)
    expense_result = await db.execute(
        select(Expense).where(
            and_(
                Expense.organization_id == org.id,
                Expense.date >= three_months_ago.date(),
            )
        )
    )
    expenses = expense_result.scalars().all()
    total_expense_3m = sum(float(e.amount) for e in expenses)
    avg_monthly_expense = total_expense_3m / 3
    expected_outflow = avg_monthly_expense  # one month estimate

    net = expected_inflow - expected_outflow

    prompt = (
        f"Business financial snapshot for a Kenyan SME:\n"
        f"- Overdue receivables (unpaid past due): KES {overdue_amount:,.0f} "
        f"across {len(overdue_invoices)} invoice(s)\n"
        f"- Expected inflow next 30 days: KES {expected_inflow:,.0f} "
        f"across {len(upcoming_invoices)} invoice(s)\n"
        f"- Average monthly expenses (last 3 months): KES {avg_monthly_expense:,.0f}/month\n"
        f"- Projected net cash position in 30 days: KES {net:,.0f}\n\n"
        "Write a concise 2-3 sentence cash flow summary and list 1-3 actionable warnings if any. "
        "Return JSON: {\"summary\": str, \"warnings\": [str]}"
    )

    ai = _get_client(settings.anthropic_api_key)
    try:
        message = ai.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        raise HTTPException(502, f"AI service error: {e}")

    try:
        data = json.loads(message.content[0].text.strip())
    except Exception:
        data = {"summary": "Unable to generate forecast summary.", "warnings": []}

    org.ai_calls_this_month += 1
    await db.commit()

    return CashFlowForecastResponse(
        summary=data.get("summary", ""),
        overdue_amount=overdue_amount,
        expected_inflow_30d=expected_inflow,
        expected_outflow_30d=expected_outflow,
        net_30_days=net,
        warnings=data.get("warnings", []),
    )


# ─────────────────────────────────────────────
# 4. Generate quotation description from bullets
# ─────────────────────────────────────────────

class GenerateDescriptionRequest(BaseModel):
    bullets: str
    context: str = ""


class GenerateDescriptionResponse(BaseModel):
    description: str


@router.post("/generate-description", response_model=GenerateDescriptionResponse)
async def generate_description(
    req: GenerateDescriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org = await _get_org(current_user, db)
    await _check_ai_access(org)

    if not req.bullets.strip():
        raise HTTPException(400, "Provide bullet points to expand.")

    context_line = f"Context: {req.context.strip()}\n" if req.context.strip() else ""
    prompt = (
        f"{context_line}"
        f"Convert these bullet points into a professional, concise quotation scope/description "
        f"suitable for a Kenyan business document:\n{req.bullets}\n\n"
        "Write 2-4 sentences. Be clear and professional. No fluff. "
        "Return JSON: {\"description\": str}"
    )

    ai = _get_client(settings.anthropic_api_key)
    try:
        message = ai.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        raise HTTPException(502, f"AI service error: {e}")

    try:
        data = json.loads(message.content[0].text.strip())
        description = str(data.get("description", "")).strip()
    except Exception:
        description = message.content[0].text.strip()

    if not description:
        raise HTTPException(502, "AI returned an empty description.")

    org.ai_calls_this_month += 1
    await db.commit()

    return GenerateDescriptionResponse(description=description)


# ─────────────────────────────────────────────
# 5. Late payment risk score for a client
# ─────────────────────────────────────────────

class ClientRiskResponse(BaseModel):
    score: int           # 1 (low risk) – 5 (high risk)
    label: str           # "Low" | "Medium" | "High" | "Very High" | "Critical"
    reason: str
    late_count: int
    total_invoices: int
    avg_days_late: float


_RISK_LABELS = {1: "Low", 2: "Medium", 3: "High", 4: "Very High", 5: "Critical"}


@router.get("/client-risk/{client_id}", response_model=ClientRiskResponse)
async def client_risk(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org = await _get_org(current_user, db)
    await _check_ai_access(org)

    result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.organization_id == org.id,
                Invoice.client_id == client_id,
            )
        ).order_by(Invoice.created_at.desc()).limit(50)
    )
    invoices = result.scalars().all()

    if not invoices:
        return ClientRiskResponse(
            score=1, label="Low", reason="No invoice history — insufficient data to assess risk.",
            late_count=0, total_invoices=0, avg_days_late=0.0,
        )

    # Compute payment stats from the data directly
    late_count = 0
    days_late_list: list[float] = []
    unpaid_overdue = 0
    total_overdue_amount = 0.0
    now = datetime.now(timezone.utc)

    for inv in invoices:
        if inv.payment_status == "paid":
            # Check if paid late (updated_at vs due_date)
            if inv.due_date and inv.updated_at and inv.updated_at > inv.due_date:
                days_late = (inv.updated_at - inv.due_date).days
                late_count += 1
                days_late_list.append(float(days_late))
        elif inv.payment_status in ("unpaid", "partial"):
            if inv.due_date and now > inv.due_date:
                unpaid_overdue += 1
                total_overdue_amount += float(inv.grand_total) - float(inv.amount_paid)

    avg_days_late = sum(days_late_list) / len(days_late_list) if days_late_list else 0.0
    total = len(invoices)
    late_rate = (late_count + unpaid_overdue) / total if total else 0

    prompt = (
        f"Payment risk assessment for a client:\n"
        f"- Total invoices: {total}\n"
        f"- Paid late: {late_count} time(s)\n"
        f"- Currently overdue unpaid: {unpaid_overdue} invoice(s) totalling KES {total_overdue_amount:,.0f}\n"
        f"- Average days late when they do pay: {avg_days_late:.1f} days\n"
        f"- Late payment rate: {late_rate:.0%}\n\n"
        "Rate the risk on a scale of 1-5 (1=low, 5=critical) and give a one-sentence reason. "
        "Return JSON: {\"score\": int, \"reason\": str}"
    )

    ai = _get_client(settings.anthropic_api_key)
    try:
        message = ai.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(message.content[0].text.strip())
        score = max(1, min(5, int(data.get("score", 2))))
        reason = str(data.get("reason", "")).strip()
    except Exception:
        # Fallback: compute score from data without AI narrative
        if late_rate >= 0.6 or unpaid_overdue >= 3:
            score = 5
        elif late_rate >= 0.4 or unpaid_overdue >= 2:
            score = 4
        elif late_rate >= 0.25 or unpaid_overdue >= 1:
            score = 3
        elif late_rate >= 0.1 or late_count >= 1:
            score = 2
        else:
            score = 1
        reason = f"Based on {late_count} late payment(s) out of {total} invoice(s)."

    org.ai_calls_this_month += 1
    await db.commit()

    return ClientRiskResponse(
        score=score,
        label=_RISK_LABELS[score],
        reason=reason,
        late_count=late_count,
        total_invoices=total,
        avg_days_late=round(avg_days_late, 1),
    )
