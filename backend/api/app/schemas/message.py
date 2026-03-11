import re
import uuid
import zoneinfo
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.message import MessageStatus

E164_PATTERN = re.compile(r"^\+[1-9]\d{1,14}$")


def normalize_phone(value: str) -> str:
    """Strip formatting characters and validate E.164."""
    digits_and_plus = re.sub(r"[\s()\-.]", "", value)
    if not E164_PATTERN.match(digits_and_plus):
        raise ValueError(
            "Phone number must be in E.164 format (e.g. +15551234567)"
        )
    return digits_and_plus


class MessageCreate(BaseModel):
    phone_number: str = Field(..., min_length=2, max_length=20)
    body: str = Field(..., min_length=1, max_length=5000)
    scheduled_at: datetime
    timezone: str = Field(default="UTC", max_length=50)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone(v)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            zoneinfo.ZoneInfo(v)
        except (KeyError, zoneinfo.ZoneInfoNotFoundError):
            raise ValueError(f"Invalid timezone: {v}")
        return v


class MessageUpdate(BaseModel):
    phone_number: str | None = Field(None, min_length=2, max_length=20)
    body: str | None = Field(None, min_length=1, max_length=5000)
    scheduled_at: datetime | None = None
    timezone: str | None = Field(None, max_length=50)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_phone(v)
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                zoneinfo.ZoneInfo(v)
            except (KeyError, zoneinfo.ZoneInfoNotFoundError):
                raise ValueError(f"Invalid timezone: {v}")
        return v


class MessageResponse(BaseModel):
    id: uuid.UUID
    phone_number: str
    body: str
    scheduled_at: datetime
    timezone: str
    status: MessageStatus
    created_at: datetime
    updated_at: datetime
    accepted_at: datetime | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None
    attempts: int
    max_attempts: int
    gateway_message_id: str | None = None

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    total: int


class GatewayStatusUpdate(BaseModel):
    message_id: uuid.UUID
    status: MessageStatus
    gateway_message_id: str | None = None
    failure_reason: str | None = None
    timestamp: datetime | None = None


class StatsResponse(BaseModel):
    queued: int = 0
    accepted: int = 0
    sent: int = 0
    delivered: int = 0
    failed: int = 0
    cancelled: int = 0
    total: int = 0
