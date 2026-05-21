from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.quotation import Quotation
from app.models.user import User

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchResult(BaseModel):
    type: str  # client | invoice | quotation
    id: str
    label: str
    sub: str | None = None


@router.get("", response_model=list[SearchResult])
async def global_search(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if len(q.strip()) < 2:
        return []

    pat = f"%{q.strip()}%"
    org_id = current_user.organization_id
    results: list[SearchResult] = []

    # Clients
    clients = (await db.execute(
        select(Client)
        .where(
            Client.organization_id == org_id,
            or_(Client.name.ilike(pat), Client.email.ilike(pat), Client.phone.ilike(pat)),
        )
        .limit(5)
    )).scalars().all()
    for c in clients:
        results.append(SearchResult(type="client", id=str(c.id), label=c.name, sub=c.email or c.phone))

    # Invoices
    invoices = (await db.execute(
        select(Invoice)
        .where(Invoice.organization_id == org_id, Invoice.id.ilike(pat))
        .limit(5)
    )).scalars().all()
    for inv in invoices:
        results.append(SearchResult(type="invoice", id=inv.id, label=inv.id, sub=f"KSh {float(inv.grand_total):,.2f} · {inv.payment_status}"))

    # Quotations
    quotations = (await db.execute(
        select(Quotation)
        .where(Quotation.organization_id == org_id, Quotation.id.ilike(pat))
        .limit(5)
    )).scalars().all()
    for qt in quotations:
        results.append(SearchResult(type="quotation", id=qt.id, label=qt.id, sub=f"KSh {float(qt.grand_total):,.2f} · {qt.status}"))

    return results
