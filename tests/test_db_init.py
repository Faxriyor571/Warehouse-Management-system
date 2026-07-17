"""Seeding tests for app.db_init — legacy admin + optional System Owner bootstrap.

Uses its own isolated in-memory SQLite database (not the shared session-scoped
one from conftest.py) so each test can freely monkeypatch ``settings`` without
affecting other test modules.
"""
from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.db_init import seed_all, seed_super_admin
from app.models.enums import UserRole
from app.models.user import User


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    import app.models  # noqa: F401  register every table on the metadata

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def configured_super_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "first_super_admin_username", "owner")
    monkeypatch.setattr(settings, "first_super_admin_password", "Str0ng!OwnerPassword")
    monkeypatch.setattr(settings, "first_super_admin_fullname", "Tizim Egasi")


def _get(db: Session, username: str) -> User:
    return db.execute(select(User).where(User.username == username)).scalar_one()


# ---------------------------------------------------------------------------
# Fresh deployment
# ---------------------------------------------------------------------------


def test_fresh_deployment_seeds_legacy_admin_without_super_admin_by_default(db: Session) -> None:
    """Unconfigured FIRST_SUPER_ADMIN_* (the shared test-suite default) must
    not seed a System Owner — only the legacy admin is bootstrapped."""
    seed_all(db)

    admin = _get(db, settings.first_admin_username)
    assert admin.is_superuser is True
    assert admin.role is None  # never carries the new multi-tenant role

    super_admins = db.execute(select(User).where(User.role == UserRole.SUPER_ADMIN)).scalars().all()
    assert super_admins == []


def test_fresh_deployment_bootstraps_legacy_admin_and_super_admin(
    db: Session, configured_super_admin: None
) -> None:
    """A fresh deployment with FIRST_SUPER_ADMIN_* configured gets both
    accounts from a single seed_all() call — the two-step bootstrap the VPS
    deployment needs."""
    seed_all(db)

    admin = _get(db, settings.first_admin_username)
    assert admin.is_superuser is True
    assert admin.role is None

    owner = _get(db, "owner")
    assert owner.role == UserRole.SUPER_ADMIN
    assert owner.company_id is None
    assert owner.store_id is None
    assert owner.role_id is None
    assert owner.is_superuser is False  # never inherits the legacy flag
    assert owner.full_name == "Tizim Egasi"
    assert owner.is_active is True


# ---------------------------------------------------------------------------
# Idempotency (repeated startup)
# ---------------------------------------------------------------------------


def test_seed_super_admin_is_idempotent_across_restarts(
    db: Session, configured_super_admin: None
) -> None:
    seed_all(db)
    seed_super_admin(db)  # simulate a second process restart
    seed_super_admin(db)  # and a third

    owners = db.execute(select(User).where(User.username == "owner")).scalars().all()
    assert len(owners) == 1
    assert owners[0].role == UserRole.SUPER_ADMIN


def test_seed_all_is_idempotent_across_restarts(db: Session, configured_super_admin: None) -> None:
    seed_all(db)
    seed_all(db)  # full restart sequence, not just the one function

    admins = db.execute(select(User).where(User.username == settings.first_admin_username)).scalars().all()
    owners = db.execute(select(User).where(User.username == "owner")).scalars().all()
    assert len(admins) == 1
    assert len(owners) == 1


# ---------------------------------------------------------------------------
# Existing super admin already present
# ---------------------------------------------------------------------------


def test_seed_super_admin_leaves_existing_super_admin_untouched(
    db: Session, configured_super_admin: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_all(db)
    owner_before = _get(db, "owner")
    owner_id = owner_before.id

    # A later restart with a *different* configured password/fullname must
    # not overwrite the already-seeded row.
    monkeypatch.setattr(settings, "first_super_admin_password", "AnotherStr0ng!Password")
    monkeypatch.setattr(settings, "first_super_admin_fullname", "Someone Else")
    seed_super_admin(db)

    owner_after = _get(db, "owner")
    assert owner_after.id == owner_id
    assert owner_after.full_name == "Tizim Egasi"  # unchanged
    assert owner_after.hashed_password == owner_before.hashed_password  # unchanged


# ---------------------------------------------------------------------------
# Never auto-promotes the legacy admin
# ---------------------------------------------------------------------------


def test_seed_super_admin_skips_without_promoting_legacy_admin_on_username_collision(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If FIRST_SUPER_ADMIN_USERNAME collides with the already-seeded legacy
    admin's username, the legacy admin must be left completely untouched and
    no System Owner should be created — never silently promoted."""
    seed_all(db)  # seeds the legacy admin under settings.first_admin_username

    monkeypatch.setattr(settings, "first_super_admin_username", settings.first_admin_username)
    monkeypatch.setattr(settings, "first_super_admin_password", "Str0ng!OwnerPassword")
    seed_super_admin(db)

    admin = _get(db, settings.first_admin_username)
    assert admin.role is None  # still not a super_admin
    assert admin.is_superuser is True  # legacy identity untouched

    super_admins = db.execute(select(User).where(User.role == UserRole.SUPER_ADMIN)).scalars().all()
    assert super_admins == []


def test_seed_super_admin_unconfigured_never_creates_or_mutates_anyone(db: Session) -> None:
    assert settings.first_super_admin_username is None
    assert settings.first_super_admin_password is None

    seed_super_admin(db)

    assert db.execute(select(User)).scalars().all() == []
