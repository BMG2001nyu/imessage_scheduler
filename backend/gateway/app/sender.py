"""Send iMessage via macOS AppleScript (osascript). SENT = handed off to Messages.app; delivery/read status not detectable."""

import subprocess
import uuid

import structlog

logger = structlog.get_logger()


class SendResult:
    def __init__(self, success: bool, gateway_message_id: str, error: str | None = None):
        self.success = success
        self.gateway_message_id = gateway_message_id
        self.error = error


def send_imessage(phone_number: str, body: str, dry_run: bool = False) -> SendResult:
    """
    Send an iMessage via AppleScript.
    Returns a SendResult with success status and a local tracking ID.
    """
    gateway_message_id = str(uuid.uuid4())

    if dry_run:
        logger.info(
            "dry_run_send",
            phone=phone_number,
            body_preview=body[:50],
            gateway_message_id=gateway_message_id,
        )
        return SendResult(success=True, gateway_message_id=gateway_message_id)

    escaped_body = body.replace("\\", "\\\\").replace('"', '\\"')
    escaped_phone = phone_number.replace('"', '')

    script = f'''
    tell application "Messages"
        set targetService to 1st account whose service type = iMessage
        set targetBuddy to participant "{escaped_phone}" of targetService
        send "{escaped_body}" to targetBuddy
    end tell
    '''

    logger.info(
        "sending_imessage",
        phone=phone_number,
        body_length=len(body),
        gateway_message_id=gateway_message_id,
        messages_app="invoking via AppleScript",
    )

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            logger.info(
                "imessage_sent_successfully",
                phone=phone_number,
                gateway_message_id=gateway_message_id,
            )
            return SendResult(success=True, gateway_message_id=gateway_message_id)
        else:
            error_msg = result.stderr.strip() or "Unknown AppleScript error"
            logger.error(
                "imessage_send_failed",
                phone=phone_number,
                gateway_message_id=gateway_message_id,
                error=error_msg,
                returncode=result.returncode,
            )
            return SendResult(
                success=False,
                gateway_message_id=gateway_message_id,
                error=error_msg,
            )

    except subprocess.TimeoutExpired:
        error_msg = "AppleScript execution timed out after 30 seconds"
        logger.error(
            "imessage_send_timeout",
            phone=phone_number,
            gateway_message_id=gateway_message_id,
        )
        return SendResult(
            success=False, gateway_message_id=gateway_message_id, error=error_msg
        )
    except Exception as e:
        logger.error(
            "imessage_send_exception",
            phone=phone_number,
            gateway_message_id=gateway_message_id,
            error=str(e),
        )
        return SendResult(
            success=False, gateway_message_id=gateway_message_id, error=str(e)
        )
