"""Organization profile: read, update, and the write-only payment credentials."""
from httpx import AsyncClient


async def _get_org(client, headers):
    resp = await client.get("/api/organization", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ── Read ─────────────────────────────────────────────────────────────────────

async def test_get_organization(client: AsyncClient, auth_headers: dict):
    org = await _get_org(client, auth_headers)
    assert org["name"].startswith("Test Biz")
    assert org["plan"] == "free"
    assert org["payment_terms_days"] > 0


async def test_get_organization_requires_auth(client: AsyncClient):
    resp = await client.get("/api/organization")
    assert resp.status_code in (401, 403)


async def test_credentials_are_reported_as_flags_not_values(
    client: AsyncClient, auth_headers: dict
):
    org = await _get_org(client, auth_headers)
    assert org["paystack_configured"] is False
    assert org["mpesa_configured"] is False
    for secret_field in (
        "paystack_secret_key", "mpesa_consumer_key", "mpesa_consumer_secret",
        "mpesa_passkey", "etims_auth_token",
    ):
        assert secret_field not in org, f"{secret_field} must never be returned"


# ── Update ───────────────────────────────────────────────────────────────────

async def test_update_organization_profile(client: AsyncClient, auth_headers: dict):
    resp = await client.put("/api/organization", json={
        "name": "Kastra Builders Ltd",
        "phone": "254700111222",
        "address": "Westlands, Nairobi",
        "kra_pin": "A123456789Z",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "Kastra Builders Ltd"
    assert data["kra_pin"] == "A123456789Z"


async def test_update_is_partial(client: AsyncClient, auth_headers: dict):
    before = await _get_org(client, auth_headers)
    resp = await client.put("/api/organization", json={"phone": "254799888777"}, headers=auth_headers)
    assert resp.status_code == 200
    after = resp.json()["data"]
    assert after["phone"] == "254799888777"
    assert after["name"] == before["name"]


async def test_update_payment_terms(client: AsyncClient, auth_headers: dict):
    resp = await client.put("/api/organization", json={
        "payment_terms_days": 45, "quotation_validity_days": 21,
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["payment_terms_days"] == 45
    assert data["quotation_validity_days"] == 21


async def test_paystack_key_is_stored_but_only_surfaced_as_a_flag(
    client: AsyncClient, auth_headers: dict
):
    resp = await client.put("/api/organization", json={
        "paystack_secret_key": "sk_test_dummy_value_for_tests",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["paystack_configured"] is True
    assert "paystack_secret_key" not in data


async def test_mpesa_is_only_configured_once_every_field_is_set(
    client: AsyncClient, auth_headers: dict
):
    partial = await client.put("/api/organization", json={
        "mpesa_consumer_key": "dummy-key",
    }, headers=auth_headers)
    assert partial.json()["data"]["mpesa_configured"] is False

    complete = await client.put("/api/organization", json={
        "mpesa_consumer_secret": "dummy-secret",
        "mpesa_shortcode": "174379",
        "mpesa_passkey": "dummy-passkey",
    }, headers=auth_headers)
    assert complete.json()["data"]["mpesa_configured"] is True


async def test_update_rejects_a_wrongly_typed_field(client: AsyncClient, auth_headers: dict):
    resp = await client.put("/api/organization", json={
        "payment_terms_days": "not-a-number",
    }, headers=auth_headers)
    assert resp.status_code == 422


async def test_update_requires_auth(client: AsyncClient):
    resp = await client.put("/api/organization", json={"name": "Hijacked"})
    assert resp.status_code in (401, 403)


# ── Org isolation ────────────────────────────────────────────────────────────

async def test_each_org_sees_only_its_own_profile(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict
):
    await client.put("/api/organization", json={"name": "First Org"}, headers=auth_headers)
    other = await _get_org(client, other_org_headers)
    assert other["name"] != "First Org"


async def test_updating_your_org_does_not_touch_another(
    client: AsyncClient, auth_headers: dict, other_org_headers: dict
):
    before = await _get_org(client, other_org_headers)
    await client.put("/api/organization", json={
        "name": "Renamed", "phone": "254700000000",
    }, headers=auth_headers)
    after = await _get_org(client, other_org_headers)
    assert after["name"] == before["name"]
    assert after["phone"] == before["phone"]
