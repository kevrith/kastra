import csv
import io
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response as RawResponse, StreamingResponse
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_permission
from app.models.client import Client
from app.models.credit_note import CreditNote
from app.models.invoice import Invoice
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationOut
from app.services.pdf_service import generate_statement_pdf

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/income")
async def income_report(
    year: int = Query(...),
    month: int | None = Query(None, ge=1, le=12),
    client_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_reports")),
):
    q = select(
        extract("month", Invoice.created_at).label("month"),
        func.sum(Invoice.grand_total * Invoice.exchange_rate).label("total"),
        func.count(Invoice.id).label("count"),
    ).where(
        Invoice.organization_id == current_user.organization_id,
        Invoice.payment_status == "paid",
        extract("year", Invoice.created_at) == year,
    )
    if month:
        q = q.where(extract("month", Invoice.created_at) == month)
    if client_id:
        q = q.where(Invoice.client_id == client_id)

    q = q.group_by(extract("month", Invoice.created_at)).order_by(extract("month", Invoice.created_at))
    result = await db.execute(q)
    rows = result.all()
    return {"data": [{"month": int(r.month), "total": r.total, "count": r.count} for r in rows]}


@router.get("/clients")
async def client_revenue_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_reports")),
):
    result = await db.execute(
        select(
            Client.id,
            Client.name,
            func.coalesce(func.sum(Invoice.grand_total * Invoice.exchange_rate), 0).label("total_billed"),
            func.count(Invoice.id).label("invoice_count"),
            func.count(Invoice.id).filter(Invoice.payment_status == "paid").label("paid_count"),
        )
        .join(Invoice, Invoice.client_id == Client.id, isouter=True)
        .where(Client.organization_id == current_user.organization_id)
        .group_by(Client.id, Client.name)
        .order_by(func.coalesce(func.sum(Invoice.grand_total * Invoice.exchange_rate), 0).desc())
    )
    rows = result.all()
    return {
        "data": [
            {
                "id": str(r.id),
                "name": r.name,
                "total_billed": r.total_billed,
                "invoice_count": r.invoice_count,
                "paid_count": r.paid_count,
            }
            for r in rows
        ]
    }


@router.get("/aging")
async def debtor_aging_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_reports")),
):
    """
    Debtor aging: outstanding balances per client bucketed by days overdue
    (current / 1-30 / 31-60 / 61-90 / 90+). Amounts in KES equivalent.
    """
    result = await db.execute(
        select(Invoice, Client.name.label("client_name"))
        .join(Client, Invoice.client_id == Client.id)
        .where(
            Invoice.organization_id == current_user.organization_id,
            Invoice.payment_status.in_(["unpaid", "partial"]),
        )
    )
    rows = result.all()

    now = datetime.now(timezone.utc)
    buckets = ("current", "d1_30", "d31_60", "d61_90", "d90_plus")
    clients: dict[str, dict] = {}
    for row in rows:
        inv = row.Invoice
        outstanding = (
            Decimal(str(inv.grand_total))
            - Decimal(str(inv.amount_paid or 0))
            - Decimal(str(inv.amount_credited or 0))
        ) * Decimal(str(inv.exchange_rate))
        if outstanding <= 0:
            continue

        if inv.due_date is None or inv.due_date >= now:
            bucket = "current"
        else:
            days = (now - inv.due_date).days
            if days <= 30:
                bucket = "d1_30"
            elif days <= 60:
                bucket = "d31_60"
            elif days <= 90:
                bucket = "d61_90"
            else:
                bucket = "d90_plus"

        key = str(inv.client_id)
        entry = clients.setdefault(key, {
            "client_id": key,
            "client_name": row.client_name,
            **{b: Decimal("0") for b in buckets},
            "total": Decimal("0"),
            "invoice_count": 0,
        })
        entry[bucket] += outstanding
        entry["total"] += outstanding
        entry["invoice_count"] += 1

    data = sorted(clients.values(), key=lambda c: c["total"], reverse=True)
    totals = {b: sum(c[b] for c in data) for b in buckets}
    totals["total"] = sum(c["total"] for c in data)

    def _f(d):
        return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in d.items()}

    return {"data": [_f(c) for c in data], "totals": _f(totals)}


async def _build_statement(
    db: AsyncSession,
    org_id,
    client_id: uuid.UUID,
    date_from: datetime | None,
    date_to: datetime,
) -> dict:
    """Build a client statement: chronological debits (invoices) and credits
    (payments, credit notes) with running balance, all in KES equivalent."""
    if date_from and date_from.tzinfo is None:
        date_from = date_from.replace(tzinfo=timezone.utc)
    if date_to.tzinfo is None:
        date_to = date_to.replace(tzinfo=timezone.utc)

    client = (await db.execute(
        select(Client).where(Client.id == client_id, Client.organization_id == org_id)
    )).scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    invoices = (await db.execute(
        select(Invoice)
        .where(
            Invoice.organization_id == org_id,
            Invoice.client_id == client_id,
            Invoice.created_at <= date_to,
        )
        .options(selectinload(Invoice.payments))
    )).scalars().all()

    credit_notes = (await db.execute(
        select(CreditNote).where(
            CreditNote.organization_id == org_id,
            CreditNote.client_id == client_id,
            CreditNote.created_at <= date_to,
        )
    )).scalars().all()

    events = []
    for inv in invoices:
        rate = Decimal(str(inv.exchange_rate))
        events.append({
            "date": inv.invoice_date or inv.created_at,
            "reference": inv.id,
            "description": f"Invoice {inv.id}" + (f" ({inv.currency})" if inv.currency != "KES" else ""),
            "debit": Decimal(str(inv.grand_total)) * rate,
            "credit": Decimal("0"),
        })
        for p in inv.payments:
            if p.paid_at <= date_to:
                events.append({
                    "date": p.paid_at,
                    "reference": p.reference or inv.id,
                    "description": f"Payment — {p.method} ({inv.id})",
                    "debit": Decimal("0"),
                    "credit": Decimal(str(p.amount)) * rate,
                })
    for cn in credit_notes:
        events.append({
            "date": cn.created_at,
            "reference": cn.id,
            "description": f"Credit note ({cn.invoice_id})",
            "debit": Decimal("0"),
            "credit": Decimal(str(cn.grand_total)) * Decimal(str(cn.exchange_rate)),
        })

    events.sort(key=lambda e: e["date"])

    opening = Decimal("0")
    lines = []
    if date_from:
        for e in events:
            if e["date"] < date_from:
                opening += e["debit"] - e["credit"]
        period_events = [e for e in events if e["date"] >= date_from]
    else:
        period_events = events

    balance = opening
    total_invoiced = Decimal("0")
    total_paid = Decimal("0")
    total_credited = Decimal("0")
    for e in period_events:
        balance += e["debit"] - e["credit"]
        total_invoiced += e["debit"]
        if "Credit note" in e["description"]:
            total_credited += e["credit"]
        else:
            total_paid += e["credit"]
        lines.append({
            "date": e["date"].isoformat(),
            "reference": e["reference"],
            "description": e["description"],
            "debit": float(e["debit"]) or None,
            "credit": float(e["credit"]) or None,
            "balance": float(balance),
        })

    return {
        "client": {
            "id": str(client.id),
            "name": client.name,
            "email": client.email,
            "address": client.address,
        },
        "date_from": (date_from or (events[0]["date"] if events else date_to)).isoformat(),
        "date_to": date_to.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "opening_balance": float(opening),
        "total_invoiced": float(total_invoiced),
        "total_paid": float(total_paid),
        "total_credited": float(total_credited),
        "closing_balance": float(balance),
        "lines": lines,
    }


@router.get("/statement/{client_id}")
async def client_statement(
    client_id: uuid.UUID,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_reports")),
):
    date_to = date_to or datetime.now(timezone.utc)
    statement = await _build_statement(db, current_user.organization_id, client_id, date_from, date_to)
    return {"data": statement}


@router.get("/statement/{client_id}/pdf")
async def client_statement_pdf(
    client_id: uuid.UUID,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_reports")),
):
    date_to = date_to or datetime.now(timezone.utc)
    statement = await _build_statement(db, current_user.organization_id, client_id, date_from, date_to)

    org = (await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )).scalar_one()
    org_data = OrganizationOut.model_validate(org).model_dump(mode="json")

    pdf_bytes = await generate_statement_pdf(statement, org_data)
    client_slug = statement["client"]["name"].replace(" ", "-").lower()
    return RawResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="statement-{client_slug}.pdf"'},
    )


@router.get("/export/csv")
async def export_csv(
    year: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("can_view_reports")),
):
    result = await db.execute(
        select(Invoice, Client.name.label("client_name"))
        .join(Client, Invoice.client_id == Client.id)
        .where(
            Invoice.organization_id == current_user.organization_id,
            extract("year", Invoice.created_at) == year,
        )
        .options(selectinload(Invoice.items))
        .order_by(Invoice.created_at)
    )
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Invoice ID", "Client", "Status", "Currency", "Subtotal", "VAT", "Grand Total", "KES Equivalent", "Due Date", "Date"])
    for row in rows:
        inv = row.Invoice
        writer.writerow([
            inv.id,
            row.client_name,
            inv.payment_status,
            inv.currency,
            inv.subtotal,
            inv.vat_amount,
            inv.grand_total,
            (inv.grand_total * inv.exchange_rate).quantize(Decimal("0.01")),
            inv.due_date.strftime("%d/%m/%Y") if inv.due_date else "",
            inv.created_at.strftime("%d/%m/%Y"),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=kastra-invoices-{year}.csv"},
    )
