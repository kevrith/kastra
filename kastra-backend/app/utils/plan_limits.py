from typing import TypedDict


class PlanLimits(TypedDict):
    invoices_per_month: int      # -1 = unlimited
    quotations_per_month: int    # -1 = unlimited
    team_members: int            # -1 = unlimited
    ocr_scans_per_month: int     # -1 = unlimited
    clients: int                 # -1 = unlimited
    templates: list[str]
    watermark: bool
    custom_logo: bool
    paystack: bool
    email_invoices: bool
    auto_reminders: bool
    sms: bool
    client_portal: bool
    expenses: bool
    products: bool
    recurring_invoices: bool
    etims: bool
    reports_months: int          # -1 = unlimited, 0 = dashboard only
    audit_logs: bool
    global_search: bool
    priority_support: bool
    white_label: bool
    suppliers: bool           # supplier management + price comparison portal
    job_profitability: bool   # cost price on items + invoice expense tracking


PLANS: dict[str, PlanLimits] = {
    "free": {
        "invoices_per_month": 20,
        "quotations_per_month": 20,
        "team_members": 1,
        "ocr_scans_per_month": 5,
        "clients": 3,
        "templates": ["classic"],
        "watermark": True,
        "custom_logo": False,
        "paystack": False,
        "email_invoices": False,
        "auto_reminders": False,
        "sms": False,
        "client_portal": False,
        "expenses": False,
        "products": False,
        "recurring_invoices": False,
        "etims": False,
        "reports_months": 0,
        "audit_logs": False,
        "global_search": False,
        "priority_support": False,
        "white_label": False,
        "suppliers": False,
        "job_profitability": False,
    },
    "starter": {
        "invoices_per_month": 200,
        "quotations_per_month": 150,
        "team_members": 3,
        "ocr_scans_per_month": 10,
        "clients": 20,
        "templates": ["classic", "executive"],
        "watermark": False,
        "custom_logo": True,
        "paystack": True,
        "email_invoices": True,
        "auto_reminders": True,
        "sms": False,
        "client_portal": True,
        "expenses": True,
        "products": True,
        "recurring_invoices": False,
        "etims": False,
        "reports_months": 3,
        "audit_logs": False,
        "global_search": True,
        "priority_support": False,
        "white_label": False,
        "suppliers": True,
        "job_profitability": True,
    },
    "business": {
        "invoices_per_month": 400,
        "quotations_per_month": 250,
        "team_members": 6,
        "ocr_scans_per_month": 35,
        "clients": 100,
        "templates": ["classic", "executive", "vivid"],
        "watermark": False,
        "custom_logo": True,
        "paystack": True,
        "email_invoices": True,
        "auto_reminders": True,
        "sms": True,
        "client_portal": True,
        "expenses": True,
        "products": True,
        "recurring_invoices": True,
        "etims": True,
        "reports_months": -1,
        "audit_logs": True,
        "global_search": True,
        "priority_support": False,
        "white_label": False,
        "suppliers": True,
        "job_profitability": True,
    },
    "premium": {
        "invoices_per_month": -1,
        "quotations_per_month": -1,
        "team_members": 15,
        "ocr_scans_per_month": 100,
        "clients": -1,
        "templates": ["classic", "executive", "vivid"],
        "watermark": False,
        "custom_logo": True,
        "paystack": True,
        "email_invoices": True,
        "auto_reminders": True,
        "sms": True,
        "client_portal": True,
        "expenses": True,
        "products": True,
        "recurring_invoices": True,
        "etims": True,
        "reports_months": -1,
        "audit_logs": True,
        "global_search": True,
        "priority_support": True,
        "white_label": True,
        "suppliers": True,
        "job_profitability": True,
    },
}

PLAN_PRICES_KES: dict[str, int] = {
    "free": 0,
    "starter": 1500,
    "business": 3000,
    "premium": 5500,
}

VALID_PLANS = list(PLANS.keys())


def get_limits(plan: str) -> PlanLimits:
    return PLANS.get(plan, PLANS["free"])
