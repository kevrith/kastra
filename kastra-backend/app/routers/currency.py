"""
Live exchange rate lookup — converts a foreign currency to KES.
Used by the invoice/quotation forms to auto-fill the exchange rate
when a business invoices a client in USD, EUR, GBP, etc.
"""
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/currency", tags=["currency"])

_RATE_API_URL = "https://open.er-api.com/v6/latest/{code}"

# Common currencies Kenyan SMEs deal with (exports, diaspora, NGO clients)
SUPPORTED_CURRENCIES = ["KES", "USD", "EUR", "GBP", "UGX", "TZS", "ZAR", "CNY", "INR", "AED"]


@router.get("/currencies")
async def list_currencies(_: User = Depends(get_current_user)):
    return {"data": SUPPORTED_CURRENCIES}


@router.get("/rate")
async def get_rate(
    code: str,
    _: User = Depends(get_current_user),
):
    """Fetch the live exchange rate of `code` → KES (1 unit of `code` = X KES)."""
    code = (code or "").upper().strip()
    if len(code) != 3 or not code.isalpha():
        raise HTTPException(status_code=422, detail="currency code must be a 3-letter ISO code")

    if code == "KES":
        return {"currency": "KES", "rate_to_kes": 1.0, "as_of": None}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_RATE_API_URL.format(code=code))
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("Exchange rate lookup failed for %s: %s", code, e)
        raise HTTPException(status_code=502, detail="Could not fetch live exchange rate. Enter it manually.")

    rate = (data.get("rates") or {}).get("KES")
    if rate is None:
        raise HTTPException(status_code=404, detail=f"No KES rate available for {code}")

    return {
        "currency": code,
        "rate_to_kes": round(float(rate), 6),
        "as_of": data.get("time_last_update_utc"),
    }
