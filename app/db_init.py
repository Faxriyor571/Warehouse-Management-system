"""Database initialisation and idempotent seeding.

On application startup this module ensures the schema exists (for convenient
local runs) and seeds the baseline data required for the app to be usable:
permissions, roles, the first admin user, payment methods and common units.

All seeding is idempotent — running it repeatedly is safe.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import security
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models.enums import PaymentMethodType, RoleName
from app.models.payment_method import PaymentMethod
from app.models.role import Permission, Role
from app.models.unit import Unit
from app.models.user import User
from app.permissions.constants import (
    DEFAULT_ROLE_PERMISSIONS,
    PERMISSIONS,
    ROLE_DESCRIPTIONS,
)

logger = logging.getLogger("wms.init")

# Default payment methods: (name, type)
_DEFAULT_PAYMENT_METHODS: list[tuple[str, PaymentMethodType]] = [
    ("Naqd", PaymentMethodType.CASH),
    ("Click", PaymentMethodType.CLICK),
    ("Payme", PaymentMethodType.PAYME),
    ("Bank", PaymentMethodType.BANK),
    ("Qarz", PaymentMethodType.DEBT),
]

# Default units: (name, short_name)
_DEFAULT_UNITS: list[tuple[str, str]] = [
    ("Dona", "dona"),
    ("Kilogramm", "kg"),
    ("Litr", "l"),
    ("Quti", "quti"),
    ("Qop", "qop"),
    ("Metr", "m"),
]


def create_tables() -> None:
    """Create any missing tables (convenience for local/dev runs)."""
    # Import the models package so every table is registered on the metadata.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def seed_permissions(db: Session) -> dict[str, Permission]:
    existing = {p.code: p for p in db.execute(select(Permission)).scalars().all()}
    for code, (name, group) in PERMISSIONS.items():
        if code not in existing:
            perm = Permission(code=code, name=name, group=group)
            db.add(perm)
            existing[code] = perm
    db.commit()
    return {p.code: p for p in db.execute(select(Permission)).scalars().all()}


def seed_roles(db: Session, permissions: dict[str, Permission]) -> dict[str, Role]:
    existing = {r.name: r for r in db.execute(select(Role)).scalars().all()}
    for role_name in RoleName:
        role = existing.get(role_name.value)
        if role is None:
            role = Role(
                name=role_name.value,
                description=ROLE_DESCRIPTIONS.get(role_name),
                is_system=True,
            )
            db.add(role)
            existing[role_name.value] = role
        # Assign default permissions (only fill if empty to respect admin edits).
        if not role.permissions:
            codes = DEFAULT_ROLE_PERMISSIONS.get(role_name, [])
            role.permissions = [permissions[c] for c in codes if c in permissions]
    db.commit()
    return {r.name: r for r in db.execute(select(Role)).scalars().all()}


def seed_admin(db: Session, roles: dict[str, Role]) -> None:
    admin_role = roles.get(RoleName.ADMIN.value)
    if admin_role is None:
        logger.warning("Admin roli topilmadi, admin foydalanuvchi yaratilmadi")
        return
    existing = db.execute(
        select(User).where(User.username == settings.first_admin_username)
    ).scalar_one_or_none()
    if existing is not None:
        return
    admin = User(
        username=settings.first_admin_username,
        full_name=settings.first_admin_fullname,
        hashed_password=security.hash_password(settings.first_admin_password),
        role_id=admin_role.id,
        is_active=True,
        is_superuser=True,
    )
    db.add(admin)
    db.commit()
    logger.info("Boshlang'ich admin foydalanuvchi yaratildi: %s", settings.first_admin_username)


def seed_payment_methods(db: Session) -> None:
    existing = {pm.name for pm in db.execute(select(PaymentMethod)).scalars().all()}
    for name, type_ in _DEFAULT_PAYMENT_METHODS:
        if name not in existing:
            db.add(PaymentMethod(name=name, type=type_, is_active=True, is_system=True))
    db.commit()


def seed_units(db: Session) -> None:
    existing = {u.name for u in db.execute(select(Unit)).scalars().all()}
    for name, short in _DEFAULT_UNITS:
        if name not in existing:
            db.add(Unit(name=name, short_name=short, is_active=True))
    db.commit()


def seed_all(db: Session) -> None:
    """Run every seeding step in the correct order."""
    permissions = seed_permissions(db)
    roles = seed_roles(db, permissions)
    seed_admin(db, roles)
    seed_payment_methods(db)
    seed_units(db)


def init_db() -> None:
    """Entry point called on startup: create tables and seed baseline data."""
    create_tables()
    with SessionLocal() as db:
        seed_all(db)
    logger.info("Ma'lumotlar bazasi tayyor (jadvallar va boshlang'ich ma'lumotlar)")
