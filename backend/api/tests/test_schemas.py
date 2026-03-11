"""Unit tests for Pydantic schemas and validation logic."""

import pytest
from app.schemas.message import MessageCreate, normalize_phone


class TestPhoneNormalization:
    def test_valid_e164(self):
        assert normalize_phone("+15551234567") == "+15551234567"

    def test_strips_formatting(self):
        assert normalize_phone("+1 (555) 123-4567") == "+15551234567"

    def test_strips_dots(self):
        assert normalize_phone("+1.555.123.4567") == "+15551234567"

    def test_invalid_no_plus(self):
        with pytest.raises(ValueError):
            normalize_phone("5551234567")

    def test_invalid_too_short(self):
        with pytest.raises(ValueError):
            normalize_phone("+1")

    def test_invalid_letters(self):
        with pytest.raises(ValueError):
            normalize_phone("+1555abc4567")


class TestMessageCreate:
    def test_valid_message(self):
        msg = MessageCreate(
            phone_number="+15551234567",
            body="Hello world",
            scheduled_at="2026-12-01T10:00:00Z",
            timezone="UTC",
        )
        assert msg.phone_number == "+15551234567"

    def test_phone_formatting_stripped(self):
        msg = MessageCreate(
            phone_number="+1 (555) 123-4567",
            body="Hello",
            scheduled_at="2026-12-01T10:00:00Z",
            timezone="America/New_York",
        )
        assert msg.phone_number == "+15551234567"

    def test_invalid_timezone(self):
        with pytest.raises(Exception):
            MessageCreate(
                phone_number="+15551234567",
                body="Hello",
                scheduled_at="2026-12-01T10:00:00Z",
                timezone="Invalid/Timezone",
            )

    def test_empty_body_rejected(self):
        with pytest.raises(Exception):
            MessageCreate(
                phone_number="+15551234567",
                body="",
                scheduled_at="2026-12-01T10:00:00Z",
                timezone="UTC",
            )
