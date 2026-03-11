import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ws import manager
from app.db.session import get_db
from app.models.message import Message, MessageStatus
from app.schemas.message import (
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    MessageUpdate,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.post("", response_model=MessageResponse, status_code=201)
async def create_message(
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    msg = Message(
        phone_number=payload.phone_number,
        body=payload.body,
        scheduled_at=payload.scheduled_at,
        timezone=payload.timezone,
        status=MessageStatus.QUEUED,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)

    logger.info("message_created", message_id=str(msg.id), phone=msg.phone_number)

    response = MessageResponse.model_validate(msg)
    await manager.broadcast("message_created", response.model_dump(mode="json"))
    return response


@router.get("", response_model=MessageListResponse)
async def list_messages(
    status: MessageStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Message).order_by(Message.scheduled_at.desc(), Message.created_at.desc())
    count_query = select(func.count(Message.id))

    if status:
        query = query.where(Message.status == status)
        count_query = count_query.where(Message.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.limit(limit).offset(offset))
    messages = result.scalars().all()

    return MessageListResponse(
        messages=[MessageResponse.model_validate(m) for m in messages],
        total=total,
    )


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    msg = await db.get(Message, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return MessageResponse.model_validate(msg)


@router.patch("/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: uuid.UUID,
    payload: MessageUpdate,
    db: AsyncSession = Depends(get_db),
):
    msg = await db.get(Message, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if msg.status != MessageStatus.QUEUED:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot edit message with status {msg.status}",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(msg, field, value)
    msg.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(msg)

    logger.info("message_updated", message_id=str(msg.id))

    response = MessageResponse.model_validate(msg)
    await manager.broadcast("message_updated", response.model_dump(mode="json"))
    return response


@router.delete("/{message_id}", response_model=MessageResponse)
async def cancel_message(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    msg = await db.get(Message, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if msg.status != MessageStatus.QUEUED:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel message with status {msg.status}",
        )

    msg.status = MessageStatus.CANCELLED
    msg.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(msg)

    logger.info("message_cancelled", message_id=str(msg.id))

    response = MessageResponse.model_validate(msg)
    await manager.broadcast("message_cancelled", response.model_dump(mode="json"))
    return response
