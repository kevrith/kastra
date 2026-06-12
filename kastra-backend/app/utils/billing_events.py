"""Helpers for recording subscription payment events and admin audit log entries."""

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_audit_log import AdminAuditLog
from app.models.subscription_payment import SubscriptionPayment
from app.utils.plan_limits import PLAN_PRICES_KES


async def record_subscription_payment(
    db: AsyncSession,
    org_id: uuid.UUID,
    org_name: str,
    plan: str,
    payment_method: str,
    reference: str | None = None,
    amount_kes: int | None = None,
) -> None:
    amount = amount_kes if amount_kes is not None else PLAN_PRICES_KES.get(plan, 0)
    payment = SubscriptionPayment(
        organization_id=org_id,
        org_name=org_name,
        amount_kes=amount,
        plan=plan,
        payment_method=payment_method,
        reference=reference,
        status="completed",
    )
    db.add(payment)


async def record_audit(
    db: AsyncSession,
    action: str,
    org_id: str,
    org_name: str,
    details: dict | None = None,
    performed_by: str = "superadmin",
) -> None:
    entry = AdminAuditLog(
        action=action,
        target_org_id=org_id,
        target_org_name=org_name,
        details=json.dumps(details) if details else None,
        performed_by=performed_by,
    )
    db.add(entry)
