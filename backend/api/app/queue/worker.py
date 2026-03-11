"""FIFO queue worker: recover stale claims on startup, rate-limit sends, claim via FOR UPDATE SKIP LOCKED, call gateway, retry or fail."""

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ws import manager
from app.config import get_settings
from app.db.session import async_session_factory
from app.models.message import Message, MessageStatus
from app.schemas.message import MessageResponse
from app.services.gateway_client import GatewayClient, GatewayError

logger = structlog.get_logger()

STALE_CLAIM_THRESHOLD = timedelta(minutes=5)


class QueueWorker:
    def __init__(self):
        self.settings = get_settings()
        self.gateway = GatewayClient()
        self._running = False
        self._last_send_time: datetime | None = None

    async def start(self) -> None:
        self._running = True
        logger.info(
            "queue_worker_started",
            poll_interval=self.settings.queue_poll_interval_seconds,
            rate_per_hour=self.settings.send_rate_per_hour,
        )

        await self._recover_stale_claims()
        await self._load_last_send_time()

        while self._running:
            try:
                await self._tick()
            except Exception:
                logger.exception("queue_worker_tick_error")
            await asyncio.sleep(self.settings.queue_poll_interval_seconds)

    def stop(self) -> None:
        self._running = False
        logger.info("queue_worker_stopped")

    # -- Startup helpers -------------------------------------------------------

    async def _recover_stale_claims(self) -> None:
        """
        On startup, revert messages stuck in ACCEPTED from a prior crash.
        A message is "stale" if claimed_at is older than STALE_CLAIM_THRESHOLD.
        """
        cutoff = datetime.now(timezone.utc) - STALE_CLAIM_THRESHOLD
        async with async_session_factory() as session:
            result = await session.execute(
                update(Message)
                .where(
                    Message.status == MessageStatus.ACCEPTED,
                    Message.claimed_at < cutoff,
                )
                .values(
                    status=MessageStatus.QUEUED,
                    claimed_at=None,
                    updated_at=datetime.now(timezone.utc),
                )
                .returning(Message.id)
            )
            recovered_ids = [row[0] for row in result.all()]
            await session.commit()

            if recovered_ids:
                logger.warning(
                    "recovered_stale_claims",
                    count=len(recovered_ids),
                    message_ids=[str(mid) for mid in recovered_ids],
                )

    async def _load_last_send_time(self) -> None:
        """Load the most recent successful send (sent_at) from the DB so rate limiting survives restarts.
        We use sent_at, not accepted_at: failed attempts set accepted_at but not sent_at, and we must
        not block the queue for an hour after every failed gateway call."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(Message.sent_at)
                .where(
                    Message.status == MessageStatus.SENT,
                    Message.sent_at.is_not(None),
                )
                .order_by(Message.sent_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row:
                self._last_send_time = row
                logger.info("rate_limit_restored", last_send_at=row.isoformat())

    # -- Main loop -------------------------------------------------------------

    def _seconds_between_sends(self) -> float:
        return 3600.0 / self.settings.send_rate_per_hour

    async def _tick(self) -> None:
        if self._last_send_time:
            elapsed = (datetime.now(timezone.utc) - self._last_send_time).total_seconds()
            if elapsed < self._seconds_between_sends():
                return

        async with async_session_factory() as session:
            msg = await self._claim_next(session)
            if not msg:
                return
            await self._process_message(session, msg)

    # -- Claim -----------------------------------------------------------------

    async def _claim_next(self, session: AsyncSession) -> Message | None:
        """
        Atomically claim the next due message.
        Uses FOR UPDATE SKIP LOCKED to prevent double-claiming across concurrent workers.
        FIFO order: scheduled_at ASC, created_at ASC.
        """
        now = datetime.now(timezone.utc)
        query = (
            select(Message)
            .where(
                Message.status == MessageStatus.QUEUED,
                Message.scheduled_at <= now,
            )
            .order_by(Message.scheduled_at.asc(), Message.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        result = await session.execute(query)
        msg = result.scalar_one_or_none()
        if not msg:
            return None

        msg.status = MessageStatus.ACCEPTED
        msg.accepted_at = now
        msg.claimed_at = now
        msg.attempts += 1
        msg.updated_at = now
        await session.commit()

        logger.info(
            "message_claimed",
            message_id=str(msg.id),
            attempt=msg.attempts,
            phone=msg.phone_number,
            scheduled_at=msg.scheduled_at.isoformat(),
        )
        await _broadcast_status(msg)
        return msg

    # -- Process ---------------------------------------------------------------

    async def _process_message(self, session: AsyncSession, msg: Message) -> None:
        try:
            result = await self.gateway.send_message(msg.id, msg.phone_number, msg.body)
            self._last_send_time = datetime.now(timezone.utc)

            if result.get("gateway_message_id"):
                msg.gateway_message_id = result["gateway_message_id"]
                msg.updated_at = datetime.now(timezone.utc)
                await session.commit()

            logger.info(
                "gateway_accepted",
                message_id=str(msg.id),
                gateway_message_id=msg.gateway_message_id,
            )

        except GatewayError as e:
            logger.error(
                "gateway_send_failed",
                message_id=str(msg.id),
                attempt=msg.attempts,
                max_attempts=msg.max_attempts,
                error=str(e),
            )
            await self._handle_failure(session, msg, str(e))

    # -- Failure & retry -------------------------------------------------------

    async def _handle_failure(
        self, session: AsyncSession, msg: Message, reason: str
    ) -> None:
        now = datetime.now(timezone.utc)

        if msg.attempts >= msg.max_attempts:
            msg.status = MessageStatus.FAILED
            msg.failed_at = now
            msg.failure_reason = reason
            msg.updated_at = now
            logger.info(
                "message_permanently_failed",
                message_id=str(msg.id),
                attempts=msg.attempts,
            )
        else:
            # Exponential backoff: 5min, 15min, 45min
            backoff_seconds = 300 * (3 ** (msg.attempts - 1))
            msg.status = MessageStatus.QUEUED
            msg.claimed_at = None
            msg.scheduled_at = now + timedelta(seconds=backoff_seconds)
            msg.updated_at = now
            logger.info(
                "message_retry_scheduled",
                message_id=str(msg.id),
                attempt=msg.attempts,
                retry_in_seconds=backoff_seconds,
                next_attempt_at=(now + timedelta(seconds=backoff_seconds)).isoformat(),
            )

        await session.commit()
        await _broadcast_status(msg)


async def _broadcast_status(msg: Message) -> None:
    response = MessageResponse.model_validate(msg)
    await manager.broadcast("message_status_changed", response.model_dump(mode="json"))
