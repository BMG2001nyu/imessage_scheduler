"""Tests for the iMessage sender module."""

from unittest.mock import patch, MagicMock
from app.sender import send_imessage, SendResult


class TestSendIMessage:
    def test_dry_run_succeeds(self):
        result = send_imessage("+15551234567", "Hello", dry_run=True)
        assert result.success is True
        assert result.gateway_message_id is not None
        assert result.error is None

    @patch("app.sender.subprocess.run")
    def test_successful_send(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        result = send_imessage("+15551234567", "Hello")
        assert result.success is True
        assert mock_run.called

    @patch("app.sender.subprocess.run")
    def test_failed_send(self, mock_run: MagicMock):
        mock_run.return_value = MagicMock(
            returncode=1, stderr="Messages got an error: buddy not found"
        )
        result = send_imessage("+15551234567", "Hello")
        assert result.success is False
        assert "buddy not found" in result.error

    @patch("app.sender.subprocess.run")
    def test_timeout(self, mock_run: MagicMock):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="osascript", timeout=30)
        result = send_imessage("+15551234567", "Hello")
        assert result.success is False
        assert "timed out" in result.error

    @patch("app.sender.subprocess.run")
    def test_exception(self, mock_run: MagicMock):
        mock_run.side_effect = OSError("No such file")
        result = send_imessage("+15551234567", "Hello")
        assert result.success is False
        assert "No such file" in result.error

    def test_message_body_escaping(self):
        result = send_imessage("+15551234567", 'Say "hello" to the world', dry_run=True)
        assert result.success is True
