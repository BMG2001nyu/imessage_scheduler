#!/usr/bin/env python3
"""Seed script: creates sample messages for demo. Run from repo root: python scripts/seed.py"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "api"))

from app.db.session import async_session_factory, engine
from app.models.message import Base, Message, MessageStatus


SAMPLE_MESSAGES = [
    {
        "phone_number": "+15551234567",
        "body": "Hey! Just a reminder about our meeting tomorrow at 2 PM. Looking forward to it!",
        "scheduled_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "timezone": "America/New_York",
        "status": MessageStatus.QUEUED,
    },
    {
        "phone_number": "+15559876543",
        "body": "Happy birthday! Hope you have an amazing day! 🎂",
        "scheduled_at": datetime.now(timezone.utc) + timedelta(hours=3),
        "timezone": "America/Los_Angeles",
        "status": MessageStatus.QUEUED,
    },
    {
        "phone_number": "+15555551234",
        "body": "Don't forget to pick up groceries on the way home. We need milk, eggs, and bread.",
        "scheduled_at": datetime.now(timezone.utc) - timedelta(hours=2),
        "timezone": "America/Chicago",
        "status": MessageStatus.SENT,
        "sent_at": datetime.now(timezone.utc) - timedelta(hours=1, minutes=45),
        "accepted_at": datetime.now(timezone.utc) - timedelta(hours=1, minutes=50),
        "attempts": 1,
    },
    {
        "phone_number": "+15553334444",
        "body": "The project proposal looks great. Let's discuss the timeline on Monday.",
        "scheduled_at": datetime.now(timezone.utc) - timedelta(hours=5),
        "timezone": "UTC",
        "status": MessageStatus.FAILED,
        "failed_at": datetime.now(timezone.utc) - timedelta(hours=4),
        "failure_reason": "Gateway connection timeout",
        "attempts": 3,
    },
    {
        "phone_number": "+15557778888",
        "body": "See you at the restaurant at 7! I made a reservation for 4.",
        "scheduled_at": datetime.now(timezone.utc) + timedelta(hours=6),
        "timezone": "America/Denver",
        "status": MessageStatus.QUEUED,
    },
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        for data in SAMPLE_MESSAGES:
            msg = Message(**data)
            session.add(msg)
        await session.commit()

    print(f"Seeded {len(SAMPLE_MESSAGES)} sample messages.")


if __name__ == "__main__":
    asyncio.run(seed())
