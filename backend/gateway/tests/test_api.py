"""Integration tests for the gateway API."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.sender import SendResult


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
@patch("app.main.send_imessage")
@patch("app.main._report_status", new_callable=AsyncMock)
async def test_send_success(mock_report: AsyncMock, mock_send: MagicMock):
    mock_send.return_value = SendResult(
        success=True, gateway_message_id="gw-test-123"
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/send",
            json={
                "message_id": "550e8400-e29b-41d4-a716-446655440000",
                "phone_number": "+15551234567",
                "body": "Test message",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ACCEPTED"
    assert data["gateway_message_id"] == "gw-test-123"


@pytest.mark.asyncio
@patch("app.main.send_imessage")
@patch("app.main._report_status", new_callable=AsyncMock)
async def test_send_failure(mock_report: AsyncMock, mock_send: MagicMock):
    mock_send.return_value = SendResult(
        success=False,
        gateway_message_id="gw-test-456",
        error="AppleScript error",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/send",
            json={
                "message_id": "550e8400-e29b-41d4-a716-446655440000",
                "phone_number": "+15551234567",
                "body": "Test message",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAILED"
    assert data["error"] == "AppleScript error"
