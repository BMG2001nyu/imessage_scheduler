import uuid

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()


class GatewayClient:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.gateway_url

    async def send_message(
        self, message_id: uuid.UUID, phone_number: str, body: str
    ) -> dict:
        """
        Send a message via the gateway.
        Returns the gateway response dict on success.
        Raises GatewayError on failure.
        """
        url = f"{self.base_url}/send"
        payload = {
            "message_id": str(message_id),
            "phone_number": phone_number,
            "body": body,
        }

        logger.info("gateway_send_request", message_id=str(message_id), url=url)

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                logger.info(
                    "gateway_send_success",
                    message_id=str(message_id),
                    gateway_response=data,
                )
                return data
            except httpx.HTTPStatusError as e:
                logger.error(
                    "gateway_send_http_error",
                    message_id=str(message_id),
                    status_code=e.response.status_code,
                    detail=e.response.text,
                )
                raise GatewayError(
                    f"Gateway returned {e.response.status_code}: {e.response.text}"
                ) from e
            except httpx.RequestError as e:
                logger.error(
                    "gateway_send_connection_error",
                    message_id=str(message_id),
                    error=str(e),
                )
                raise GatewayError(f"Gateway connection error: {e}") from e

    async def health_check(self) -> bool:
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
            except Exception:
                return False


class GatewayError(Exception):
    pass
