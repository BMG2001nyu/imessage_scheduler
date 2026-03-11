"""Tests for queue ordering, claiming, status transitions, and reliability."""

import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message, MessageStatus, validate_transition


class TestStatusTransitions:
    """Verify the domain model's transition rules are correct."""

    def test_queued_can_become_accepted(self):
        assert validate_transition(MessageStatus.QUEUED, MessageStatus.ACCEPTED)

    def test_queued_can_become_cancelled(self):
        assert validate_transition(MessageStatus.QUEUED, MessageStatus.CANCELLED)

    def test_queued_cannot_become_sent_directly(self):
        assert not validate_transition(MessageStatus.QUEUED, MessageStatus.SENT)

    def test_accepted_can_become_sent(self):
        assert validate_transition(MessageStatus.ACCEPTED, MessageStatus.SENT)

    def test_accepted_can_become_failed(self):
        assert validate_transition(MessageStatus.ACCEPTED, MessageStatus.FAILED)

    def test_accepted_can_revert_to_queued_for_retry(self):
        assert validate_transition(MessageStatus.ACCEPTED, MessageStatus.QUEUED)

    def test_sent_can_become_delivered(self):
        assert validate_transition(MessageStatus.SENT, MessageStatus.DELIVERED)

    def test_sent_cannot_revert_to_queued(self):
        assert not validate_transition(MessageStatus.SENT, MessageStatus.QUEUED)

    def test_failed_is_terminal(self):
        assert not validate_transition(MessageStatus.FAILED, MessageStatus.QUEUED)

    def test_cancelled_is_terminal(self):
        assert not validate_transition(MessageStatus.CANCELLED, MessageStatus.QUEUED)


class TestFIFOOrdering:
    """Verify that queue claims respect FIFO order by scheduled_at, then created_at."""

    @pytest.mark.asyncio
    async def test_earlier_scheduled_at_is_claimed_first(self, db_session: AsyncSession):
        early = Message(
            id=uuid.uuid4(),
            phone_number="+15550000001",
            body="Earlier",
            scheduled_at=datetime.now(timezone.utc) - timedelta(hours=2),
            timezone="UTC",
            status=MessageStatus.QUEUED,
        )
        late = Message(
            id=uuid.uuid4(),
            phone_number="+15550000002",
            body="Later",
            scheduled_at=datetime.now(timezone.utc) - timedelta(hours=1),
            timezone="UTC",
            status=MessageStatus.QUEUED,
        )
        db_session.add_all([late, early])
        await db_session.commit()

        result = await db_session.execute(
            select(Message)
            .where(
                Message.status == MessageStatus.QUEUED,
                Message.scheduled_at <= datetime.now(timezone.utc),
            )
            .order_by(Message.scheduled_at.asc(), Message.created_at.asc())
            .limit(1)
        )
        first = result.scalar_one()
        assert first.id == early.id

    @pytest.mark.asyncio
    async def test_same_scheduled_at_uses_created_at_tiebreak(self, db_session: AsyncSession):
        same_time = datetime.now(timezone.utc) - timedelta(hours=1)
        first_created = Message(
            id=uuid.uuid4(),
            phone_number="+15550000001",
            body="Created first",
            scheduled_at=same_time,
            timezone="UTC",
            status=MessageStatus.QUEUED,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        second_created = Message(
            id=uuid.uuid4(),
            phone_number="+15550000002",
            body="Created second",
            scheduled_at=same_time,
            timezone="UTC",
            status=MessageStatus.QUEUED,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        db_session.add_all([second_created, first_created])
        await db_session.commit()

        result = await db_session.execute(
            select(Message)
            .where(
                Message.status == MessageStatus.QUEUED,
                Message.scheduled_at <= datetime.now(timezone.utc),
            )
            .order_by(Message.scheduled_at.asc(), Message.created_at.asc())
            .limit(1)
        )
        first = result.scalar_one()
        assert first.id == first_created.id


class TestClaimSafety:
    """Verify that only eligible messages are claimed and the claim is atomic."""

    @pytest.mark.asyncio
    async def test_future_messages_are_not_eligible(self, db_session: AsyncSession):
        future = Message(
            id=uuid.uuid4(),
            phone_number="+15550000001",
            body="Future message",
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
            timezone="UTC",
            status=MessageStatus.QUEUED,
        )
        db_session.add(future)
        await db_session.commit()

        result = await db_session.execute(
            select(Message)
            .where(
                Message.status == MessageStatus.QUEUED,
                Message.scheduled_at <= datetime.now(timezone.utc),
            )
            .limit(1)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_non_queued_messages_are_skipped(self, db_session: AsyncSession):
        sent = Message(
            id=uuid.uuid4(),
            phone_number="+15550000001",
            body="Already sent",
            scheduled_at=datetime.now(timezone.utc) - timedelta(hours=1),
            timezone="UTC",
            status=MessageStatus.SENT,
        )
        db_session.add(sent)
        await db_session.commit()

        result = await db_session.execute(
            select(Message)
            .where(
                Message.status == MessageStatus.QUEUED,
                Message.scheduled_at <= datetime.now(timezone.utc),
            )
            .limit(1)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_cancelled_messages_are_skipped(self, db_session: AsyncSession):
        cancelled = Message(
            id=uuid.uuid4(),
            phone_number="+15550000001",
            body="Cancelled",
            scheduled_at=datetime.now(timezone.utc) - timedelta(hours=1),
            timezone="UTC",
            status=MessageStatus.CANCELLED,
        )
        db_session.add(cancelled)
        await db_session.commit()

        result = await db_session.execute(
            select(Message)
            .where(
                Message.status == MessageStatus.QUEUED,
                Message.scheduled_at <= datetime.now(timezone.utc),
            )
            .limit(1)
        )
        assert result.scalar_one_or_none() is None


class TestRetryLogic:
    """Verify retry counting and failure states."""

    @pytest.mark.asyncio
    async def test_max_attempts_reached_is_terminal(self, db_session: AsyncSession):
        msg = Message(
            id=uuid.uuid4(),
            phone_number="+15550000001",
            body="Will fail",
            scheduled_at=datetime.now(timezone.utc) - timedelta(hours=1),
            timezone="UTC",
            status=MessageStatus.QUEUED,
            attempts=2,
            max_attempts=3,
        )
        db_session.add(msg)
        await db_session.commit()

        msg.attempts = 3
        msg.status = MessageStatus.FAILED
        msg.failure_reason = "Gateway timeout"
        await db_session.commit()
        await db_session.refresh(msg)

        assert msg.status == MessageStatus.FAILED
        assert msg.attempts == 3
        assert not validate_transition(MessageStatus.FAILED, MessageStatus.QUEUED)
