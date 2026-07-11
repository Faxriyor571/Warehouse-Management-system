"""Application configuration.

All settings are loaded from environment variables (``.env`` file) using
``pydantic-settings``. This keeps configuration in one place and validated,
following the 12-factor app methodology.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Sentinel defaults that must never reach a production deployment.
_DEFAULT_SECRET_KEY = "CHANGE_ME"
_DEFAULT_ADMIN_PASSWORD = "Admin12345!"

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
    secret_key: str = Field(default=_DEFAULT_SECRET_KEY)
    access_token_expire_minutes: int = Field(default=60)
    refresh_token_expire_days: int = Field(default=7)
    algorithm: str = Field(default="HS256")

    # --- CORS ---
    # Comma-separated list of allowed origins, or "*" (development only).
    cors_origins: str = Field(default="*")

    # --- Session cookie ---
    session_cookie_name: str = Field(default="wms_session")
    session_cookie_secure: bool = Field(default=False)

    # --- Uploads ---
    upload_dir: str = Field(default="uploads")
    max_upload_size_mb: int = Field(default=5)

    # --- First admin (seed) ---
    # This is the LEGACY single-tenant admin (``is_superuser=True``, ``role=None``)
    # — a completely different identity from the multi-tenant System Owner below.
    first_admin_username: str = Field(default="admin")
    first_admin_password: str = Field(default=_DEFAULT_ADMIN_PASSWORD)
    first_admin_fullname: str = Field(default="Bosh Administrator")

    # --- First System Owner / Super Admin (seed, optional) ---
    # The multi-tenant ``role=super_admin`` identity (DATABASE_DESIGN.md §3.3),
    # required to create/manage companies. Unlike the legacy admin above, this
    # account is opt-in: leaving both unset (the default) skips seeding it
    # entirely, since mapping the legacy admin to Super Admin is a business
    # decision this app never makes automatically (see db_init.seed_super_admin).
    first_super_admin_username: str | None = Field(default=None)
    first_super_admin_password: str | None = Field(default=None)
    first_super_admin_fullname: str = Field(default="Tizim Egasi")

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

    @computed_field  # type: ignore[misc]
    @property
    def cors_origin_list(self) -> list[str]:
        """Parsed CORS origins: ``["*"]`` or a list of explicit origins."""
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # ------------------------------------------------------------------
    # Production safety gate
    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def _reject_insecure_production_config(self) -> "Settings":
        """Fail fast at startup if APP_ENV=production keeps any dev default.

        Runs at ``Settings()`` construction time (i.e. on import of this
        module), so a misconfigured production process refuses to start
        rather than run with insecure defaults.
        """
        if self.app_env.lower() != "production":
            return self

        errors: list[str] = []
        if self.secret_key == _DEFAULT_SECRET_KEY:
            errors.append("SECRET_KEY must be set to a strong random value (not the default).")
        if self.debug:
            errors.append("DEBUG must be false in production.")
        if self.first_admin_password == _DEFAULT_ADMIN_PASSWORD:
            errors.append("FIRST_ADMIN_PASSWORD must be changed from the default value.")
        if self.first_super_admin_username or self.first_super_admin_password:
            # Configuring the System Owner seed is optional (unset = skipped
            # entirely), but a *partial* configuration is always a mistake —
            # it would silently no-op (seed_super_admin requires both) while
            # looking configured, so fail loud instead in production.
            if not (self.first_super_admin_username and self.first_super_admin_password):
                errors.append(
                    "FIRST_SUPER_ADMIN_USERNAME and FIRST_SUPER_ADMIN_PASSWORD must both be "
                    "set together (or both left unset to skip System Owner seeding)."
                )
            elif self.first_super_admin_password == _DEFAULT_ADMIN_PASSWORD:
                errors.append(
                    "FIRST_SUPER_ADMIN_PASSWORD must not reuse the default insecure admin password."
                )
            elif self.first_super_admin_username == self.first_admin_username:
                errors.append(
                    "FIRST_SUPER_ADMIN_USERNAME must differ from FIRST_ADMIN_USERNAME "
                    "(both are platform-level usernames and would collide)."
                )
        if "*" in self.cors_origin_list:
            errors.append(
                "CORS_ORIGINS must not include a wildcard '*' in production "
                "(found in: " + self.cors_origins + "); set explicit allowed origins."
            )
        if errors:
            raise ValueError(
                "Refusing to start: insecure configuration for APP_ENV=production:\n- "
                + "\n- ".join(errors)
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance (created once per process)."""
    return Settings()


# Convenience singleton importable as ``from app.config import settings``.
settings: Settings = get_settings()
