"""Spend approvals: threshold holds a document, and the approver must be someone else.

The separation of duties is the whole control — a threshold anyone can self-clear
is decoration — so it gets its own tests on both the invoice and the PO path.
"""
from datetime import datetime, timezone

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def procurement_headers(client: AsyncClient, auth_headers: dict, db_session: AsyncSession) -> dict:
    """`auth_headers` with the org lifted off the free plan.

    Purchasing is plan-gated, so the PO tests need a paid org. Defined here
    rather than in conftest so this file stands on its own.
    """
    from app.models.organization import Organization

    me = await client.get("/api/auth/me", headers=auth_headers)
    org_id = me.json()["organization"]["id"]
    org = (await db_session.execute(
        select(Organization).where(Organization.id == org_id)
    )).scalar_one()
    org.plan = "business"
    await db_session.flush()
    return auth_headers


@pytest_asyncio.fixture
async def second_admin(client: AsyncClient, auth_headers: dict) -> dict:
    """A second admin in the same org, to act as the approver."""
    email = f"approver-{datetime.now(timezone.utc).timestamp()}@example.com"
    invite = await client.post("/api/team/invite", json={
        "email": email, "role": "admin", "display_name": "Approver",
    }, headers=auth_headers)
    await client.post("/api/team/accept-invite", json={
        "token": invite.json()["invite_token"], "password": "approverpass123",
    })
    login = await client.post("/api/auth/login", json={
        "email": email, "password": "approverpass123",
    })
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _set_threshold(client: AsyncClient, headers: dict, **kw) -> None:
    resp = await client.put("/api/organization", json=kw, headers=headers)
    assert resp.status_code == 200, resp.text


async def _invoice(client: AsyncClient, headers: dict, client_id: str, amount: float) -> dict:
    resp = await client.post("/api/invoices", json={
        "client_id": client_id,
        "items": [{"description": "Work", "quantity": 1, "unit_price": amount}],
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


# ── Invoices ─────────────────────────────────────────────────────────────────

async def test_no_threshold_means_no_approval_step(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    inv = await _invoice(client, auth_headers, sample_client_id, 999_999)
    assert inv["approval_status"] == "approved"


async def test_below_the_threshold_is_approved_outright(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    await _set_threshold(client, auth_headers, invoice_approval_threshold=50_000)
    inv = await _invoice(client, auth_headers, sample_client_id, 10_000)
    assert inv["approval_status"] == "approved"


async def test_at_or_above_the_threshold_is_held(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    await _set_threshold(client, auth_headers, invoice_approval_threshold=50_000)
    inv = await _invoice(client, auth_headers, sample_client_id, 50_000)
    assert inv["approval_status"] == "pending_approval", "the threshold is inclusive"


async def test_a_held_invoice_cannot_be_emailed(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    await _set_threshold(client, auth_headers, invoice_approval_threshold=50_000)
    inv = await _invoice(client, auth_headers, sample_client_id, 120_000)
    resp = await client.post(f"/api/invoices/{inv['id']}/email", headers=auth_headers)
    assert resp.status_code == 403


async def test_the_raiser_cannot_approve_their_own_invoice(
    client: AsyncClient, auth_headers: dict, sample_client_id: str
):
    await _set_threshold(client, auth_headers, invoice_approval_threshold=50_000)
    inv = await _invoice(client, auth_headers, sample_client_id, 120_000)
    resp = await client.post(f"/api/invoices/{inv['id']}/approve", headers=auth_headers)
    assert resp.status_code == 403
    assert "someone other than" in resp.json()["detail"]


async def test_a_second_admin_can_approve_and_it_unblocks_sending(
    client: AsyncClient, auth_headers: dict, second_admin: dict, sample_client_id: str
):
    await _set_threshold(client, auth_headers, invoice_approval_threshold=50_000)
    inv = await _invoice(client, auth_headers, sample_client_id, 120_000)

    resp = await client.post(f"/api/invoices/{inv['id']}/approve", headers=second_admin)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["approval_status"] == "approved"

    email = await client.post(f"/api/invoices/{inv['id']}/email", headers=auth_headers)
    assert email.status_code == 200, email.text


async def test_approving_something_not_held_is_rejected(
    client: AsyncClient, auth_headers: dict, second_admin: dict, sample_client_id: str
):
    inv = await _invoice(client, auth_headers, sample_client_id, 1_000)
    resp = await client.post(f"/api/invoices/{inv['id']}/approve", headers=second_admin)
    assert resp.status_code == 400


# ── Purchase orders ──────────────────────────────────────────────────────────

async def _supplier(client: AsyncClient, headers: dict) -> str:
    resp = await client.post("/api/suppliers", json={
        "name": f"Supplier {datetime.now(timezone.utc).timestamp()}", "phone": "254722000333",
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


async def _po(client: AsyncClient, headers: dict, supplier_id: str, price: float) -> str:
    resp = await client.post("/api/purchase-orders", json={
        "supplier_id": supplier_id,
        "items": [{"description": "Cement", "ordered_qty": 1, "ordered_unit_price": price}],
    }, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


async def test_a_po_below_the_threshold_goes_straight_out(
    client: AsyncClient, procurement_headers: dict
):
    await _set_threshold(client, procurement_headers, po_approval_threshold=100_000)
    sup = await _supplier(client, procurement_headers)
    po = await _po(client, procurement_headers, sup, 20_000)
    resp = await client.post(f"/api/purchase-orders/{po}/send", headers=procurement_headers)
    assert resp.json()["data"]["status"] == "sent"


async def test_a_po_over_the_threshold_is_held(client: AsyncClient, procurement_headers: dict):
    await _set_threshold(client, procurement_headers, po_approval_threshold=100_000)
    sup = await _supplier(client, procurement_headers)
    po = await _po(client, procurement_headers, sup, 250_000)
    resp = await client.post(f"/api/purchase-orders/{po}/send", headers=procurement_headers)
    assert resp.json()["data"]["status"] == "pending_approval"


async def test_the_raiser_cannot_approve_their_own_po(
    client: AsyncClient, procurement_headers: dict
):
    await _set_threshold(client, procurement_headers, po_approval_threshold=100_000)
    sup = await _supplier(client, procurement_headers)
    po = await _po(client, procurement_headers, sup, 250_000)
    await client.post(f"/api/purchase-orders/{po}/send", headers=procurement_headers)

    resp = await client.post(f"/api/purchase-orders/{po}/approve", headers=procurement_headers)
    assert resp.status_code == 403
    assert "someone other than" in resp.json()["detail"]


async def test_declining_returns_the_po_to_draft(
    client: AsyncClient, procurement_headers: dict, second_admin: dict
):
    await _set_threshold(client, procurement_headers, po_approval_threshold=100_000)
    sup = await _supplier(client, procurement_headers)
    po = await _po(client, procurement_headers, sup, 250_000)
    await client.post(f"/api/purchase-orders/{po}/send", headers=procurement_headers)

    resp = await client.post(f"/api/purchase-orders/{po}/decline-approval",
                             json={"reason": "Get a second quote"}, headers=second_admin)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "draft"
