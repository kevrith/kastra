"""Tests for the Africa's Talking SMS service — especially delivery-status parsing."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import sms_service
from app.services.sms_service import send_sms


def _at_response(body: dict):
    """Build a mock httpx response carrying an AT JSON body."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock(return_value=None)
    resp.json = MagicMock(return_value=body)
    resp.text = str(body)
    return resp


def _patch_post(resp):
    """Patch httpx.AsyncClient so the POST returns `resp`."""
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=resp)))
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return patch("app.services.sms_service.httpx.AsyncClient", return_value=mock_cm)


# ---------------------------------------------------------------------------
# Dev guard: no real send unless configured + production
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dev_mode_does_not_send():
    with patch.object(sms_service.settings, "at_api_key", ""), \
         _patch_post(_at_response({})) as mock_client:
        result = await send_sms("0712345678", "hi")
    assert result is True          # dev no-op returns True
    mock_client.assert_not_called()  # never hit the network


# ---------------------------------------------------------------------------
# Live sends: success vs the failures we actually observed from AT
# ---------------------------------------------------------------------------

def _live():
    """Context managers that make send_sms take the real (production) path."""
    return (
        patch.object(sms_service.settings, "at_api_key", "test_key"),
        patch.object(sms_service.settings, "environment", "production"),
    )


@pytest.mark.asyncio
async def test_success_returns_true():
    body = {"SMSMessageData": {"Message": "Sent to 1/1 Total Cost: KES 0.8000", "Recipients": [
        {"statusCode": 101, "number": "+254712345678", "status": "Success",
         "cost": "KES 0.8000", "messageId": "ATXid_abc"},
    ]}}
    a, b = _live()
    with a, b, _patch_post(_at_response(body)):
        result = await send_sms("0712345678", "hi")
    assert result is True


@pytest.mark.asyncio
async def test_user_in_blacklist_returns_false():
    # Exactly the response we saw live: HTTP 201 but zero delivered.
    body = {"SMSMessageData": {"Message": "Sent to 0/1 Total Cost: 0", "Recipients": [
        {"cost": "0", "messageId": "None", "number": "+254712345678",
         "status": "UserInBlacklist", "statusCode": 406},
    ]}}
    a, b = _live()
    with a, b, _patch_post(_at_response(body)):
        result = await send_sms("0712345678", "hi")
    assert result is False


@pytest.mark.asyncio
async def test_invalid_sender_id_returns_false():
    # No recipients queued at all.
    body = {"SMSMessageData": {"Message": "InvalidSenderId", "Recipients": []}}
    a, b = _live()
    with a, b, _patch_post(_at_response(body)):
        result = await send_sms("0712345678", "hi")
    assert result is False


@pytest.mark.asyncio
async def test_unparseable_phone_returns_false():
    result = await send_sms("not-a-phone", "hi")
    assert result is False
