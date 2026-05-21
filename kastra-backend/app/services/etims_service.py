"""
KRA eTIMS integration — Virtual Sales Control Unit (VSCU) API.

Businesses register at https://etims.kra.go.ke and receive:
  - A Device Serial Number (dvcSrlNo)
  - An Auth Token
  - A Branch ID (bhfId) — "000" for single-branch

The VSCU API accepts invoice submissions and returns a KRA-signed
Control Unit Invoice Number (cuInvoiceNo) + QR verification data.

Invoice QR code links to:
  https://etims.kra.go.ke/etims-portal/searchDetails/{cuInvoiceNo}
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.invoice import Invoice
from app.models.organization import Organization

logger = logging.getLogger(__name__)

ETIMS_PROD_URL = "https://vscu.kra.go.ke/api"
ETIMS_SANDBOX_URL = "https://etims-sbx.kra.go.ke/api"


def _base_url(org: Organization) -> str:
    return ETIMS_PROD_URL


def _headers(org: Organization) -> dict:
    return {
        "Content-Type": "application/json",
        "tin": org.kra_pin or "",
        "bhfId": org.etims_branch_id or "000",
        "dvcSrlNo": org.etims_device_serial or "",
        "Authorization": f"Bearer {org.etims_auth_token}" if org.etims_auth_token else "",
    }


def _invoice_payload(inv: Invoice, org: Organization) -> dict:
    """
    Build the KRA eTIMS invoice submission payload.
    Tax type B = standard rated (16% VAT).
    Tax type E = VAT exempt (for non-VAT registered or exempt goods).
    """
    vat = float(inv.vat_amount)
    subtotal = float(inv.subtotal)
    total = float(inv.grand_total)

    # For non-VAT-registered businesses: put amount in taxblAmtE (exempt)
    if vat == 0:
        taxble_b = 0.0
        taxble_e = subtotal
        tax_amt_b = 0.0
    else:
        taxble_b = subtotal
        taxble_e = 0.0
        tax_amt_b = vat

    issue_dt = inv.created_at.strftime("%Y%m%d%H%M%S") if inv.created_at else datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    items_payload = []
    for i, item in enumerate(inv.items, start=1):
        items_payload.append({
            "itemSeq": i,
            "itemCd": f"ITEM{str(i).zfill(4)}",
            "itemClsCd": "5020230602",  # general merchandise
            "itemNm": item.description[:100],
            "bcd": None,
            "pkgUnitCd": "BJ",
            "pkg": float(item.quantity),
            "qtyUnitCd": "U",
            "qty": float(item.quantity),
            "prc": float(item.unit_price),
            "splyAmt": float(item.line_total),
            "dcRt": 0,
            "dcAmt": 0,
            "isrccCd": None,
            "isrccNm": None,
            "isrcRt": None,
            "isrcAmt": None,
            "vatCatCd": "B" if vat > 0 else "E",
            "exciseTxCatCd": None,
            "vatTaxblAmt": float(item.line_total) if vat > 0 else 0,
            "exciseTxblAmt": None,
            "exciseTxAmt": None,
            "vatAmt": round(float(item.line_total) * 0.16 / 1.16, 2) if vat > 0 else 0,
            "totAmt": float(item.line_total),
        })

    return {
        "invcNo": 1,
        "orgInvcNo": 0,
        "cfmDt": issue_dt,
        "salesDt": inv.created_at.strftime("%Y%m%d") if inv.created_at else datetime.now(timezone.utc).strftime("%Y%m%d"),
        "stockRlsDt": None,
        "rcptTyCd": "S",
        "pmtTyCd": _payment_code(inv.payment_method),
        "salesSttsCd": "02",
        "salesTyCd": "N",
        "cancelReqDt": None,
        "rfdDt": None,
        "rfdRsnCd": None,
        "totItemCnt": len(inv.items),
        "taxblAmtA": 0,
        "taxblAmtB": taxble_b,
        "taxblAmtC": 0,
        "taxblAmtD": 0,
        "taxblAmtE": taxble_e,
        "taxRtA": 0,
        "taxRtB": 16,
        "taxRtC": 0,
        "taxRtD": 0,
        "taxRtE": 0,
        "taxAmtA": 0,
        "taxAmtB": tax_amt_b,
        "taxAmtC": 0,
        "taxAmtD": 0,
        "taxAmtE": 0,
        "totTaxblAmt": subtotal,
        "totTaxAmt": vat,
        "totAmt": total,
        "prchrAcptcYn": "N",
        "remark": f"Invoice {inv.id}",
        "regrId": org.kra_pin or "SYSTEM",
        "regrNm": org.name or "System",
        "modrId": org.kra_pin or "SYSTEM",
        "modrNm": org.name or "System",
        "receipt": {
            "custTin": None,
            "custMblNo": None,
            "rptNo": 1,
            "trdeNm": inv.client.name if inv.client else "",
            "adrs": inv.client.address if inv.client else "",
            "topMsg": f"Receipt for {inv.id}",
            "btmMsg": "Thank you for your business.",
            "prchrAcptcYn": "N",
        },
        "itemList": items_payload,
    }


def _payment_code(method: str | None) -> str:
    return {"mpesa": "04", "bank": "02", "cash": "01"}.get(method or "", "01")


async def submit_to_kra(
    db: AsyncSession,
    invoice_id: str,
    org: Organization,
) -> Invoice:
    """
    Submit an invoice to KRA eTIMS and store the control unit data.
    Returns the updated Invoice.
    Raises ValueError on KRA API error.
    """
    from app.models.invoice import Invoice

    result = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(selectinload(Invoice.client), selectinload(Invoice.items))
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise ValueError("Invoice not found")
    if inv.etims_cu_invoice_no:
        raise ValueError("Invoice already submitted to eTIMS")

    payload = _invoice_payload(inv, org)
    url = f"{_base_url(org)}/TrnsSalesOsdc"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=_headers(org))
        resp.raise_for_status()
        body = resp.json()
    except httpx.HTTPStatusError as e:
        raise ValueError(f"KRA API error: {e.response.status_code} — {e.response.text}") from e
    except httpx.RequestError as e:
        raise ValueError(f"Could not reach KRA eTIMS: {e}") from e

    result_cd = body.get("resultCd", "")
    if result_cd != "000":
        raise ValueError(f"KRA rejected invoice: {body.get('resultMsg', 'Unknown error')}")

    data = body.get("data", {})
    inv.etims_cu_invoice_no = str(data.get("rcptNo", ""))
    inv.etims_rcpt_sign = data.get("rcptSign", "")
    inv.etims_int_data = data.get("intrlData", "")
    inv.etims_submitted_at = datetime.now(timezone.utc)

    await db.flush()
    return inv


async def test_connection(org: Organization) -> dict:
    """Ping KRA to verify credentials. Returns {ok, message}."""
    url = f"{_base_url(org)}/selectInitInfo"
    payload = {
        "tin": org.kra_pin or "",
        "bhfId": org.etims_branch_id or "000",
        "dvcSrlNo": org.etims_device_serial or "",
        "lastReqDt": "20240101000000",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=_headers(org))
        body = resp.json()
        if body.get("resultCd") == "000":
            return {"ok": True, "message": "Connected to KRA eTIMS successfully."}
        return {"ok": False, "message": body.get("resultMsg", "Authentication failed")}
    except Exception as e:
        return {"ok": False, "message": f"Could not reach KRA: {e}"}


def verification_url(cu_invoice_no: str) -> str:
    return f"https://etims.kra.go.ke/etims-portal/searchDetails/{cu_invoice_no}"
