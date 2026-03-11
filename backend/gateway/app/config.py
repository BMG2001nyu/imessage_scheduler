from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

# Repo root .env (works regardless of cwd)
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _ROOT / ".env"


class Settings(BaseSettings):
    backend_callback_url: str = "http://localhost:8000/api/webhooks/gateway-status"
    log_level: str = "INFO"
    dry_run: bool = False

    model_config = {"env_file": _ENV_FILE, "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
