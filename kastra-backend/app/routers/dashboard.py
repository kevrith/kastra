from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.client import Client
from app.models.expense import Expense
from app.models.invoice import Invoice, InvoiceItem
from app.models.quotation import Quotation
from app.models.user import User
from app.schemas.dashboard import (
    DashboardStats,
    KPIStats,
    MonthlyBar,
    RecentInvoice,
    RecentQuotation,
    TopClient,
    YearlyPoint,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    org_id = current_user.organization_id

    # KPIs
    pending_qt = await db.scalar(
        select(func.count(Quotation.id)).where(
            Quotation.organization_id == org_id,
            Quotation.status == "pending",
        )
    )
    unpaid_inv = await db.scalar(
        select(func.count(Invoice.id)).where(
            Invoice.organization_id == org_id,
            Invoice.payment_status == "unpaid",
        )
    )
    monthly_rev = await db.scalar(
        select(func.coalesce(func.sum(Invoice.grand_total * Invoice.exchange_rate), 0)).where(
            Invoice.organization_id == org_id,
            Invoice.payment_status == "paid",
            extract("year", Invoice.created_at) == now.year,
            extract("month", Invoice.created_at) == now.month,
        )
    )
    active_clients = await db.scalar(
        select(func.count(Client.id)).where(
            Client.organization_id == org_id,
            Client.status == "active",
        )
    )
    monthly_expenses = await db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.organization_id == org_id,
            extract("year", Expense.date) == now.year,
            extract("month", Expense.date) == now.month,
        )
    )
    # COGS: sum of cost_price × quantity for all paid invoices this month
    monthly_cogs = await db.scalar(
        select(func.coalesce(func.sum(InvoiceItem.cost_price * InvoiceItem.quantity), 0))
        .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
        .where(
            Invoice.organization_id == org_id,
            Invoice.payment_status == "paid",
            extract("year", Invoice.created_at) == now.year,
            extract("month", Invoice.created_at) == now.month,
            InvoiceItem.cost_price.isnot(None),
        )
    )
    monthly_net_profit = (
        (monthly_rev or Decimal(0))
        - (monthly_expenses or Decimal(0))
        - (monthly_cogs or Decimal(0))
    )

    # Monthly bars — last 6 months
    monthly_bars = []
    for i in range(5, -1, -1):
        month_offset = now.month - i
        year = now.year
        if month_offset <= 0:
            month_offset += 12
            year -= 1
        rev = await db.scalar(
            select(func.coalesce(func.sum(Invoice.grand_total * Invoice.exchange_rate), 0)).where(
                Invoice.organization_id == org_id,
                Invoice.payment_status == "paid",
                extract("year", Invoice.created_at) == year,
                extract("month", Invoice.created_at) == month_offset,
            )
        )
        monthly_bars.append(MonthlyBar(month=f"{MONTH_NAMES[month_offset - 1]} {year}", revenue=rev or Decimal(0)))

    # Yearly trend — last 3 years
    yearly_trend = []
    for y in range(now.year - 2, now.year + 1):
        rev = await db.scalar(
            select(func.coalesce(func.sum(Invoice.grand_total * Invoice.exchange_rate), 0)).where(
                Invoice.organization_id == org_id,
                Invoice.payment_status == "paid",
                extract("year", Invoice.created_at) == y,
            )
        )
        yearly_trend.append(YearlyPoint(year=y, revenue=rev or Decimal(0)))

    # Top 5 clients
    top_result = await db.execute(
        select(
            Client.id,
            Client.name,
            func.coalesce(func.sum(Invoice.grand_total * Invoice.exchange_rate), 0).label("total_billed"),
            func.count(Invoice.id).label("invoice_count"),
        )
        .join(Invoice, Invoice.client_id == Client.id, isouter=True)
        .where(Client.organization_id == org_id)
        .group_by(Client.id, Client.name)
        .order_by(func.coalesce(func.sum(Invoice.grand_total * Invoice.exchange_rate), 0).desc())
        .limit(5)
    )
    top_clients = [
        TopClient(id=str(r.id), name=r.name, total_billed=r.total_billed, invoice_count=r.invoice_count)
        for r in top_result.all()
    ]

    # Recent quotations
    qt_result = await db.execute(
        select(Quotation, Client.name.label("client_name"))
        .join(Client, Quotation.client_id == Client.id)
        .where(Quotation.organization_id == org_id)
        .order_by(Quotation.created_at.desc())
        .limit(5)
    )
    recent_quotations = [
        RecentQuotation(
            id=row.Quotation.id,
            client_name=row.client_name,
            status=row.Quotation.status,
            currency=row.Quotation.currency,
            grand_total=row.Quotation.grand_total,
            created_at=row.Quotation.created_at.strftime("%d/%m/%Y"),
        )
        for row in qt_result.all()
    ]

    # Recent invoices
    inv_result = await db.execute(
        select(Invoice, Client.name.label("client_name"))
        .join(Client, Invoice.client_id == Client.id)
        .where(Invoice.organization_id == org_id)
        .order_by(Invoice.created_at.desc())
        .limit(5)
    )
    recent_invoices = [
        RecentInvoice(
            id=row.Invoice.id,
            client_name=row.client_name,
            payment_status=row.Invoice.payment_status,
            currency=row.Invoice.currency,
            grand_total=row.Invoice.grand_total,
            created_at=row.Invoice.created_at.strftime("%d/%m/%Y"),
        )
        for row in inv_result.all()
    ]

    return DashboardStats(
        kpis=KPIStats(
            pending_quotations=pending_qt or 0,
            unpaid_invoices=unpaid_inv or 0,
            monthly_revenue=monthly_rev or Decimal(0),
            active_clients=active_clients or 0,
            monthly_expenses=monthly_expenses or Decimal(0),
            monthly_net_profit=monthly_net_profit,
        ),
        monthly_bars=monthly_bars,
        yearly_trend=yearly_trend,
        top_clients=top_clients,
        recent_quotations=recent_quotations,
        recent_invoices=recent_invoices,
    )
