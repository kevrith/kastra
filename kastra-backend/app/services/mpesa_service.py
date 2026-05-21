import base64
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.config import settings


@dataclass
class MpesaCredentials:
    consumer_key: str
    consumer_secret: str
    shortcode: str
    passkey: str
    env: str = "sandbox"

    @property
    def base_url(self) -> str:
        if self.env == "production":
            return "https://api.safaricom.co.ke"
        return "https://sandbox.safaricom.co.ke"


def _creds_from_settings() -> MpesaCredentials:
    return MpesaCredentials(
        consumer_key=settings.mpesa_consumer_key,
        consumer_secret=settings.mpesa_consumer_secret,
        shortcode=settings.mpesa_shortcode,
        passkey=settings.mpesa_passkey,
        env=settings.mpesa_env,
    )


def _creds_from_org(org) -> MpesaCredentials | None:
    if org and org.mpesa_consumer_key and org.mpesa_shortcode and org.mpesa_passkey:
        return MpesaCredentials(
            consumer_key=org.mpesa_consumer_key,
            consumer_secret=org.mpesa_consumer_secret or "",
            shortcode=org.mpesa_shortcode,
            passkey=org.mpesa_passkey,
            env=org.mpesa_env or "sandbox",
        )
    return None


async def _get_access_token(creds: MpesaCredentials) -> str:
    credentials = base64.b64encode(
        f"{creds.consumer_key}:{creds.consumer_secret}".encode()
    ).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{creds.base_url}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {credentials}"},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def initiate_stk_push(
    phone: str,
    amount: int,
    account_ref: str,
    description: str,
    org=None,
) -> str:
    creds = _creds_from_org(org) or _creds_from_settings()
    token = await _get_access_token(creds)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(
        f"{creds.shortcode}{creds.passkey}{timestamp}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{creds.base_url}/mpesa/stkpush/v1/processrequest",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "BusinessShortCode": creds.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": amount,
                "PartyA": phone,
                "PartyB": creds.shortcode,
                "PhoneNumber": phone,
                "CallBackURL": settings.mpesa_callback_url,
                "AccountReference": account_ref,
                "TransactionDesc": description,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("ResponseCode") != "0":
            raise ValueError(data.get("ResponseDescription", "STK Push failed"))
        return data["CheckoutRequestID"]
