from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ws import manager
from app.db.session import get_db
from app.models.message import Message, MessageStatus, validate_transition
from app.schemas.message import GatewayStatusUpdate, MessageResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/gateway-status", response_model=MessageResponse)
async def gateway_status_callback(
    payload: GatewayStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    msg = await db.get(Message, payload.message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if not validate_transition(msg.status, payload.status):
        logger.warning(
            "invalid_status_transition",
            message_id=str(msg.id),
            current=msg.status.value,
            requested=payload.status.value,
        )
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition from {msg.status} to {payload.status}",
        )

    now = payload.timestamp or datetime.now(timezone.utc)
    msg.status = payload.status
    msg.updated_at = now

    if payload.status == MessageStatus.SENT:
        msg.sent_at = now
    elif payload.status == MessageStatus.DELIVERED:
        msg.delivered_at = now
    elif payload.status == MessageStatus.FAILED:
        msg.failed_at = now
        msg.failure_reason = payload.failure_reason

    if payload.gateway_message_id:
        msg.gateway_message_id = payload.gateway_message_id

    await db.flush()
    await db.refresh(msg)

    logger.info(
        "gateway_status_update",
        message_id=str(msg.id),
        new_status=payload.status.value,
    )

    response = MessageResponse.model_validate(msg)
    await manager.broadcast("message_status_changed", response.model_dump(mode="json"))
    return response
