"""Production startup validation tests (Production Fix 2).

``Settings`` raises at construction time when ``APP_ENV=production`` keeps any
insecure default (SECRET_KEY, DEBUG, FIRST_ADMIN_PASSWORD, wildcard CORS, or a
partially/insecurely configured FIRST_SUPER_ADMIN_*), so a misconfigured
production process fails fast instead of starting.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings

_SECURE_KWARGS = dict(
    app_env="production",
    secret_key="a-long-random-production-secret-key-value",
    debug=False,
    first_admin_password="Str0ng!ProductionPassword",
    cors_origins="https://app.example.com",
)


def test_production_accepts_secure_config() -> None:
    Settings(**_SECURE_KWARGS)  # must not raise


def test_development_allows_insecure_defaults() -> None:
    Settings(app_env="development")  # must not raise despite dev defaults


def test_production_rejects_default_secret_key() -> None:
    kwargs = {**_SECURE_KWARGS, "secret_key": "CHANGE_ME"}
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(**kwargs)


def test_production_rejects_debug_true() -> None:
    kwargs = {**_SECURE_KWARGS, "debug": True}
    with pytest.raises(ValidationError, match="DEBUG"):
        Settings(**kwargs)


def test_production_rejects_default_admin_password() -> None:
    kwargs = {**_SECURE_KWARGS, "first_admin_password": "Admin12345!"}
    with pytest.raises(ValidationError, match="FIRST_ADMIN_PASSWORD"):
        Settings(**kwargs)


def test_production_rejects_wildcard_cors() -> None:
    kwargs = {**_SECURE_KWARGS, "cors_origins": "*"}
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(**kwargs)


def test_production_rejects_wildcard_mixed_with_explicit_origins() -> None:
    kwargs = {**_SECURE_KWARGS, "cors_origins": "*,https://example.com"}
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(**kwargs)


def test_production_reports_all_violations_together() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            secret_key="CHANGE_ME",
            debug=True,
            first_admin_password="Admin12345!",
            cors_origins="*",
        )
    message = str(exc_info.value)
    for keyword in ("SECRET_KEY", "DEBUG", "FIRST_ADMIN_PASSWORD", "CORS_ORIGINS"):
        assert keyword in message


def test_production_accepts_secure_config_with_super_admin() -> None:
    kwargs = {
        **_SECURE_KWARGS,
        "first_super_admin_username": "owner",
        "first_super_admin_password": "Str0ng!OwnerPassword",
    }
    Settings(**kwargs)  # must not raise


def test_production_accepts_unset_super_admin() -> None:
    Settings(**_SECURE_KWARGS)  # first_super_admin_* left unset entirely — must not raise


def test_production_rejects_super_admin_username_without_password() -> None:
    kwargs = {**_SECURE_KWARGS, "first_super_admin_username": "owner"}
    with pytest.raises(ValidationError, match="FIRST_SUPER_ADMIN_USERNAME and FIRST_SUPER_ADMIN_PASSWORD"):
        Settings(**kwargs)


def test_production_rejects_super_admin_password_without_username() -> None:
    kwargs = {**_SECURE_KWARGS, "first_super_admin_password": "Str0ng!OwnerPassword"}
    with pytest.raises(ValidationError, match="FIRST_SUPER_ADMIN_USERNAME and FIRST_SUPER_ADMIN_PASSWORD"):
        Settings(**kwargs)


def test_production_rejects_super_admin_default_admin_password() -> None:
    kwargs = {
        **_SECURE_KWARGS,
        "first_super_admin_username": "owner",
        "first_super_admin_password": "Admin12345!",
    }
    with pytest.raises(ValidationError, match="FIRST_SUPER_ADMIN_PASSWORD"):
        Settings(**kwargs)


def test_production_rejects_super_admin_username_matching_legacy_admin() -> None:
    kwargs = {
        **_SECURE_KWARGS,
        "first_admin_username": "platform-admin",
        "first_super_admin_username": "platform-admin",
        "first_super_admin_password": "Str0ng!OwnerPassword",
    }
    with pytest.raises(ValidationError, match="FIRST_SUPER_ADMIN_USERNAME must differ"):
        Settings(**kwargs)


def test_development_allows_partial_super_admin_config() -> None:
    # Dev stays lenient like every other insecure-default check; only
    # production fails fast.
    Settings(app_env="development", first_super_admin_username="owner")


def test_cors_origin_list_wildcard() -> None:
    assert Settings(app_env="development", cors_origins="*").cors_origin_list == ["*"]


def test_cors_origin_list_parses_comma_separated() -> None:
    settings = Settings(app_env="development", cors_origins="https://a.com, https://b.com")
    assert settings.cors_origin_list == ["https://a.com", "https://b.com"]
