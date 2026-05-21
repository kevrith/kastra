from decimal import Decimal

from pydantic import BaseModel


class KPIStats(BaseModel):
    pending_quotations: int
    unpaid_invoices: int
    monthly_revenue: Decimal
    active_clients: int
    monthly_expenses: Decimal = Decimal(0)
    monthly_net_profit: Decimal = Decimal(0)


class MonthlyBar(BaseModel):
    month: str  # e.g. "Jan 2026"
    revenue: Decimal


class YearlyPoint(BaseModel):
    year: int
    revenue: Decimal


class TopClient(BaseModel):
    id: str
    name: str
    total_billed: Decimal
    invoice_count: int


class RecentQuotation(BaseModel):
    id: str
    client_name: str
    status: str
    grand_total: Decimal
    created_at: str


class RecentInvoice(BaseModel):
    id: str
    client_name: str
    payment_status: str
    grand_total: Decimal
    created_at: str


class DashboardStats(BaseModel):
    kpis: KPIStats
    monthly_bars: list[MonthlyBar]
    yearly_trend: list[YearlyPoint]
    top_clients: list[TopClient]
    recent_quotations: list[RecentQuotation]
    recent_invoices: list[RecentInvoice]
