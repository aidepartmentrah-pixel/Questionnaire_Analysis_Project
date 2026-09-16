"""Application configuration.

Settings are loaded from environment variables (and an optional .env file)
so the same code runs unmodified in local dev, tests and Docker.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> backend/
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Central, typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore",
    )

    app_name: str = "AutoML Demonstration API"
    environment: str = Field(default="development")  # development | test | production
    api_prefix: str = "/api"

    # Origins allowed to call the API from a browser (local Vite dev server,
    # local Docker frontend, etc.). Comma-separated in the environment.
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    # Where uploaded datasets and generated experiment artifacts are stored.
    # Always resolved relative to the backend package, never to an
    # arbitrary user-supplied path.
    storage_dir: Path = BACKEND_ROOT / "storage_data"
    uploads_dir: Path = storage_dir / "uploads"
    artifacts_dir: Path = storage_dir / "artifacts"

    max_upload_size_bytes: int = 25 * 1024 * 1024  # 25 MB

    def ensure_storage_dirs(self) -> None:
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
