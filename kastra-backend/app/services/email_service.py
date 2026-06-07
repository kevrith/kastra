import logging
from datetime import datetime, timedelta, timezone

import httpx
from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger(__name__)

_RESET_SECRET = settings.secret_key + "-reset"
_RESET_EXPIRE_MINUTES = 30


def create_password_reset_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=_RESET_EXPIRE_MINUTES)
    return jwt.encode({"sub": email, "exp": expire, "type": "reset"}, _RESET_SECRET, algorithm="HS256")


def verify_password_reset_token(token: str) -> str:
    payload = jwt.decode(token, _RESET_SECRET, algorithms=["HS256"])
    if payload.get("type") != "reset":
        raise JWTError("Invalid token type")
    return payload["sub"]


async def _send_via_sendgrid(to_email: str, subject: str, html: str) -> None:
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": settings.mail_from, "name": "Kastra"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
        )
        resp.raise_for_status()


async def _send(to_email: str, subject: str, html: str) -> None:
    if settings.is_production and settings.sendgrid_api_key:
        try:
            await _send_via_sendgrid(to_email, subject, html)
        except Exception:
            logger.exception("SendGrid error sending to %s", to_email)
    else:
        logger.info("[DEV EMAIL] To: %s | Subject: %s", to_email, subject)


async def send_password_reset_email(email: str, reset_token: str) -> None:
    reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"
    html = f"""
    <p>Hi,</p>
    <p>Click the link below to reset your Kastra password. It expires in 30 minutes.</p>
    <p><a href="{reset_url}" style="background:#16a34a;color:#fff;padding:10px 20px;
       border-radius:6px;text-decoration:none;display:inline-block;">Reset Password</a></p>
    <p>If you didn't request this, you can safely ignore this email.</p>
    """
    await _send(email, "Reset your Kastra password", html)


async def send_payment_received_email(
    org_email: str,
    invoice_id: str,
    amount: float,
    client_name: str,
    receipt_number: str | None = None,
) -> None:
    """Notify the business owner when a payment is confirmed."""
    receipt_line = f"<p><strong>M-Pesa Receipt:</strong> {receipt_number}</p>" if receipt_number else ""
    html = f"""
    <div style="font-family:sans-serif;max-width:480px">
      <h2 style="color:#16a34a">Payment Received</h2>
      <p>A payment has been confirmed for invoice <strong>{invoice_id}</strong>.</p>
      <p><strong>Client:</strong> {client_name}</p>
      <p><strong>Amount:</strong> KSh {amount:,.2f}</p>
      {receipt_line}
      <p><a href="{settings.frontend_url}/invoices/{invoice_id}"
            style="background:#16a34a;color:#fff;padding:8px 18px;border-radius:6px;text-decoration:none">
         View Invoice</a></p>
    </div>
    """
    await _send(org_email, f"Payment received — {invoice_id}", html)


async def send_invoice_email(
    client_email: str,
    client_name: str,
    invoice_id: str,
    amount: float,
    business_name: str,
    due_date: str | None = None,
) -> None:
    pay_url = f"{settings.frontend_url}/pay/{invoice_id}"
    due_line = f"<p><strong>Due:</strong> {due_date}</p>" if due_date else ""
    html = f"""
    <div style="font-family:sans-serif;max-width:520px">
      <p style="font-size:11px;color:#16a34a;font-weight:700;letter-spacing:2px;text-transform:uppercase">{business_name}</p>
      <h2 style="color:#111">Invoice {invoice_id}</h2>
      <p>Hi {client_name},</p>
      <p>Please find your invoice details below.</p>
      <p><strong>Amount:</strong> KSh {amount:,.2f}</p>
      {due_line}
      <p><a href="{pay_url}" style="background:#16a34a;color:#fff;padding:10px 22px;border-radius:8px;text-decoration:none;display:inline-block;font-weight:600">Pay Now</a></p>
      <p style="color:#888;font-size:12px">You can also view and pay this invoice at:<br>{pay_url}</p>
    </div>
    """
    await _send(client_email, f"Invoice {invoice_id} from {business_name}", html)


async def send_quotation_email(
    client_email: str,
    client_name: str,
    quotation_id: str,
    amount: float,
    business_name: str,
    expires_at: str | None = None,
) -> None:
    portal_url = f"{settings.frontend_url}/portal/q/{quotation_id}"
    exp_line = f"<p><strong>Valid until:</strong> {expires_at}</p>" if expires_at else ""
    html = f"""
    <div style="font-family:sans-serif;max-width:520px">
      <p style="font-size:11px;color:#16a34a;font-weight:700;letter-spacing:2px;text-transform:uppercase">{business_name}</p>
      <h2 style="color:#111">Quotation {quotation_id}</h2>
      <p>Hi {client_name},</p>
      <p>We've prepared a quotation for you. Please review and let us know your decision.</p>
      <p><strong>Total:</strong> KSh {amount:,.2f}</p>
      {exp_line}
      <p><a href="{portal_url}" style="background:#16a34a;color:#fff;padding:10px 22px;border-radius:8px;text-decoration:none;display:inline-block;font-weight:600">Review Quotation</a></p>
    </div>
    """
    await _send(client_email, f"Quotation {quotation_id} from {business_name}", html)


async def send_receipt_email(
    client_email: str,
    client_name: str,
    invoice_id: str,
    amount_paid: float,
    business_name: str,
    receipt_ref: str | None = None,
) -> None:
    ref_line = f"<p><strong>Reference:</strong> {receipt_ref}</p>" if receipt_ref else ""
    html = f"""
    <div style="font-family:sans-serif;max-width:520px">
      <p style="font-size:11px;color:#16a34a;font-weight:700;letter-spacing:2px;text-transform:uppercase">{business_name}</p>
      <h2 style="color:#16a34a">Payment Received</h2>
      <p>Hi {client_name},</p>
      <p>We've received your payment for invoice <strong>{invoice_id}</strong>. Thank you!</p>
      <p><strong>Amount Paid:</strong> KSh {amount_paid:,.2f}</p>
      {ref_line}
      <p style="color:#888;font-size:12px">This is your payment confirmation. Please retain for your records.</p>
    </div>
    """
    await _send(client_email, f"Payment confirmed — {invoice_id}", html)


async def send_subscription_renewal_reminder_email(
    org_email: str,
    org_name: str,
    plan: str,
    amount_kes: int,
    next_billing_date: "datetime",
) -> None:
    """Remind the org admin that their subscription renews in 5 days."""
    due_str = next_billing_date.strftime("%d %b %Y")
    plan_label = plan.capitalize()
    settings_url = f"{settings.frontend_url}/settings"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;color:#1f2937">
      <div style="background:#0f172a;padding:24px 28px;border-radius:10px 10px 0 0">
        <p style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 4px">Kastra</p>
        <h2 style="color:#f8fafc;margin:0;font-size:20px">Subscription Renewal Reminder</h2>
      </div>
      <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;padding:24px 28px;border-radius:0 0 10px 10px">
        <p style="margin:0 0 16px">Hi {org_name},</p>
        <div style="background:#fefce8;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;margin-bottom:20px">
          <p style="margin:0;font-size:13px;color:#92400e">
            Your <strong>Kastra {plan_label}</strong> plan is due for renewal on
            <strong>{due_str}</strong> — <strong>KES {amount_kes:,} / month</strong>.
          </p>
        </div>
        <p style="font-size:13px;color:#6b7280;margin:0 0 20px">
          To keep uninterrupted access, please ensure your payment is processed before the renewal date.
          Log in to Kastra and pay via M-Pesa or card from your Settings page.
        </p>
        <a href="{settings_url}"
           style="display:inline-block;background:#16a34a;color:#fff;padding:10px 22px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">
          Renew on Kastra
        </a>
        <p style="font-size:11px;color:#9ca3af;margin-top:24px">
          If you no longer need this plan, you can downgrade to Free from your Settings page.
        </p>
      </div>
    </div>
    """
    await _send(org_email, f"Your Kastra {plan_label} plan renews on {due_str}", html)


async def send_subscription_downgraded_email(
    org_email: str,
    org_name: str,
    old_plan: str,
) -> None:
    """Notify the org admin their plan was downgraded to free due to non-renewal."""
    old_plan_label = old_plan.capitalize()
    settings_url = f"{settings.frontend_url}/settings"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;color:#1f2937">
      <div style="background:#0f172a;padding:24px 28px;border-radius:10px 10px 0 0">
        <p style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 4px">Kastra</p>
        <h2 style="color:#f8fafc;margin:0;font-size:20px">Plan Downgraded to Free</h2>
      </div>
      <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;padding:24px 28px;border-radius:0 0 10px 10px">
        <p style="margin:0 0 16px">Hi {org_name},</p>
        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:14px 16px;margin-bottom:20px">
          <p style="margin:0;font-size:13px;color:#991b1b">
            Your <strong>Kastra {old_plan_label}</strong> subscription has expired and your account has been
            moved to the <strong>Free plan</strong>. Your data is safe — no invoices, clients, or records have been deleted.
          </p>
        </div>
        <p style="font-size:13px;color:#6b7280;margin:0 0 20px">
          To restore full access, upgrade your plan from the Settings page at any time.
        </p>
        <a href="{settings_url}"
           style="display:inline-block;background:#16a34a;color:#fff;padding:10px 22px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">
          Upgrade Now
        </a>
        <p style="font-size:11px;color:#9ca3af;margin-top:24px">
          Questions? Reply to this email and our team will help.
        </p>
      </div>
    </div>
    """
    await _send(org_email, f"Your Kastra {old_plan_label} plan has expired — account moved to Free", html)


async def send_due_soon_reminder_email(
    client_email: str,
    invoice_id: str,
    amount: float,
    business_name: str,
    days_until_due: int,
) -> None:
    """Friendly heads-up sent 7 days before the invoice due date."""
    due_label = "tomorrow" if days_until_due == 1 else f"in {days_until_due} day{'s' if days_until_due != 1 else ''}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;color:#1f2937">
      <div style="background:#0f172a;padding:24px 28px;border-radius:10px 10px 0 0">
        <p style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 4px">{business_name}</p>
        <h2 style="color:#f8fafc;margin:0;font-size:20px">Payment Due Soon</h2>
      </div>
      <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;padding:24px 28px;border-radius:0 0 10px 10px">
        <p style="margin:0 0 16px">Hi, this is a friendly reminder from <strong>{business_name}</strong>.</p>
        <div style="background:#fefce8;border:1px solid #fde68a;border-radius:8px;padding:14px 16px;margin-bottom:20px">
          <p style="margin:0;font-size:13px;color:#92400e">
            Invoice <strong style="font-family:monospace">{invoice_id}</strong> for
            <strong>KSh {amount:,.2f}</strong> is due <strong>{due_label}</strong>.
          </p>
        </div>
        <p style="font-size:13px;color:#6b7280;margin:0 0 20px">
          Please arrange payment before the due date to avoid any late fees.
        </p>
        <a href="{settings.frontend_url}/pay/{invoice_id}"
           style="display:inline-block;background:#16a34a;color:#fff;padding:10px 22px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">
          Pay Now — KSh {amount:,.2f}
        </a>
        <p style="font-size:11px;color:#9ca3af;margin-top:24px">
          If you have already arranged payment, please disregard this message.
        </p>
      </div>
    </div>
    """
    await _send(client_email, f"Payment due {due_label} — {invoice_id}", html)


async def send_overdue_reminder_email(
    client_email: str,
    invoice_id: str,
    amount: float,
    business_name: str,
    days_overdue: int,
    balance_due: float | None = None,
) -> None:
    """Remind a client that their invoice is overdue."""
    display_amount = balance_due if balance_due is not None else amount
    urgency_color = "#dc2626" if days_overdue >= 30 else "#d97706"
    urgency_label = "FINAL NOTICE" if days_overdue >= 60 else ("URGENT" if days_overdue >= 30 else "Overdue")
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;color:#1f2937">
      <div style="background:#0f172a;padding:24px 28px;border-radius:10px 10px 0 0">
        <p style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 4px">{business_name}</p>
        <h2 style="color:#f8fafc;margin:0;font-size:20px">Payment Overdue</h2>
      </div>
      <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;padding:24px 28px;border-radius:0 0 10px 10px">
        <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:14px 16px;margin-bottom:20px">
          <p style="margin:0 0 4px;font-size:11px;font-weight:700;color:{urgency_color};text-transform:uppercase;letter-spacing:1px">{urgency_label}</p>
          <p style="margin:0;font-size:13px;color:#991b1b">
            Invoice <strong style="font-family:monospace">{invoice_id}</strong> for
            <strong>KSh {display_amount:,.2f}</strong> is <strong>{days_overdue} day{'s' if days_overdue != 1 else ''} overdue</strong>.
          </p>
        </div>
        <p style="font-size:13px;color:#374151;margin:0 0 20px">
          Please settle this invoice immediately to avoid further action.
          Contact us if you have already made payment or need to discuss a payment arrangement.
        </p>
        <a href="{settings.frontend_url}/pay/{invoice_id}"
           style="display:inline-block;background:#dc2626;color:#fff;padding:10px 22px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">
          Pay Now — KSh {display_amount:,.2f}
        </a>
        <p style="font-size:11px;color:#9ca3af;margin-top:24px">
          Reference: <span style="font-family:monospace">{invoice_id}</span> · {business_name}
        </p>
      </div>
    </div>
    """
    subject = f"[{urgency_label}] Payment {days_overdue}d overdue — {invoice_id}"
    await _send(client_email, subject, html)
