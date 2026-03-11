import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.api.routes.messages import router as messages_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.ws import manager
from app.config import get_settings
from app.logging_config import setup_logging
from app.queue.worker import QueueWorker

setup_logging()
logger = structlog.get_logger()
settings = get_settings()
worker = QueueWorker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(worker.start())
    yield
    worker.stop()
    task.cancel()


app = FastAPI(
    title="iMessage Scheduler API",
    version="1.0.0",
    description="Backend API for scheduling and sending iMessages",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(messages_router)
app.include_router(health_router)
app.include_router(webhooks_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
