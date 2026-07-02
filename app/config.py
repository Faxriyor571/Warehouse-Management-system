"""Application configuration.

All settings are loaded from environment variables (``.env`` file) using
``pydantic-settings``. This keeps configuration in one place and validated,
following the 12-factor app methodology.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root directory (…/wms)
BASE_DIR: Path = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = Field(default="Ombor Boshqaruv Tizimi")
    app_env: str = Field(default="development")
    debug: bool = Field(default=True)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # --- Database ---
    postgres_user: str = Field(default="wms_user")
    postgres_password: str = Field(default="wms_password")
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="wms_db")

    # --- Security ---
    secret_key: str = Field(default="CHANGE_ME")
    access_token_expire_minutes: int = Field(default=60)
    refresh_token_expire_days: int = Field(default=7)
    algorithm: str = Field(default="HS256")

    # --- Session cookie ---
    session_cookie_name: str = Field(default="wms_session")
    session_cookie_secure: bool = Field(default=False)

    # --- Uploads ---
    upload_dir: str = Field(default="uploads")
    max_upload_size_mb: int = Field(default=5)

    # --- First admin (seed) ---
    first_admin_username: str = Field(default="admin")
    first_admin_password: str = Field(default="Admin12345!")
    first_admin_fullname: str = Field(default="Bosh Administrator")

    # ------------------------------------------------------------------
    # Derived / computed properties
    # ------------------------------------------------------------------
    @computed_field  # type: ignore[misc]
    @property
    def database_url(self) -> str:
        """Synchronous SQLAlchemy URL using the psycopg (v3) driver."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[misc]
    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @computed_field  # type: ignore[misc]
    @property
    def base_dir(self) -> Path:
        return BASE_DIR

    @computed_field  # type: ignore[misc]
    @property
    def upload_path(self) -> Path:
        path = BASE_DIR / self.upload_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @computed_field  # type: ignore[misc]
    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance (created once per process)."""
    return Settings()


# Convenience singleton importable as ``from app.config import settings``.
settings: Settings = get_settings()
