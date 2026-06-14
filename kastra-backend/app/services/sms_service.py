"""
Africa's Talking SMS integration.
Sends transactional SMS notifications to clients.

Set in .env:
  AT_API_KEY=<your_key>
  AT_USERNAME=<your_username>          # 'sandbox' for testing
  AT_SENDER_ID=<optional_branded_id>   # e.g. KASTRA (must be approved by AT)

Cost: ~KSh 0.8 per SMS. Only sends in production or when AT_API_KEY is set.
Fails silently — a missed SMS should never break a payment flow.
"""
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_AT_URL = "https://api.africastalking.com/version1/messaging"

# Africa's Talking per-recipient status codes that mean the message was accepted
# for delivery: 100 Processed, 101 Sent, 102 Queued. Anything else (e.g. 406
# UserInBlacklist, 405 InsufficientBalance, 407 CouldNotRoute) is a failure.
_SMS_SUCCESS_CODES = {100, 101, 102}


def _format_phone(phone: str | None) -> str | None:
    """Normalise phone to +254XXXXXXXXX. Returns None if unparseable."""
    if not phone:
        return None
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("254") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 10:
        return f"+254{digits[1:]}"
    if len(digits) == 9:
        return f"+254{digits}"
    return None


async def send_sms(phone: str | None, message: str) -> bool:
    """
    Send a single SMS. Returns True if accepted by Africa's Talking.
    Fails silently in development (logs instead of sending).
    """
    normalised = _format_phone(phone)
    if not normalised:
        logger.debug("[SMS] Skipped — could not parse phone: %s", phone)
        return False

    if not settings.at_api_key or not settings.is_production:
        logger.info("[SMS DEV] To: %s | %s", normalised, message)
        return True

    payload: dict = {
        "username": settings.at_username,
        "to": normalised,
        "message": message,
    }
    if settings.at_sender_id:
        payload["from"] = settings.at_sender_id

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _AT_URL,
                data=payload,
                headers={
                    "apiKey": settings.at_api_key,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
    except Exception:
        logger.exception("[SMS] Request to Africa's Talking failed for %s", normalised)
        return False

    # AT returns HTTP 201 even when it rejects the message — the real outcome is in
    # the body. Only treat an accepted recipient (statusCode 100/101/102) as success.
    try:
        data = resp.json().get("SMSMessageData", {})
        recipients = data.get("Recipients", [])
    except Exception:
        logger.error("[SMS] Unparseable Africa's Talking response for %s: %s", normalised, resp.text[:200])
        return False

    if not recipients:
        # No recipients queued at all, e.g. InvalidSenderId or InsufficientBalance.
        logger.error("[SMS] Not delivered to %s — %s", normalised, data.get("Message", "no recipients"))
        return False

    rcpt = recipients[0]
    if rcpt.get("statusCode") in _SMS_SUCCESS_CODES:
        logger.info("[SMS] Sent to %s (messageId=%s)", normalised, rcpt.get("messageId"))
        return True

    logger.error(
        "[SMS] Not delivered to %s — %s (statusCode %s)",
        normalised, rcpt.get("status"), rcpt.get("statusCode"),
    )
    return False


async def sms_invoice_sent(client_phone: str | None, client_name: str, invoice_id: str,
                           amount: float, business_name: str, sms_consent: bool = True) -> None:
    if not sms_consent:
        return
    msg = (
        f"Hi {client_name}, {business_name} has sent you invoice {invoice_id} "
        f"for KSh {amount:,.0f}. Reply or contact them to arrange payment."
    )
    await send_sms(client_phone, msg)


async def sms_payment_received(client_phone: str | None, client_name: str, invoice_id: str,
                                amount: float, business_name: str, receipt: str | None = None,
                                sms_consent: bool = True) -> None:
    if not sms_consent:
        return
    ref = f" (Ref: {receipt})" if receipt else ""
    msg = (
        f"Hi {client_name}, {business_name} has received your payment of "
        f"KSh {amount:,.0f}{ref} for invoice {invoice_id}. Thank you!"
    )
    await send_sms(client_phone, msg)


async def sms_overdue_reminder(client_phone: str | None, client_name: str, invoice_id: str,
                                balance_due: float, business_name: str, days_overdue: int,
                                sms_consent: bool = True) -> None:
    if not sms_consent:
        return
    msg = (
        f"Hi {client_name}, invoice {invoice_id} from {business_name} is "
        f"{days_overdue} day(s) overdue. Balance: KSh {balance_due:,.0f}. "
        f"Please arrange payment to avoid late fees."
    )
    await send_sms(client_phone, msg)


async def sms_due_soon(client_phone: str | None, client_name: str, invoice_id: str,
                        amount: float, business_name: str, days_until_due: int,
                        sms_consent: bool = True) -> None:
    if not sms_consent:
        return
    msg = (
        f"Hi {client_name}, invoice {invoice_id} from {business_name} for "
        f"KSh {amount:,.0f} is due in {days_until_due} day(s). Please arrange payment."
    )
    await send_sms(client_phone, msg)
