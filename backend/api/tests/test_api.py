"""Integration tests for the messages REST API."""

import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient

from app.models.message import Message


class TestCreateMessage:
    @pytest.mark.asyncio
    async def test_creates_with_queued_status(self, client: AsyncClient):
        payload = {
            "phone_number": "+15551234567",
            "body": "Hello from tests!",
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "timezone": "UTC",
        }
        resp = await client.post("/api/messages", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["phone_number"] == "+15551234567"
        assert data["status"] == "QUEUED"
        assert data["attempts"] == 0
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_rejects_invalid_phone(self, client: AsyncClient):
        payload = {
            "phone_number": "not-a-phone",
            "body": "Hello",
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "timezone": "UTC",
        }
        resp = await client.post("/api/messages", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_empty_body(self, client: AsyncClient):
        payload = {
            "phone_number": "+15551234567",
            "body": "",
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "timezone": "UTC",
        }
        resp = await client.post("/api/messages", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_strips_phone_formatting(self, client: AsyncClient):
        payload = {
            "phone_number": "+1 (555) 123-4567",
            "body": "Test",
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "timezone": "UTC",
        }
        resp = await client.post("/api/messages", json=payload)
        assert resp.status_code == 201
        assert resp.json()["phone_number"] == "+15551234567"

    @pytest.mark.asyncio
    async def test_rejects_invalid_timezone(self, client: AsyncClient):
        payload = {
            "phone_number": "+15551234567",
            "body": "Test",
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "timezone": "Invalid/Timezone",
        }
        resp = await client.post("/api/messages", json=payload)
        assert resp.status_code == 422


class TestListMessages:
    @pytest.mark.asyncio
    async def test_returns_messages_with_total(self, client: AsyncClient):
        await client.post("/api/messages", json={
            "phone_number": "+15559999999",
            "body": "List test",
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "timezone": "UTC",
        })
        resp = await client.get("/api/messages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["messages"]) >= 1

    @pytest.mark.asyncio
    async def test_filters_by_status(self, client: AsyncClient, sample_message: Message):
        resp = await client.get("/api/messages?status=QUEUED")
        assert resp.status_code == 200
        for msg in resp.json()["messages"]:
            assert msg["status"] == "QUEUED"

    @pytest.mark.asyncio
    async def test_returns_newest_first(self, client: AsyncClient):
        """List endpoint returns messages ordered by scheduled_at descending."""
        for i in range(3):
            await client.post("/api/messages", json={
                "phone_number": "+15550000000",
                "body": f"Message {i}",
                "scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=i + 1)).isoformat(),
                "timezone": "UTC",
            })
        resp = await client.get("/api/messages")
        msgs = resp.json()["messages"]
        dates = [m["scheduled_at"] for m in msgs]
        assert dates == sorted(dates, reverse=True)


class TestGetMessage:
    @pytest.mark.asyncio
    async def test_returns_message_by_id(self, client: AsyncClient, sample_message: Message):
        resp = await client.get(f"/api/messages/{sample_message.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == str(sample_message.id)

    @pytest.mark.asyncio
    async def test_404_for_missing_message(self, client: AsyncClient):
        resp = await client.get("/api/messages/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


class TestUpdateMessage:
    @pytest.mark.asyncio
    async def test_updates_queued_message(self, client: AsyncClient, sample_message: Message):
        resp = await client.patch(
            f"/api/messages/{sample_message.id}",
            json={"body": "Updated body"},
        )
        assert resp.status_code == 200
        assert resp.json()["body"] == "Updated body"

    @pytest.mark.asyncio
    async def test_rejects_update_after_cancel(self, client: AsyncClient, sample_message: Message):
        await client.delete(f"/api/messages/{sample_message.id}")
        resp = await client.patch(
            f"/api/messages/{sample_message.id}",
            json={"body": "Should fail"},
        )
        assert resp.status_code == 409


class TestCancelMessage:
    @pytest.mark.asyncio
    async def test_cancels_queued_message(self, client: AsyncClient, sample_message: Message):
        resp = await client.delete(f"/api/messages/{sample_message.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "CANCELLED"

    @pytest.mark.asyncio
    async def test_double_cancel_returns_409(self, client: AsyncClient, sample_message: Message):
        await client.delete(f"/api/messages/{sample_message.id}")
        resp = await client.delete(f"/api/messages/{sample_message.id}")
        assert resp.status_code == 409


class TestSystemEndpoints:
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_stats_returns_counts(self, client: AsyncClient):
        resp = await client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "queued" in data
        assert "total" in data
        assert isinstance(data["total"], int)
