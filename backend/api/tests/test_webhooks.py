"""Integration tests for the gateway webhook endpoint and status transitions."""

import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message, MessageStatus


@pytest_asyncio.fixture
async def accepted_message(db_session: AsyncSession) -> Message:
    msg = Message(
        id=uuid.uuid4(),
        phone_number="+15550001111",
        body="Webhook test message",
        scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        timezone="UTC",
        status=MessageStatus.ACCEPTED,
        accepted_at=datetime.now(timezone.utc) - timedelta(minutes=3),
        attempts=1,
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)
    return msg


class TestGatewayWebhook:
    @pytest.mark.asyncio
    async def test_accepted_to_sent_transition(self, client: AsyncClient, accepted_message: Message):
        resp = await client.post("/api/webhooks/gateway-status", json={
            "message_id": str(accepted_message.id),
            "status": "SENT",
            "gateway_message_id": "gw-123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SENT"
        assert data["gateway_message_id"] == "gw-123"
        assert data["sent_at"] is not None

    @pytest.mark.asyncio
    async def test_accepted_to_failed_transition(self, client: AsyncClient, accepted_message: Message):
        resp = await client.post("/api/webhooks/gateway-status", json={
            "message_id": str(accepted_message.id),
            "status": "FAILED",
            "failure_reason": "AppleScript error: buddy not found",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "FAILED"
        assert data["failure_reason"] == "AppleScript error: buddy not found"

    @pytest.mark.asyncio
    async def test_invalid_transition_returns_409(self, client: AsyncClient, sample_message: Message):
        """QUEUED -> SENT skips ACCEPTED, which is not allowed."""
        resp = await client.post("/api/webhooks/gateway-status", json={
            "message_id": str(sample_message.id),
            "status": "SENT",
        })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_unknown_message_returns_404(self, client: AsyncClient):
        resp = await client.post("/api/webhooks/gateway-status", json={
            "message_id": "00000000-0000-0000-0000-000000000000",
            "status": "SENT",
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_duplicate_webhook_is_idempotent(self, client: AsyncClient, accepted_message: Message):
        """Sending the same SENT webhook twice should succeed first time, 409 second time."""
        resp1 = await client.post("/api/webhooks/gateway-status", json={
            "message_id": str(accepted_message.id),
            "status": "SENT",
        })
        assert resp1.status_code == 200

        resp2 = await client.post("/api/webhooks/gateway-status", json={
            "message_id": str(accepted_message.id),
            "status": "SENT",
        })
        # SENT -> SENT is not a valid transition, so second call is rejected
        assert resp2.status_code == 409
