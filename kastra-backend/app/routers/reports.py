import csv
import io
import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.user import User

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/income")
async def income_report(
    year: int = Query(...),
    month: int | None = Query(None, ge=1, le=12),
    client_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(
        extract("month", Invoice.created_at).label("month"),
        func.sum(Invoice.grand_total).label("total"),
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
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(
            Client.id,
            Client.name,
            func.coalesce(func.sum(Invoice.grand_total), 0).label("total_billed"),
            func.count(Invoice.id).label("invoice_count"),
            func.count(Invoice.id).filter(Invoice.payment_status == "paid").label("paid_count"),
        )
        .join(Invoice, Invoice.client_id == Client.id, isouter=True)
        .where(Client.organization_id == current_user.organization_id)
        .group_by(Client.id, Client.name)
        .order_by(func.coalesce(func.sum(Invoice.grand_total), 0).desc())
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


@router.get("/export/csv")
async def export_csv(
    year: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    writer.writerow(["Invoice ID", "Client", "Status", "Subtotal", "VAT", "Grand Total", "Due Date", "Date"])
    for row in rows:
        inv = row.Invoice
        writer.writerow([
            inv.id,
            row.client_name,
            inv.payment_status,
            inv.subtotal,
            inv.vat_amount,
            inv.grand_total,
            inv.due_date.strftime("%d/%m/%Y") if inv.due_date else "",
            inv.created_at.strftime("%d/%m/%Y"),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=kastra-invoices-{year}.csv"},
    )
