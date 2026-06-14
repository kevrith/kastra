import logging
from datetime import datetime, timedelta, timezone

import httpx
from jose import JWTError, jwt

from app.config import settings
from app.services.sms_service import _format_phone, send_sms

logger = logging.getLogger(__name__)

_RESET_SECRET = settings.secret_key + "-reset"
_RESET_EXPIRE_MINUTES = 30

_VERIFY_SECRET = settings.secret_key + "-verify"
_VERIFY_EXPIRE_HOURS = 48


def create_password_reset_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=_RESET_EXPIRE_MINUTES)
    return jwt.encode({"sub": email, "exp": expire, "type": "reset"}, _RESET_SECRET, algorithm="HS256")


def verify_password_reset_token(token: str) -> str:
    payload = jwt.decode(token, _RESET_SECRET, algorithms=["HS256"])
    if payload.get("type") != "reset":
        raise JWTError("Invalid token type")
    return payload["sub"]


def create_email_verification_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_VERIFY_EXPIRE_HOURS)
    return jwt.encode({"sub": email, "exp": expire, "type": "verify"}, _VERIFY_SECRET, algorithm="HS256")


def verify_email_verification_token(token: str) -> str:
    payload = jwt.decode(token, _VERIFY_SECRET, algorithms=["HS256"])
    if payload.get("type") != "verify":
        raise JWTError("Invalid token type")
    return payload["sub"]


async def _send_via_sendgrid(to_email: str, subject: str, html: str) -> None:
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": settings.mail_from, "name": "Kastra"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    if settings.mail_reply_to:
        payload["reply_to"] = {"email": settings.mail_reply_to}
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
    reset_url = f"{settings.primary_frontend_url}/reset-password?token={reset_token}"
    html = f"""
    <p>Hi,</p>
    <p>Click the link below to reset your Kastra password. It expires in 30 minutes.</p>
    <p><a href="{reset_url}" style="background:#16a34a;color:#fff;padding:10px 20px;
       border-radius:6px;text-decoration:none;display:inline-block;">Reset Password</a></p>
    <p>If you didn't request this, you can safely ignore this email.</p>
    """
    await _send(email, "Reset your Kastra password", html)


async def send_verification_email(email: str, token: str) -> None:
    verify_url = f"{settings.primary_frontend_url}/verify-email?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;color:#1f2937">
      <div style="background:#0f172a;padding:24px 28px;border-radius:10px 10px 0 0">
        <p style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 4px">Kastra</p>
        <h2 style="color:#f8fafc;margin:0;font-size:20px">Verify your email address</h2>
      </div>
      <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;padding:24px 28px;border-radius:0 0 10px 10px">
        <p style="margin:0 0 16px">Welcome to Kastra!</p>
        <p style="color:#374151;margin:0 0 20px">
          Click the button below to activate your account. This link is valid for 48 hours.
        </p>
        <a href="{verify_url}"
           style="display:inline-block;background:#16a34a;color:#fff;padding:12px 26px;
                  border-radius:8px;text-decoration:none;font-weight:700;font-size:14px">
          Activate my account
        </a>
        <p style="font-size:12px;color:#6b7280;margin-top:20px">
          Or copy this link into your browser:<br>
          <span style="word-break:break-all;color:#374151">{verify_url}</span>
        </p>
        <p style="font-size:11px;color:#9ca3af;margin-top:20px">
          If you did not create a Kastra account, you can safely ignore this email.
        </p>
      </div>
    </div>
    """
    await _send(email, "Activate your Kastra account", html)


async def send_plan_activated_email(
    org_email: str,
    org_name: str,
    plan: str,
    amount_kes: int,
    next_billing_date: "datetime",
) -> None:
    """Confirmation sent to org admin immediately after a successful subscription payment."""
    plan_label = plan.capitalize()
    due_str = next_billing_date.strftime("%d %b %Y")
    settings_url = f"{settings.primary_frontend_url}/settings"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;color:#1f2937">
      <div style="background:#0f172a;padding:24px 28px;border-radius:10px 10px 0 0">
        <p style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 4px">Kastra</p>
        <h2 style="color:#f8fafc;margin:0;font-size:20px">Plan Activated — {plan_label}</h2>
      </div>
      <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;padding:24px 28px;border-radius:0 0 10px 10px">
        <p style="margin:0 0 16px">Hi {org_name},</p>
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 16px;margin-bottom:20px">
          <p style="margin:0;font-size:13px;color:#166534">
            Your <strong>Kastra {plan_label}</strong> plan is now active.
            Payment of <strong>KES {amount_kes:,}</strong> received.
            Your next renewal date is <strong>{due_str}</strong>.
          </p>
        </div>
        <p style="font-size:13px;color:#6b7280;margin:0 0 20px">
          You now have full access to all {plan_label} features. Log in to your dashboard to get started.
        </p>
        <a href="{settings_url}"
           style="display:inline-block;background:#16a34a;color:#fff;padding:10px 22px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">
          Go to Kastra
        </a>
        <p style="font-size:11px;color:#9ca3af;margin-top:24px">
          Questions? Reply to this email and our team will help.
        </p>
      </div>
    </div>
    """
    await _send(org_email, f"Kastra {plan_label} plan activated — payment confirmed", html)


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
      <p><a href="{settings.primary_frontend_url}/invoices/{invoice_id}"
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
    pay_url = f"{settings.primary_frontend_url}/pay/{invoice_id}"
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
    portal_url = f"{settings.primary_frontend_url}/portal/q/{quotation_id}"
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
    settings_url = f"{settings.primary_frontend_url}/settings"
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
    settings_url = f"{settings.primary_frontend_url}/settings"
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
        <a href="{settings.primary_frontend_url}/pay/{invoice_id}"
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


def _build_whatsapp_link(phone: str, form_url: str, name: str) -> str:
    """Return a wa.me link with the message pre-written (works even if API is not configured)."""
    import urllib.parse
    msg = (
        f"Hi {name},\n\n"
        "The team at Kastra would love to hear about your experience using our platform.\n\n"
        "Could you spare 2 minutes to share a quick testimonial? Your feedback may be featured on our website.\n\n"
        f"👉 {form_url}\n\n"
        "Thank you! 🙏"
    )
    clean = _format_phone(phone) or phone
    return f"https://wa.me/{clean.lstrip('+')}?text={urllib.parse.quote(msg)}"


async def send_testimonial_whatsapp(phone: str, name: str, form_url: str) -> bool:
    """
    Send the testimonial request via Africa's Talking WhatsApp API.
    Returns True on success, False if AT is not configured or the call fails.
    The caller should always also generate the wa.me link as a fallback.
    """
    if not settings.at_api_key or not settings.at_whatsapp_number:
        logger.info("[WHATSAPP] AT not configured — skipping programmatic send to %s", phone)
        return False

    message = (
        f"Hi {name}, the Kastra team would love to hear about your experience. "
        f"Share a quick testimonial (2 min) here: {form_url} "
        "Your feedback may be featured on our website. Thank you!"
    )
    clean_phone = _format_phone(phone) or phone

    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.post(
                "https://api.africastalking.com/version1/messaging/whatsapp/text/send",
                headers={
                    "apiKey": settings.at_api_key,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={
                    "username": settings.at_username,
                    "to": clean_phone,
                    "from": settings.at_whatsapp_number,
                    "message": message,
                },
            )
        if resp.is_success:
            logger.info("[WHATSAPP] Sent to %s via AT", clean_phone)
            return True
        logger.warning("[WHATSAPP] AT returned %s: %s", resp.status_code, resp.text[:200])
        return False
    except Exception:
        logger.exception("[WHATSAPP] Failed to send to %s via AT", clean_phone)
        return False


async def send_testimonial_request_email(
    to_email: str,
    name: str,
    form_url: str,
) -> None:
    html = f"""
    <div style="font-family:sans-serif;max-width:520px;color:#1f2937">
      <div style="background:#0f172a;padding:24px 28px;border-radius:10px 10px 0 0">
        <p style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 4px">Kastra</p>
        <h2 style="color:#f8fafc;margin:0;font-size:20px">Share your experience with Kastra</h2>
      </div>
      <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;padding:24px 28px;border-radius:0 0 10px 10px">
        <p style="margin:0 0 16px">Hi {name},</p>
        <p style="color:#374151;margin:0 0 16px">
          Thank you for using Kastra. We'd love to hear about your experience — it helps other Kenyan businesses
          discover the platform and helps us keep improving.
        </p>
        <p style="color:#374151;margin:0 0 24px">
          If you have 2 minutes, please share a quick testimonial using the link below.
          You'll have the chance to review what you've written and give consent before anything is published.
        </p>
        <a href="{form_url}"
           style="display:inline-block;background:#16a34a;color:#fff;padding:12px 26px;
                  border-radius:8px;text-decoration:none;font-weight:700;font-size:14px">
          Share your experience →
        </a>
        <p style="font-size:11px;color:#9ca3af;margin-top:24px">
          This link is unique to you and can only be used once.
          If you'd prefer not to share a testimonial, simply ignore this email — no action needed.
        </p>
      </div>
    </div>
    """
    await _send(to_email, "Share your Kastra experience — 2-minute testimonial request", html)


async def send_affiliate_approved_email(name: str, email: str) -> None:
    login_url = f"{settings.primary_frontend_url}/affiliate/login"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;color:#1f2937">
      <div style="background:#0f172a;padding:24px 28px;border-radius:10px 10px 0 0">
        <p style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 4px">Kastra Partners</p>
        <h2 style="color:#f8fafc;margin:0;font-size:20px">You're approved!</h2>
      </div>
      <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;padding:24px 28px;border-radius:0 0 10px 10px">
        <p style="margin:0 0 16px">Hi {name},</p>
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 16px;margin-bottom:20px">
          <p style="margin:0;font-size:13px;color:#166534">
            Your Kastra affiliate application has been approved.
            Your account is now active and you can start earning commissions immediately.
          </p>
        </div>
        <p style="color:#374151;margin:0 0 20px;font-size:13px">
          Log in to your partner portal to grab your referral link and track your earnings.
          You earn a commission for every paying subscriber you refer.
        </p>
        <a href="{login_url}"
           style="display:inline-block;background:#16a34a;color:#fff;padding:12px 26px;
                  border-radius:8px;text-decoration:none;font-weight:700;font-size:14px">
          Go to Partner Portal
        </a>
        <p style="font-size:12px;color:#6b7280;margin-top:20px">
          Sign in with the email and password you used when you applied.
        </p>
        <p style="font-size:11px;color:#9ca3af;margin-top:16px">
          Questions? Reply to this email and we'll help you get started.
        </p>
      </div>
    </div>
    """
    await _send(email, "You've been approved — Kastra Partner Portal", html)


async def send_affiliate_application_email(name: str, email: str, phone: str) -> None:
    """Notify the admin ops inbox that a new affiliate has applied and needs review."""
    if not settings.admin_email:
        return
    review_url = f"{settings.primary_frontend_url}/superadmin"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;color:#1f2937">
      <div style="background:#0f172a;padding:24px 28px;border-radius:10px 10px 0 0">
        <p style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 4px">Kastra Partners</p>
        <h2 style="color:#f8fafc;margin:0;font-size:20px">New affiliate application</h2>
      </div>
      <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;padding:24px 28px;border-radius:0 0 10px 10px">
        <p style="margin:0 0 16px;font-size:13px">A new partner has applied and is awaiting approval:</p>
        <table style="font-size:13px;color:#374151;border-collapse:collapse;margin-bottom:20px">
          <tr><td style="padding:2px 12px 2px 0;color:#6b7280">Name</td><td style="font-weight:600">{name}</td></tr>
          <tr><td style="padding:2px 12px 2px 0;color:#6b7280">Email</td><td>{email}</td></tr>
          <tr><td style="padding:2px 12px 2px 0;color:#6b7280">Phone</td><td>{phone}</td></tr>
        </table>
        <a href="{review_url}"
           style="display:inline-block;background:#16a34a;color:#fff;padding:12px 26px;
                  border-radius:8px;text-decoration:none;font-weight:700;font-size:14px">
          Review in Super Admin
        </a>
      </div>
    </div>
    """
    await _send(settings.admin_email, f"New affiliate application — {name}", html)


async def send_affiliate_application_whatsapp(name: str, phone: str) -> bool:
    """WhatsApp ping to the admin's phone when a new affiliate applies, for a faster nudge than email.

    Returns True on success, False if the admin phone or Africa's Talking aren't configured.
    """
    if not settings.admin_phone:
        return False
    if not settings.at_api_key or not settings.at_whatsapp_number:
        logger.info("[WHATSAPP] AT not configured — skipping affiliate application ping")
        return False

    message = (
        "New Kastra affiliate application 🎉\n"
        f"Name: {name}\n"
        f"Phone: {phone}\n"
        "Review and approve in Super Admin."
    )
    to = _format_phone(settings.admin_phone) or settings.admin_phone
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.post(
                "https://api.africastalking.com/version1/messaging/whatsapp/text/send",
                headers={
                    "apiKey": settings.at_api_key,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={
                    "username": settings.at_username,
                    "to": to,
                    "from": settings.at_whatsapp_number,
                    "message": message,
                },
            )
        if resp.is_success:
            logger.info("[WHATSAPP] Affiliate application ping sent to admin")
            return True
        logger.warning("[WHATSAPP] AT returned %s: %s", resp.status_code, resp.text[:200])
        return False
    except Exception:
        logger.exception("[WHATSAPP] Failed to send affiliate application ping to admin")
        return False


async def send_affiliate_application_sms(name: str, phone: str) -> bool:
    """SMS ping to the admin's phone when a new affiliate applies.

    Returns True if the message was accepted for delivery. No-ops (False) when
    no admin phone is configured. Delivery to Safaricom numbers requires an
    approved Africa's Talking sender ID; until then send_sms reports the failure.
    """
    if not settings.admin_phone:
        return False
    msg = (
        f"New Kastra affiliate application from {name} ({phone}). "
        "Review and approve in Super Admin."
    )
    return await send_sms(settings.admin_phone, msg)


async def send_affiliate_payout_shortfall_email(needed_ksh: float, available_ksh: float, affiliate_count: int) -> None:
    """Alert the admin that the Paystack balance can't cover the monthly affiliate payout batch."""
    if not settings.admin_email:
        return
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;color:#1f2937">
      <div style="background:#7f1d1d;padding:24px 28px;border-radius:10px 10px 0 0">
        <p style="color:#fca5a5;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;margin:0 0 4px">Kastra Partners</p>
        <h2 style="color:#fff;margin:0;font-size:20px">Top up needed for affiliate payouts</h2>
      </div>
      <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;padding:24px 28px;border-radius:0 0 10px 10px">
        <p style="margin:0 0 16px;font-size:13px">
          This month's automatic affiliate payout ran, but your Paystack balance is too low to pay everyone.
          Affiliates that fit within the balance were paid; the rest were skipped and will roll over.
        </p>
        <table style="font-size:13px;color:#374151;border-collapse:collapse;margin-bottom:20px">
          <tr><td style="padding:2px 12px 2px 0;color:#6b7280">Eligible affiliates</td><td style="font-weight:600">{affiliate_count}</td></tr>
          <tr><td style="padding:2px 12px 2px 0;color:#6b7280">Total needed</td><td style="font-weight:600">KSh {needed_ksh:,.0f}</td></tr>
          <tr><td style="padding:2px 12px 2px 0;color:#6b7280">Available balance</td><td style="font-weight:600;color:#b91c1c">KSh {available_ksh:,.0f}</td></tr>
          <tr><td style="padding:2px 12px 2px 0;color:#6b7280">Shortfall</td><td style="font-weight:600;color:#b91c1c">KSh {max(0, needed_ksh - available_ksh):,.0f}</td></tr>
        </table>
        <a href="https://dashboard.paystack.com"
           style="display:inline-block;background:#16a34a;color:#fff;padding:12px 26px;
                  border-radius:8px;text-decoration:none;font-weight:700;font-size:14px">
          Top up Paystack balance
        </a>
        <p style="font-size:12px;color:#6b7280;margin-top:16px">
          Once topped up, skipped affiliates are paid on the next monthly run, or you can pay them sooner from Super Admin.
        </p>
      </div>
    </div>
    """
    await _send(settings.admin_email, "Action needed: Paystack balance too low for affiliate payouts", html)


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
        <a href="{settings.primary_frontend_url}/pay/{invoice_id}"
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
