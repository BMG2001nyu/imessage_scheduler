import asyncio
from datetime import datetime, timezone

import httpx
import structlog
from fastapi import FastAPI
from pydantic import BaseModel

from app.config import get_settings
from app.sender import send_imessage

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()
settings = get_settings()

app = FastAPI(
    title="iMessage Gateway",
    version="1.0.0",
    description="macOS gateway for sending iMessages via AppleScript",
)


class SendRequest(BaseModel):
    message_id: str
    phone_number: str
    body: str


class SendResponse(BaseModel):
    status: str
    gateway_message_id: str | None = None
    error: str | None = None


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "platform": "macOS",
        "dry_run": settings.dry_run,
        "messages_app_receives_requests": not settings.dry_run,
        "note": "When dry_run is false, each /send invokes Messages.app via AppleScript. "
        "Watch gateway logs for 'sending_imessage' and 'imessage_sent_successfully' to confirm.",
    }


@app.post("/send", response_model=SendResponse)
async def send(request: SendRequest):
    logger.info(
        "send_request_received",
        message_id=request.message_id,
        phone=request.phone_number,
    )

    result = send_imessage(
        phone_number=request.phone_number,
        body=request.body,
        dry_run=settings.dry_run,
    )

    asyncio.create_task(
        _report_status(
            message_id=request.message_id,
            status="SENT" if result.success else "FAILED",
            gateway_message_id=result.gateway_message_id,
            failure_reason=result.error,
        )
    )

    if result.success:
        return SendResponse(
            status="ACCEPTED",
            gateway_message_id=result.gateway_message_id,
        )
    else:
        return SendResponse(
            status="FAILED",
            gateway_message_id=result.gateway_message_id,
            error=result.error,
        )


async def _report_status(
    message_id: str,
    status: str,
    gateway_message_id: str,
    failure_reason: str | None = None,
) -> None:
    payload = {
        "message_id": message_id,
        "status": status,
        "gateway_message_id": gateway_message_id,
        "failure_reason": failure_reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "reporting_status_to_backend",
        message_id=message_id,
        status=status,
        callback_url=settings.backend_callback_url,
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(settings.backend_callback_url, json=payload)
            resp.raise_for_status()
            logger.info("status_reported_successfully", message_id=message_id)
    except Exception as e:
        logger.error(
            "status_report_failed",
            message_id=message_id,
            error=str(e),
        )
