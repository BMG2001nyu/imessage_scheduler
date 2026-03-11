import json
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings

_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _ROOT / ".env"
_MODEL_CONFIG = {"extra": "ignore"}
if _ENV_FILE.exists():
    _MODEL_CONFIG["env_file"] = _ENV_FILE


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://imessage:imessage_dev@localhost:5432/imessage_scheduler"
    gateway_url: str = "http://localhost:8001"
    send_rate_per_hour: int = 1
    queue_poll_interval_seconds: int = 30
    max_retry_attempts: int = 3
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = _MODEL_CONFIG


@lru_cache
def get_settings() -> Settings:
    return Settings()
