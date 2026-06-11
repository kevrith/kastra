"""Tests for field-level encryption of payment credentials."""
import os
from decimal import Decimal

import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient

from app.utils.encryption import decrypt_value, encrypt_value


# ---------------------------------------------------------------------------
# Unit tests — encryption utility (no DB required)
# ---------------------------------------------------------------------------

def test_encrypt_decrypt_roundtrip(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", key)
    # Reset cached fernet so it picks up the new key
    import app.utils.encryption as enc
    enc._fernet = None

    token = encrypt_value("sk_live_abc123")
    assert token != "sk_live_abc123"
    assert decrypt_value(token) == "sk_live_abc123"

    enc._fernet = None  # cleanup


def test_decrypt_falls_back_for_plaintext(monkeypatch):
    """Plain-text values stored before encryption was enabled must still be readable."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", key)
    import app.utils.encryption as enc
    enc._fernet = None

    result = decrypt_value("sk_live_this_was_never_encrypted")
    assert result == "sk_live_this_was_never_encrypted"

    enc._fernet = None


def test_no_key_passthrough(monkeypatch):
    """Without FIELD_ENCRYPTION_KEY the values pass through unchanged (dev mode)."""
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", "")
    import app.utils.encryption as enc
    enc._fernet = None

    assert encrypt_value("sk_live_abc") == "sk_live_abc"
    assert decrypt_value("sk_live_abc") == "sk_live_abc"

    enc._fernet = None


def test_encrypted_token_is_longer_than_plaintext(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", key)
    import app.utils.encryption as enc
    enc._fernet = None

    plain = "sk_live_abc123"
    token = encrypt_value(plain)
    assert len(token) > len(plain)

    enc._fernet = None


# ---------------------------------------------------------------------------
# Integration tests — credentials via the API
# ---------------------------------------------------------------------------

async def test_paystack_key_not_in_api_response(client: AsyncClient, auth_headers: dict):
    """Saving a Paystack key must never return the raw key in any API response."""
    resp = await client.put(
        "/api/organization",
        json={"paystack_secret_key": "sk_live_super_secret_12345"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.text
    assert "sk_live_super_secret_12345" not in body


async def test_paystack_configured_flag_set_after_save(client: AsyncClient, auth_headers: dict):
    resp = await client.put(
        "/api/organization",
        json={"paystack_secret_key": "sk_live_testkey"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["paystack_configured"] is True


async def test_paystack_configured_false_before_save(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/organization", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["paystack_configured"] is False


async def test_mpesa_configured_flag_set_after_full_save(client: AsyncClient, auth_headers: dict):
    resp = await client.put(
        "/api/organization",
        json={
            "mpesa_consumer_key": "ckey_abc",
            "mpesa_consumer_secret": "csecret_xyz",
            "mpesa_shortcode": "174379",
            "mpesa_passkey": "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["mpesa_configured"] is True


async def test_mpesa_credentials_not_in_api_response(client: AsyncClient, auth_headers: dict):
    secret = "mpesa_consumer_secret_value_xyz"
    resp = await client.put(
        "/api/organization",
        json={"mpesa_consumer_secret": secret},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert secret not in resp.text


async def test_get_org_never_returns_raw_credentials(client: AsyncClient, auth_headers: dict):
    """GET /api/organization must not include any credential fields."""
    await client.put(
        "/api/organization",
        json={
            "paystack_secret_key": "sk_live_must_not_appear",
            "mpesa_consumer_secret": "mpesa_secret_must_not_appear",
            "mpesa_passkey": "passkey_must_not_appear",
        },
        headers=auth_headers,
    )
    resp = await client.get("/api/organization", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.text
    assert "sk_live_must_not_appear" not in body
    assert "mpesa_secret_must_not_appear" not in body
    assert "passkey_must_not_appear" not in body
    # Only the boolean flags are present
    data = resp.json()["data"]
    assert "paystack_secret_key" not in data
    assert "mpesa_consumer_secret" not in data
    assert "mpesa_passkey" not in data


async def test_unauthenticated_cannot_access_org_settings(client: AsyncClient):
    resp = await client.get("/api/organization")
    assert resp.status_code in (401, 403)


async def test_unauthenticated_cannot_update_org_settings(client: AsyncClient):
    resp = await client.put("/api/organization", json={"paystack_secret_key": "sk_live_hacker"})
    assert resp.status_code in (401, 403)
