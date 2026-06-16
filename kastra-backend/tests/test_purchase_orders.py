"""End-to-end tests for the Procure-to-Pay flow:
PO -> send -> supplier responds (portal) -> accept/reject -> receive goods -> bill -> pay.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def paid_headers(client: AsyncClient, auth_headers: dict, db_session: AsyncSession) -> dict:
    """auth_headers, but the org is upgraded to a plan that includes suppliers."""
    me = await client.get("/api/auth/me", headers=auth_headers)
    org_id = me.json()["organization"]["id"]
    org = (await db_session.execute(select(Organization).where(Organization.id == org_id))).scalar_one()
    org.plan = "business"
    await db_session.commit()
    return auth_headers


@pytest_asyncio.fixture
async def supplier_id(client: AsyncClient, paid_headers: dict) -> str:
    resp = await client.post("/api/suppliers", json={
        "name": "James Mwangi", "company_name": "Nairobi Hardware Ltd",
        "phone": "254712345678", "email": "james@hardware.co.ke",
    }, headers=paid_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


async def _create_po(client, headers, supplier_id, **overrides):
    payload = {
        "supplier_id": supplier_id,
        "items": [
            {"description": "Cement 50kg", "unit": "bag", "ordered_qty": 10, "ordered_unit_price": 750},
            {"description": "Steel bars", "unit": "pcs", "ordered_qty": 5, "ordered_unit_price": 1200},
        ],
        **overrides,
    }
    resp = await client.post("/api/purchase-orders", json=payload, headers=headers)
    return resp


# ── Plan gating ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_purchase_orders_require_paid_plan(client: AsyncClient, auth_headers: dict):
    # Default org is on the free plan — suppliers/procurement should be blocked.
    resp = await client.post("/api/purchase-orders", json={
        "supplier_id": "00000000-0000-0000-0000-000000000000",
        "items": [{"description": "X", "ordered_qty": 1, "ordered_unit_price": 1}],
    }, headers=auth_headers)
    assert resp.status_code == 402, resp.text


# ── Create / totals ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_po_computes_totals_and_id(client: AsyncClient, paid_headers: dict, supplier_id: str):
    resp = await _create_po(client, paid_headers, supplier_id)
    assert resp.status_code == 201, resp.text
    po = resp.json()["data"]
    # 10*750 + 5*1200 = 7500 + 6000 = 13500
    assert float(po["subtotal"]) == 13500
    assert float(po["total"]) == 13500
    assert po["status"] == "draft"
    assert "-PO-" in po["id"]
    assert len(po["items"]) == 2


@pytest.mark.asyncio
async def test_create_po_rejects_empty_items(client: AsyncClient, paid_headers: dict, supplier_id: str):
    resp = await client.post("/api/purchase-orders", json={
        "supplier_id": supplier_id, "items": [],
    }, headers=paid_headers)
    assert resp.status_code == 400


# ── Full happy path ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_p2p_flow(client: AsyncClient, paid_headers: dict, supplier_id: str):
    # 1. Create + send
    po = (await _create_po(client, paid_headers, supplier_id)).json()["data"]
    po_id, token = po["id"], po["portal_token"]
    sent = await client.post(f"/api/purchase-orders/{po_id}/send", headers=paid_headers)
    assert sent.status_code == 200
    assert sent.json()["data"]["status"] == "sent"

    # 2. Supplier views the order via the portal (no auth)
    portal = await client.get(f"/api/supplier-portal/order/{token}")
    assert portal.status_code == 200
    items = portal.json()["items"]
    assert len(items) == 2

    # 3. Supplier confirms as ordered → supplier_confirmed
    respond = await client.post(f"/api/supplier-portal/order/{token}/respond", json={
        "items": [
            {"id": items[0]["id"], "confirmed_qty": 10, "confirmed_unit_price": 750},
            {"id": items[1]["id"], "confirmed_qty": 5, "confirmed_unit_price": 1200},
        ],
        "supplier_notes": "Available in 2 days",
    })
    assert respond.status_code == 200, respond.text
    detail = (await client.get(f"/api/purchase-orders/{po_id}", headers=paid_headers)).json()["data"]
    assert detail["status"] == "supplier_confirmed"
    assert float(detail["confirmed_total"]) == 13500

    # 4. Buyer accepts
    acc = await client.post(f"/api/purchase-orders/{po_id}/accept", headers=paid_headers)
    assert acc.status_code == 200
    assert acc.json()["data"]["status"] == "accepted"

    # 5. Receive all goods → received
    grn = await client.post(f"/api/purchase-orders/{po_id}/receipts", json={
        "items": [
            {"purchase_order_item_id": items[0]["id"], "quantity": 10},
            {"purchase_order_item_id": items[1]["id"], "quantity": 5},
        ],
    }, headers=paid_headers)
    assert grn.status_code == 201, grn.text
    received = grn.json()["data"]
    assert received["status"] == "received"
    assert len(received["receipts"]) == 1

    # 6. Create a bill → billed, 3-way matched
    bill = await client.post(f"/api/supplier-bills/from-po/{po_id}", json={
        "supplier_ref": "INV-9001", "due_date": "2026-12-31",
    }, headers=paid_headers)
    assert bill.status_code == 201, bill.text
    bill_data = bill.json()["data"]
    assert bill_data["match_status"] == "matched"
    assert float(bill_data["total"]) == 13500
    assert bill_data["status"] == "unpaid"

    # 7. Pay the bill in full → paid; PO advances to paid
    pay = await client.post(f"/api/supplier-bills/{bill_data['id']}/payments", json={
        "amount": 13500,
    }, headers=paid_headers)
    assert pay.status_code == 200, pay.text
    assert pay.json()["data"]["status"] == "paid"
    assert float(pay.json()["data"]["balance"]) == 0

    final = (await client.get(f"/api/purchase-orders/{po_id}", headers=paid_headers)).json()["data"]
    assert final["status"] == "paid"


# ── Negotiation: revise + reject + price flag ────────────────────────────────

@pytest.mark.asyncio
async def test_supplier_revision_sets_price_flag(client: AsyncClient, paid_headers: dict, supplier_id: str):
    po = (await _create_po(client, paid_headers, supplier_id)).json()["data"]
    po_id, token = po["id"], po["portal_token"]
    await client.post(f"/api/purchase-orders/{po_id}/send", headers=paid_headers)
    items = (await client.get(f"/api/supplier-portal/order/{token}")).json()["items"]

    # Supplier raises cement price 750 -> 800 (+6.67%)
    await client.post(f"/api/supplier-portal/order/{token}/respond", json={
        "items": [
            {"id": items[0]["id"], "confirmed_qty": 10, "confirmed_unit_price": 800},
            {"id": items[1]["id"], "confirmed_qty": 5, "confirmed_unit_price": 1200},
        ],
    })
    detail = (await client.get(f"/api/purchase-orders/{po_id}", headers=paid_headers)).json()["data"]
    assert detail["status"] == "supplier_revised"
    cement = next(i for i in detail["items"] if i["description"] == "Cement 50kg")
    assert cement["price_delta_pct"] == 6.7  # rounded


@pytest.mark.asyncio
async def test_reject_then_supplier_resubmits(client: AsyncClient, paid_headers: dict, supplier_id: str):
    po = (await _create_po(client, paid_headers, supplier_id)).json()["data"]
    po_id, token = po["id"], po["portal_token"]
    await client.post(f"/api/purchase-orders/{po_id}/send", headers=paid_headers)
    items = (await client.get(f"/api/supplier-portal/order/{token}")).json()["items"]

    # Supplier revises up
    await client.post(f"/api/supplier-portal/order/{token}/respond", json={
        "items": [{"id": i["id"], "confirmed_qty": 1, "confirmed_unit_price": 9999} for i in items],
    })
    # Buyer rejects with a reason
    rej = await client.post(f"/api/purchase-orders/{po_id}/reject", json={
        "reason": "Price too high, please review.",
    }, headers=paid_headers)
    assert rej.status_code == 200
    rejected = rej.json()["data"]
    assert rejected["status"] == "rejected"
    assert any(n["author_type"] == "buyer" for n in rejected["notes_thread"])

    # Supplier sees the rejection note and resubmits at the original price
    portal = await client.get(f"/api/supplier-portal/order/{token}")
    assert portal.json()["status"] == "rejected"
    await client.post(f"/api/supplier-portal/order/{token}/respond", json={
        "items": [
            {"id": items[0]["id"], "confirmed_qty": 10, "confirmed_unit_price": 750},
            {"id": items[1]["id"], "confirmed_qty": 5, "confirmed_unit_price": 1200},
        ],
        "reply": "Adjusted as requested.",
    })
    detail = (await client.get(f"/api/purchase-orders/{po_id}", headers=paid_headers)).json()["data"]
    assert detail["status"] == "supplier_confirmed"
    assert any(n["author_type"] == "supplier" for n in detail["notes_thread"])


@pytest.mark.asyncio
async def test_reject_requires_a_reason(client: AsyncClient, paid_headers: dict, supplier_id: str):
    po = (await _create_po(client, paid_headers, supplier_id)).json()["data"]
    po_id, token = po["id"], po["portal_token"]
    await client.post(f"/api/purchase-orders/{po_id}/send", headers=paid_headers)
    items = (await client.get(f"/api/supplier-portal/order/{token}")).json()["items"]
    await client.post(f"/api/supplier-portal/order/{token}/respond", json={
        "items": [{"id": i["id"], "confirmed_qty": 1, "confirmed_unit_price": 100} for i in items],
    })
    resp = await client.post(f"/api/purchase-orders/{po_id}/reject", json={"reason": "   "}, headers=paid_headers)
    assert resp.status_code == 400


# ── Partial receipt + guards ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_partial_receipt_keeps_order_receiving(client: AsyncClient, paid_headers: dict, supplier_id: str):
    po = (await _create_po(client, paid_headers, supplier_id)).json()["data"]
    po_id, token = po["id"], po["portal_token"]
    await client.post(f"/api/purchase-orders/{po_id}/send", headers=paid_headers)
    items = (await client.get(f"/api/supplier-portal/order/{token}")).json()["items"]
    await client.post(f"/api/supplier-portal/order/{token}/respond", json={
        "items": [
            {"id": items[0]["id"], "confirmed_qty": 10, "confirmed_unit_price": 750},
            {"id": items[1]["id"], "confirmed_qty": 5, "confirmed_unit_price": 1200},
        ],
    })
    await client.post(f"/api/purchase-orders/{po_id}/accept", headers=paid_headers)

    # Receive only part of the first line
    grn = await client.post(f"/api/purchase-orders/{po_id}/receipts", json={
        "items": [{"purchase_order_item_id": items[0]["id"], "quantity": 4}],
    }, headers=paid_headers)
    assert grn.status_code == 201
    assert grn.json()["data"]["status"] == "receiving"


@pytest.mark.asyncio
async def test_cannot_receive_before_accept(client: AsyncClient, paid_headers: dict, supplier_id: str):
    po = (await _create_po(client, paid_headers, supplier_id)).json()["data"]
    po_id = po["id"]
    resp = await client.post(f"/api/purchase-orders/{po_id}/receipts", json={
        "items": [{"purchase_order_item_id": po["items"][0]["id"], "quantity": 1}],
    }, headers=paid_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_payables_summary(client: AsyncClient, paid_headers: dict, supplier_id: str):
    resp = await client.get("/api/supplier-bills/summary", headers=paid_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "total_outstanding" in body and "aging" in body


@pytest.mark.asyncio
async def test_portal_invalid_token_404(client: AsyncClient):
    resp = await client.get("/api/supplier-portal/order/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
