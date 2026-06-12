"""
Payment reconciliation — import an M-Pesa or bank statement CSV and match
incoming transactions to open invoices.

Two-step flow:
  1. POST /api/reconciliation/parse   — upload CSV, get parsed transactions
     with suggested invoice matches (nothing is written).
  2. POST /api/reconciliation/confirm — record the user-approved matches as
     invoice payments.
"""
import csv
import io
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_permission
from app.models.invoice import Invoice, PaymentDetail
from app.models.invoice_payment import InvoicePayment
from app.models.user import User
from app.routers.invoice_payments import _recalculate_status

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])

# Header keywords → canonical column, checked case-insensitively. Covers the
# M-Pesa statement export ("Receipt No.", "Completion Time", "Details",
# "Paid In") and generic bank CSVs (date/reference/description/amount).
_COLUMN_KEYWORDS = {
    "reference": ("receipt no", "receipt", "reference", "ref no", "transaction id", "ref"),
    "date": ("completion time", "date", "time", "transaction date", "value date"),
    "description": ("details", "description", "narrative", "particulars", "transaction details"),
    "amount": ("paid in", "credit", "amount", "deposit", "money in"),
}

_DATE_FORMATS = (
    "%d-%m-%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y",
    "%d %b %Y", "%m/%d/%Y",
)


def _detect_columns(header: list[str]) -> dict[str, int]:
    cols: dict[str, int] = {}
    lowered = [h.strip().lower() for h in header]
    for canonical, keywords in _COLUMN_KEYWORDS.items():
        for kw in keywords:
            for idx, h in enumerate(lowered):
                if kw in h and idx not in cols.values():
                    cols[canonical] = idx
                    break
            if canonical in cols:
                break
    return cols


def _parse_amount(raw: str) -> Decimal | None:
    cleaned = re.sub(r"[^\d.\-]", "", (raw or "").strip())
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _parse_date(raw: str) -> datetime | None:
    raw = (raw or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


class TransactionOut(BaseModel):
    row: int
    reference: str
    date: datetime | None
    description: str
    amount: float
    suggested_invoice_id: str | None
    confidence: str | None  # high | medium
    match_reason: str | None


class OpenInvoiceOut(BaseModel):
    id: str
    client_name: str
    balance_due: float
    due_date: datetime | None


class ParseResult(BaseModel):
    transactions: list[TransactionOut]
    open_invoices: list[OpenInvoiceOut]
    skipped_rows: int


class MatchIn(BaseModel):
    invoice_id: str
    amount: float
    reference: str | None = None
    paid_at: datetime | None = None
    method: str = "mpesa"


class ConfirmRequest(BaseModel):
    matches: list[MatchIn]


class ConfirmResult(BaseModel):
    recorded: int
    skipped: list[dict]


async def _open_invoices(db: AsyncSession, org_id) -> list[Invoice]:
    rows = (await db.execute(
        select(Invoice)
        .where(
            Invoice.organization_id == org_id,
            Invoice.payment_status.in_(["unpaid", "partial"]),
            Invoice.currency == "KES",  # statement amounts are KSh
        )
        .options(selectinload(Invoice.client))
        .order_by(Invoice.created_at.desc())
    )).scalars().all()
    return rows


def _balance(inv: Invoice) -> Decimal:
    return (
        Decimal(str(inv.grand_total))
        - Decimal(str(inv.amount_paid or 0))
        - Decimal(str(inv.amount_credited or 0))
    )


def _suggest_match(txn_ref: str, txn_desc: str, amount: Decimal, invoices: list[Invoice]):
    """Return (invoice_id, confidence, reason) or (None, None, None)."""
    haystack = f"{txn_ref} {txn_desc}".upper()

    # 1) Invoice ID quoted in the transaction
    for inv in invoices:
        if inv.id.upper() in haystack:
            return inv.id, "high", f"Invoice number {inv.id} found in transaction details"

    # 2) Amount exactly matches the balance of exactly one open invoice
    exact = [inv for inv in invoices if abs(_balance(inv) - amount) < Decimal("0.01")]
    if len(exact) == 1:
        return exact[0].id, "medium", f"Amount matches balance due on {exact[0].id}"

    # 3) Client name appears in the details and amount fits within balance
    for inv in invoices:
        name = (inv.client.name if inv.client else "").upper().strip()
        if name and len(name) >= 4 and name in haystack and amount <= _balance(inv) + Decimal("0.01"):
            return inv.id, "medium", f"Client name '{inv.client.name}' found in transaction details"

    return None, None, None


@router.post("/parse", response_model=ParseResult)
async def parse_statement(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_edit_invoices")),
):
    raw = await file.read()
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 2 MB)")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        raise HTTPException(status_code=400, detail="The file is empty or not a valid CSV")

    # The M-Pesa export has preamble lines before the real header — scan for it.
    cols: dict[str, int] = {}
    header_idx = 0
    for idx, row in enumerate(rows[:10]):
        detected = _detect_columns(row)
        if "amount" in detected and ("reference" in detected or "description" in detected):
            cols, header_idx = detected, idx
            break
    if not cols:
        raise HTTPException(
            status_code=400,
            detail="Could not detect statement columns. Expected headers like "
                   "'Receipt No / Reference', 'Details / Description' and 'Paid In / Amount'.",
        )

    invoices = await _open_invoices(db, current_user.organization_id)

    transactions: list[TransactionOut] = []
    skipped = 0
    for row_no, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        def cell(name: str) -> str:
            idx = cols.get(name)
            return row[idx].strip() if idx is not None and idx < len(row) else ""

        amount = _parse_amount(cell("amount"))
        if amount is None or amount <= 0:
            skipped += 1
            continue

        reference = cell("reference")
        description = cell("description")
        inv_id, confidence, reason = _suggest_match(reference, description, amount, invoices)
        transactions.append(TransactionOut(
            row=row_no,
            reference=reference,
            date=_parse_date(cell("date")),
            description=description,
            amount=float(amount),
            suggested_invoice_id=inv_id,
            confidence=confidence,
            match_reason=reason,
        ))

    return ParseResult(
        transactions=transactions,
        open_invoices=[
            OpenInvoiceOut(
                id=inv.id,
                client_name=inv.client.name if inv.client else "",
                balance_due=float(_balance(inv)),
                due_date=inv.due_date,
            )
            for inv in invoices
        ],
        skipped_rows=skipped,
    )


@router.post("/confirm", response_model=ConfirmResult)
async def confirm_matches(
    payload: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_edit_invoices")),
):
    recorded = 0
    skipped: list[dict] = []

    for match in payload.matches:
        inv = (await db.execute(
            select(Invoice)
            .where(
                Invoice.id == match.invoice_id,
                Invoice.organization_id == current_user.organization_id,
            )
            .options(selectinload(Invoice.payment_detail))
        )).scalar_one_or_none()
        if not inv:
            skipped.append({"invoice_id": match.invoice_id, "reason": "Invoice not found"})
            continue
        if inv.payment_status == "paid":
            skipped.append({"invoice_id": match.invoice_id, "reason": "Already fully paid"})
            continue

        balance = float(_balance(inv))
        if match.amount <= 0 or match.amount > balance + 0.01:
            skipped.append({
                "invoice_id": match.invoice_id,
                "reason": f"Amount {match.amount:,.2f} exceeds balance due of {balance:,.2f}",
            })
            continue

        # Skip duplicates: same reference already recorded on this invoice
        if match.reference:
            existing = (await db.execute(
                select(InvoicePayment).where(
                    InvoicePayment.invoice_id == inv.id,
                    InvoicePayment.reference == match.reference,
                )
            )).scalar_one_or_none()
            if existing:
                skipped.append({"invoice_id": match.invoice_id, "reason": f"Reference {match.reference} already recorded"})
                continue

        paid_at = match.paid_at or datetime.now(timezone.utc)
        db.add(InvoicePayment(
            invoice_id=inv.id,
            organization_id=current_user.organization_id,
            amount=match.amount,
            method=match.method,
            reference=match.reference,
            notes="Recorded via statement reconciliation",
            paid_at=paid_at,
        ))
        inv.amount_paid = float(Decimal(str(inv.amount_paid)) + Decimal(str(match.amount)))
        _recalculate_status(inv)
        if inv.payment_status == "paid" and inv.payment_detail is None:
            db.add(PaymentDetail(
                invoice_id=inv.id,
                payment_method=match.method,
                payment_date=paid_at,
                transaction_id=match.reference,
                notes="Statement reconciliation",
            ))
        recorded += 1

    await db.flush()
    return ConfirmResult(recorded=recorded, skipped=skipped)
