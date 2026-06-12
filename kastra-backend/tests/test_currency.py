import httpx
from httpx import AsyncClient

from app.routers import currency as currency_router

# ---------------------------------------------------------------------------
# Fake httpx.AsyncClient — the currency router calls a third-party exchange
# rate API (open.er-api.com). Tests must never depend on that being reachable
# (flaky, slow, rate-limited), so we monkeypatch httpx.AsyncClient with a
# stand-in whose `.get()` is driven by a per-test handler function.
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, payload=None, raise_error=None):
        self._payload = payload or {}
        self._raise_error = raise_error

    def raise_for_status(self):
        if self._raise_error:
            raise self._raise_error

    def json(self):
        return self._payload


class _FakeAsyncClient:
    handler = None  # set per-test via _install_fake_http

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url):
        return _FakeAsyncClient.handler(url)


def _install_fake_http(monkeypatch, handler):
    _FakeAsyncClient.handler = staticmethod(handler)
    monkeypatch.setattr(currency_router.httpx, "AsyncClient", _FakeAsyncClient)


# ---------------------------------------------------------------------------
# /api/currency/currencies
# ---------------------------------------------------------------------------

async def test_list_currencies_returns_supported_list(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/currency/currencies", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "KES" in data
    assert "USD" in data
    assert data == currency_router.SUPPORTED_CURRENCIES


async def test_list_currencies_requires_auth(client: AsyncClient):
    resp = await client.get("/api/currency/currencies")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# /api/currency/rate
# ---------------------------------------------------------------------------

async def test_get_rate_kes_short_circuits_to_one(client: AsyncClient, auth_headers: dict):
    """KES -> KES must always be exactly 1, with no external call."""
    resp = await client.get("/api/currency/rate?code=KES", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["currency"] == "KES"
    assert body["rate_to_kes"] == 1.0


async def test_get_rate_rejects_malformed_code(client: AsyncClient, auth_headers: dict):
    for bad_code in ("US", "DOLLARZ", "12$", ""):
        resp = await client.get(f"/api/currency/rate?code={bad_code}", headers=auth_headers)
        assert resp.status_code == 422, bad_code


async def test_get_rate_normalizes_lowercase_and_whitespace(client: AsyncClient, auth_headers: dict, monkeypatch):
    seen = {}

    def handler(url):
        seen["url"] = url
        return _FakeResponse({"rates": {"KES": 129.5}, "time_last_update_utc": "Mon, 01 Jan 2026 00:00:00 +0000"})

    _install_fake_http(monkeypatch, handler)
    resp = await client.get("/api/currency/rate?code=usd", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["currency"] == "USD"
    assert "USD" in seen["url"]


async def test_get_rate_returns_live_rate_from_api(client: AsyncClient, auth_headers: dict, monkeypatch):
    def handler(url):
        return _FakeResponse({"rates": {"KES": 129.456789}, "time_last_update_utc": "Mon, 01 Jan 2026 00:00:00 +0000"})

    _install_fake_http(monkeypatch, handler)
    resp = await client.get("/api/currency/rate?code=USD", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["currency"] == "USD"
    # rate is rounded to 6 dp by the router
    assert body["rate_to_kes"] == 129.456789
    assert body["as_of"] == "Mon, 01 Jan 2026 00:00:00 +0000"


async def test_get_rate_returns_502_when_api_unreachable(client: AsyncClient, auth_headers: dict, monkeypatch):
    def handler(url):
        raise httpx.ConnectError("connection refused")

    _install_fake_http(monkeypatch, handler)
    resp = await client.get("/api/currency/rate?code=EUR", headers=auth_headers)
    assert resp.status_code == 502


async def test_get_rate_returns_502_on_http_error_status(client: AsyncClient, auth_headers: dict, monkeypatch):
    def handler(url):
        return _FakeResponse(raise_error=httpx.HTTPStatusError(
            "rate limited", request=httpx.Request("GET", url), response=httpx.Response(429, request=httpx.Request("GET", url)),
        ))

    _install_fake_http(monkeypatch, handler)
    resp = await client.get("/api/currency/rate?code=GBP", headers=auth_headers)
    assert resp.status_code == 502


async def test_get_rate_returns_404_when_currency_has_no_kes_rate(client: AsyncClient, auth_headers: dict, monkeypatch):
    def handler(url):
        return _FakeResponse({"rates": {"USD": 1.0}})  # no KES key for this base currency

    _install_fake_http(monkeypatch, handler)
    resp = await client.get("/api/currency/rate?code=AED", headers=auth_headers)
    assert resp.status_code == 404


async def test_get_rate_returns_502_on_malformed_json(client: AsyncClient, auth_headers: dict, monkeypatch):
    class _BadJsonResponse(_FakeResponse):
        def json(self):
            raise ValueError("not json")

    def handler(url):
        return _BadJsonResponse()

    _install_fake_http(monkeypatch, handler)
    resp = await client.get("/api/currency/rate?code=ZAR", headers=auth_headers)
    assert resp.status_code == 502


async def test_get_rate_requires_auth(client: AsyncClient):
    resp = await client.get("/api/currency/rate?code=USD")
    assert resp.status_code in (401, 403)
