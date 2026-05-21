"""
Paystack card payment integration.
Uses redirect flow: initialize → hosted page → verify/webhook confirms payment.
Supports partial payments: pass `amount` to initialize; actual paid amount
is read from Paystack response and accumulated on invoice.amount_paid.
"""
import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.invoice import Invoice, PaymentDetail
from app.models.invoice_payment import InvoicePayment
from app.models.notification import Notification
from app.services.audit_service import log_action
from app.services.email_service import send_payment_received_email, send_receipt_email
from app.services.payment_events import publish as publish_payment_event
from app.services.pdf_service import generate_pdf
from app.services.sms_service import sms_payment_received

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/paystack", tags=["paystack"])

PAYSTACK_API = "https://api.paystack.co"


class PaystackInitRequest(BaseModel):
    invoice_id: str
    email: str
    amount: float | None = None  # optional partial amount; defaults to balance due


def _org_paystack_key(org) -> str:
    if org and getattr(org, "paystack_secret_key", None):
        return org.paystack_secret_key
    return settings.paystack_secret_key


async def _record_card_payment(db: AsyncSession, invoice: Invoice, paid_amount: float, reference: str, card_note: str):
    """Accumulate a card payment on invoice, setting partial or paid status."""
    now = datetime.now(timezone.utc)
    client_name = invoice.client.name if invoice.client else "Client"

    new_total_paid = float(invoice.amount_paid or 0) + paid_amount
    invoice.amount_paid = new_total_paid
    invoice.payment_method = "card"

    if new_total_paid >= float(invoice.grand_total) - 0.01:
        invoice.payment_status = "paid"
        status_label = "paid"
    else:
        invoice.payment_status = "partial"
        status_label = "partial"

    db.add(PaymentDetail(
        invoice_id=invoice.id,
        payment_method="card",
        payment_date=now,
        transaction_id=reference,
        notes=card_note,
    ))
    db.add(InvoicePayment(
        invoice_id=invoice.id,
        organization_id=invoice.organization_id,
        amount=paid_amount,
        method="paystack",
        reference=reference,
        notes=card_note,
        paid_at=now,
    ))

    remaining = float(invoice.grand_total) - new_total_paid
    notif_body = (
        f"{client_name} paid KSh {paid_amount:,.2f} on invoice {invoice.id} via card."
        + (f" Balance remaining: KSh {remaining:,.2f}." if status_label == "partial" else " Invoice fully paid.")
    )
    db.add(Notification(
        organization_id=invoice.organization_id,
        type="payment_received",
        title="Card payment received",
        body=notif_body,
        entity_id=invoice.id,
    ))

    await log_action(
        db,
        action="payment",
        resource_type="invoice",
        resource_id=invoice.id,
        detail=f"Card payment via Paystack — KSh {paid_amount:,.2f}. Reference: {reference}. Status: {status_label}.",
        organization_id=str(invoice.organization_id),
    )

    org_email = invoice.organization.email if invoice.organization else None
    if org_email:
        asyncio.ensure_future(send_payment_received_email(
            org_email=org_email,
            invoice_id=invoice.id,
            amount=paid_amount,
            client_name=client_name,
            receipt_number=reference,
        ))

    return invoice.payment_status


def _fire_post_payment(invoice: Invoice, paid_amount: float, reference: str) -> None:
    """Fire SSE, PDF receipt email, and SMS after a commit."""
    client_name = invoice.client.name if invoice.client else "Client"
    client_email = invoice.client.email if invoice.client else None
    biz_name = invoice.organization.name if invoice.organization else "Business"

    asyncio.ensure_future(publish_payment_event(invoice.id, {
        "payment_status": invoice.payment_status,
        "amount_paid": float(invoice.amount_paid),
        "receipt": reference,
    }))

    if client_email:
        from app.schemas.invoice import InvoiceOut
        from app.schemas.organization import OrganizationOut
        _doc = InvoiceOut.model_validate(invoice).model_dump(mode="json")
        _org = OrganizationOut.model_validate(invoice.organization).model_dump(mode="json") if invoice.organization else {}
        _inv_id = invoice.id

        async def _send_receipt():
            try:
                pdf = await generate_pdf("invoice", _doc, _org)
            except Exception:
                logger.exception("PDF generation failed for Paystack receipt %s", _inv_id)
                pdf = None
            await send_receipt_email(
                client_email=client_email,
                client_name=client_name,
                invoice_id=_inv_id,
                amount_paid=paid_amount,
                business_name=biz_name,
                receipt_ref=reference,
                pdf_bytes=pdf,
            )
        asyncio.ensure_future(_send_receipt())

    asyncio.ensure_future(sms_payment_received(
        client_phone=invoice.client.phone if invoice.client else None,
        client_name=client_name,
        invoice_id=invoice.id,
        amount=paid_amount,
        business_name=biz_name,
        receipt=reference,
    ))


@router.post("/initialize")
async def initialize_payment(payload: PaystackInitRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Invoice).where(Invoice.id == payload.invoice_id).options(selectinload(Invoice.organization))
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Invoice is already paid")

    balance_due = float(inv.grand_total) - float(inv.amount_paid or 0)
    charge = payload.amount if payload.amount else balance_due

    if charge <= 0 or charge > balance_due + 0.01:
        raise HTTPException(status_code=400, detail=f"Amount must be between 1 and {balance_due:.2f}")

    amount_cents = int(charge * 100)
    callback_url = f"{settings.frontend_url}/portal/paystack/verify"
    secret_key = _org_paystack_key(inv.organization)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYSTACK_API}/transaction/initialize",
            headers={
                "Authorization": f"Bearer {secret_key}",
                "Content-Type": "application/json",
            },
            json={
                "email": payload.email,
                "amount": amount_cents,
                "reference": f"{payload.invoice_id}-{int(datetime.now().timestamp())}",
                "callback_url": callback_url,
                "currency": "KES",
                "metadata": {"invoice_id": payload.invoice_id},
            },
        )

    if not resp.is_success:
        detail = resp.json().get("message", "Failed to initialize Paystack payment")
        raise HTTPException(status_code=502, detail=detail)

    data = resp.json()["data"]
    return {
        "authorization_url": data["authorization_url"],
        "reference": data["reference"],
    }


@router.get("/verify/{reference}")
async def verify_payment(reference: str, db: AsyncSession = Depends(get_db)):
    """
    Called by frontend immediately after Paystack redirect.
    Verifies with Paystack and records payment — no webhook dependency.
    Handles partial payments: uses actual amount paid from Paystack response.
    """
    # reference format: {invoice_id}-{timestamp}; extract invoice_id
    invoice_id = reference.rsplit("-", 1)[0] if "-" in reference else reference

    result = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(selectinload(Invoice.client), selectinload(Invoice.organization))
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    secret_key = _org_paystack_key(invoice.organization)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PAYSTACK_API}/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {secret_key}"},
        )

    if not resp.is_success:
        raise HTTPException(status_code=502, detail="Could not reach Paystack to verify payment")

    data = resp.json().get("data", {})
    ps_status = data.get("status")
    paid_amount = data.get("amount", 0) / 100  # Paystack returns kobo/cents

    if ps_status != "success":
        return {
            "status": ps_status or "failed",
            "invoice_id": invoice.id,
            "amount": paid_amount,
            "balance_due": float(invoice.grand_total) - float(invoice.amount_paid or 0),
            "business_name": invoice.organization.name if invoice.organization else "",
        }

    # Idempotency check — don't double-record the same reference
    existing = await db.execute(
        select(InvoicePayment).where(InvoicePayment.reference == reference)
    )
    if existing.scalar_one_or_none():
        new_status = invoice.payment_status
    else:
        auth = data.get("authorization", {})
        card_note = f"Paystack: {auth.get('card_type', 'card')} ending {auth.get('last4', '****')}"
        new_status = await _record_card_payment(db, invoice, paid_amount, reference, card_note)
        await db.commit()
        _fire_post_payment(invoice, paid_amount, reference)

    balance_due = float(invoice.grand_total) - float(invoice.amount_paid or 0)
    return {
        "status": new_status,
        "invoice_id": invoice.id,
        "amount": paid_amount,
        "balance_due": max(0.0, balance_due),
        "business_name": invoice.organization.name if invoice.organization else "",
    }


@router.post("/webhook")
async def paystack_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    event = json.loads(body)
    if event.get("event") != "charge.success":
        return {"status": "ignored"}

    data = event.get("data", {})
    reference = data.get("reference", "")
    if not reference:
        return {"status": "no reference"}

    # Check if this is a subscription payment (reference starts with SUB-)
    meta = data.get("metadata", {})
    if reference.startswith("SUB-") or meta.get("type") == "subscription":
        import uuid
        from app.models.organization import Organization
        from datetime import timedelta
        from app.utils.plan_limits import VALID_PLANS
        org_id_str = meta.get("org_id", "")
        plan = meta.get("plan", "")
        if org_id_str and plan and plan in VALID_PLANS:
            try:
                org_uuid = uuid.UUID(org_id_str)
                org_res = await db.execute(select(Organization).where(Organization.id == org_uuid))
                org = org_res.scalar_one_or_none()
                if org:
                    from app.utils.billing_events import record_subscription_payment, record_audit
                    now = datetime.now(timezone.utc)
                    paid_amount = int(data.get("amount", 0) / 100)  # Paystack sends kobo
                    org.plan = plan
                    org.plan_status = "active"
                    org.pending_plan = None
                    org.is_trial = False
                    org.trial_ends_at = None
                    if not org.billing_cycle_start:
                        org.billing_cycle_start = now
                    org.next_billing_date = now + timedelta(days=30)
                    await record_subscription_payment(
                        db, org.id, org.name, plan, "paystack",
                        reference=reference, amount_kes=paid_amount or None,
                    )
                    await record_audit(db, "paystack_payment", str(org.id), org.name, {
                        "plan": plan, "reference": reference, "amount_kes": paid_amount,
                    }, performed_by="paystack_webhook")
                    await db.commit()
                    logger.info("Paystack subscription webhook: org=%s plan=%s ref=%s", org_id_str, plan, reference)
            except Exception:
                logger.exception("Error processing Paystack subscription webhook for ref=%s", reference)
        return {"status": "ok"}

    invoice_id = reference.rsplit("-", 1)[0] if "-" in reference else reference

    result = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(selectinload(Invoice.client), selectinload(Invoice.organization))
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        return {"status": "ok"}

    # Verify HMAC using org's key
    secret_key = _org_paystack_key(invoice.organization)
    if secret_key != "sk_test_placeholder":
        expected = hmac.new(
            secret_key.encode("utf-8"),
            body,
            hashlib.sha512,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=400, detail="Invalid signature")

    # Idempotency check
    existing = await db.execute(
        select(InvoicePayment).where(InvoicePayment.reference == reference)
    )
    if existing.scalar_one_or_none():
        return {"status": "ok"}

    paid_amount = data.get("amount", 0) / 100
    auth = data.get("authorization", {})
    card_note = f"Paystack: {auth.get('card_type', 'card')} ending {auth.get('last4', '****')}"

    await _record_card_payment(db, invoice, paid_amount, reference, card_note)
    await db.commit()
    _fire_post_payment(invoice, paid_amount, reference)
    return {"status": "ok"}
