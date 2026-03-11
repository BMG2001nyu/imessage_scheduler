import json
from datetime import datetime
from uuid import UUID

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


class _JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


class ConnectionManager:
    """Manages WebSocket connections for real-time status push to frontend clients."""

    def __init__(self):
        self._connections: list[WebSocket] = []

    @property
    def client_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        logger.info("ws_client_connected", total=self.client_count)

    def disconnect(self, websocket: WebSocket) -> None:
        try:
            self._connections.remove(websocket)
        except ValueError:
            pass
        logger.info("ws_client_disconnected", total=self.client_count)

    async def broadcast(self, event: str, data: dict) -> None:
        if not self._connections:
            return
        payload = json.dumps({"event": event, "data": data}, cls=_JSONEncoder)
        stale: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            try:
                self._connections.remove(ws)
            except ValueError:
                pass


manager = ConnectionManager()
