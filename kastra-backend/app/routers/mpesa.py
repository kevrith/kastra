import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.invoice import Invoice, PaymentDetail
from app.models.invoice_payment import InvoicePayment
from app.models.notification import Notification
from app.models.organization import Organization
from app.services.audit_service import log_action
from app.services.email_service import send_payment_received_email, send_receipt_email
from app.services.payment_events import publish as publish_payment_event
from app.services.pdf_service import generate_pdf
from app.services.sms_service import sms_payment_received

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mpesa", tags=["mpesa"])

_SAFARICOM_IPS = {
    "196.201.214.200", "196.201.214.206", "196.201.213.114",
    "196.201.214.207", "196.201.214.208", "196.201.213.44",
    "196.201.212.127", "196.201.212.128", "196.201.212.129",
    "196.201.212.132", "196.201.212.136", "196.201.212.138",
}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.post("/callback")
async def mpesa_callback(request: Request, db: AsyncSession = Depends(get_db)):
    if settings.is_production:
        ip = _client_ip(request)
        if ip not in _SAFARICOM_IPS:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    body = await request.json()
    stk_callback = body.get("Body", {}).get("stkCallback", {})
    result_code = stk_callback.get("ResultCode")
    checkout_request_id = stk_callback.get("CheckoutRequestID")

    if not checkout_request_id:
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    result = await db.execute(
        select(Invoice)
        .where(Invoice.mpesa_checkout_request_id == checkout_request_id)
        .options(selectinload(Invoice.client), selectinload(Invoice.organization))
    )
    invoice = result.scalar_one_or_none()

    # Check if this is a subscription payment
    if result_code == 0 and not invoice:
        sub_result = await db.execute(
            select(Organization).where(Organization.sub_mpesa_checkout_id == checkout_request_id)
        )
        org = sub_result.scalar_one_or_none()
        if org and org.pending_plan:
            from app.utils.plan_limits import VALID_PLANS
            from app.utils.billing_events import record_subscription_payment, record_audit
            from datetime import timedelta
            if org.pending_plan in VALID_PLANS:
                now = datetime.now(timezone.utc)
                activated_plan = org.pending_plan
                metadata_items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
                meta_dict = {item["Name"]: item.get("Value") for item in metadata_items}
                receipt = str(meta_dict.get("MpesaReceiptNumber", ""))
                paid_amount = int(meta_dict.get("Amount", 0))
                org.plan = activated_plan
                org.plan_status = "active"
                org.pending_plan = None
                org.sub_mpesa_checkout_id = None
                org.is_trial = False
                org.trial_ends_at = None
                if org.plan != "free":
                    if not org.billing_cycle_start:
                        org.billing_cycle_start = now
                    org.next_billing_date = now + timedelta(days=30)
                await record_subscription_payment(
                    db, org.id, org.name, activated_plan, "mpesa",
                    reference=receipt, amount_kes=paid_amount or None,
                )
                await record_audit(db, "mpesa_payment", str(org.id), org.name, {
                    "plan": activated_plan, "receipt": receipt, "amount_kes": paid_amount,
                }, performed_by="mpesa_callback")
                await db.commit()
                logger.info("M-Pesa subscription activated: org=%s plan=%s", org.id, org.plan)
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    if invoice and result_code == 0:
        metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
        meta = {item["Name"]: item.get("Value") for item in metadata}
        receipt_number = str(meta.get("MpesaReceiptNumber", ""))
        paid_amount = float(meta.get("Amount", invoice.grand_total))

        now = datetime.now(timezone.utc)
        client_name = invoice.client.name if invoice.client else "Client"
        client_email = invoice.client.email if invoice.client else None

        new_total_paid = float(invoice.amount_paid or 0) + paid_amount
        invoice.amount_paid = new_total_paid
        invoice.payment_method = "mpesa"

        if new_total_paid >= float(invoice.grand_total) - 0.01:
            invoice.payment_status = "paid"
        else:
            invoice.payment_status = "partial"

        remaining = float(invoice.grand_total) - new_total_paid
        notif_body = (
            f"{client_name} paid KSh {paid_amount:,.2f} on invoice {invoice.id} via M-Pesa. Receipt: {receipt_number}."
            + (f" Balance remaining: KSh {remaining:,.2f}." if invoice.payment_status == "partial" else " Invoice fully paid.")
        )

        db.add(PaymentDetail(
            invoice_id=invoice.id,
            payment_method="mpesa",
            payment_date=now,
            mpesa_receipt_number=receipt_number,
            transaction_id=checkout_request_id,
        ))
        db.add(InvoicePayment(
            invoice_id=invoice.id,
            organization_id=invoice.organization_id,
            amount=paid_amount,
            method="mpesa",
            reference=receipt_number or checkout_request_id,
            paid_at=now,
        ))
        db.add(Notification(
            organization_id=invoice.organization_id,
            type="payment_received",
            title="M-Pesa payment received",
            body=notif_body,
            entity_id=invoice.id,
        ))

        await log_action(
            db,
            action="payment",
            resource_type="invoice",
            resource_id=invoice.id,
            detail=f"M-Pesa payment confirmed — KSh {paid_amount:,.2f}. Receipt: {receipt_number}. Status: {invoice.payment_status}.",
            organization_id=str(invoice.organization_id),
        )

        # Commit before notifying SSE subscribers so they see the updated status
        await db.commit()
        await publish_payment_event(invoice.id, {
            "payment_status": invoice.payment_status,
            "amount_paid": float(invoice.amount_paid),
            "receipt": receipt_number,
        })

        org_email = invoice.organization.email if invoice.organization else None
        biz_name = invoice.organization.name if invoice.organization else "Business"

        if org_email:
            asyncio.ensure_future(send_payment_received_email(
                org_email=org_email,
                invoice_id=invoice.id,
                amount=paid_amount,
                client_name=client_name,
                receipt_number=receipt_number or None,
            ))

        if client_email:
            from app.schemas.invoice import InvoiceOut
            from app.schemas.organization import OrganizationOut
            _doc = InvoiceOut.model_validate(invoice).model_dump(mode="json")
            _org = OrganizationOut.model_validate(invoice.organization).model_dump(mode="json") if invoice.organization else {}
            _inv_id = invoice.id

            async def _send_receipt_with_pdf():
                try:
                    pdf = await generate_pdf("invoice", _doc, _org)
                except Exception:
                    logger.exception("PDF generation failed for M-Pesa receipt %s", _inv_id)
                    pdf = None
                await send_receipt_email(
                    client_email=client_email,
                    client_name=client_name,
                    invoice_id=_inv_id,
                    amount_paid=paid_amount,
                    business_name=biz_name,
                    receipt_ref=receipt_number or None,
                    pdf_bytes=pdf,
                )
            asyncio.ensure_future(_send_receipt_with_pdf())

        asyncio.ensure_future(sms_payment_received(
            client_phone=invoice.client.phone if invoice.client else None,
            client_name=client_name,
            invoice_id=invoice.id,
            amount=paid_amount,
            business_name=biz_name,
            receipt=receipt_number or None,
            sms_consent=getattr(invoice.client, "sms_consent", False) if invoice.client else False,
        ))

    return {"ResultCode": 0, "ResultDesc": "Accepted"}
