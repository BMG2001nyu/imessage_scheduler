from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ws import manager
from app.config import get_settings
from app.db.session import get_db
from app.models.message import Message, MessageStatus
from app.schemas.message import StatsResponse
from app.services.gateway_client import GatewayClient

router = APIRouter(tags=["system"])


@router.get("/api/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "healthy"}


@router.get("/api/readiness")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Extended health check including gateway connectivity and system state."""
    settings = get_settings()
    gateway = GatewayClient()

    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    gateway_ok = await gateway.health_check()

    return {
        "status": "ready" if (db_ok and gateway_ok) else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "gateway": "connected" if gateway_ok else "unreachable",
        "websocket_clients": manager.client_count,
        "send_rate_per_hour": settings.send_rate_per_hour,
    }


@router.get("/api/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Message.status, func.count(Message.id)).group_by(Message.status)
    )
    counts = {row[0]: row[1] for row in result.all()}

    total = sum(counts.values())
    return StatsResponse(
        queued=counts.get(MessageStatus.QUEUED, 0),
        accepted=counts.get(MessageStatus.ACCEPTED, 0),
        sent=counts.get(MessageStatus.SENT, 0),
        delivered=counts.get(MessageStatus.DELIVERED, 0),
        failed=counts.get(MessageStatus.FAILED, 0),
        cancelled=counts.get(MessageStatus.CANCELLED, 0),
        total=total,
    )
