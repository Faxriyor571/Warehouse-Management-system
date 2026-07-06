"""Authentication service: credential verification and token issuance."""
from __future__ import annotations

from datetime import datetime, timezone

import jwt
from sqlalchemy.orm import Session

from app.auth import security
from app.crud.company import company as company_crud
from app.crud.refresh_token import refresh_token as refresh_token_crud
from app.crud.user import user as user_crud
from app.models.enums import AuditAction, CompanyStatus
from app.models.user import User
from app.schemas.token import Token
from app.services import audit_service
from app.utils.exceptions import AuthenticationError


def authenticate(
    db: Session,
    username: str,
    password: str,
    *,
    company_slug: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User:
    """Verify credentials and return the user, or raise ``AuthenticationError``.

    Resolution order (API_SPECIFICATION.md §1, DATABASE_DESIGN.md §6):

        company_slug -> Company (must be active)
                     -> username within that company
                     -> User -> password

    When ``company_slug`` is omitted the username is resolved within the
    Super Admin / legacy scope (``company_id IS NULL``), so platform Super
    Admins and existing single-tenant users continue to log in as before.
    A CEO/Seller must supply their ``company_slug`` — omitting it simply
    fails to resolve their tenant-scoped account. No global username lookup
    is performed for tenant users.
    """
    if company_slug is not None:
        company = company_crud.get_by_slug(db, company_slug)
        if company is None or company.status != CompanyStatus.ACTIVE:
            audit_service.log_action(
                db,
                action=AuditAction.LOGIN_FAILED,
                user_id=None,
                description=f"Muvaffaqiyatsiz kirish urinishi (kompaniya): {company_slug}/{username}",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise AuthenticationError("Kompaniya topilmadi yoki faol emas")
        user = user_crud.get_by_username(db, username, company_id=company.id)
    else:
        user = user_crud.get_by_username(db, username)

    if user is None or not security.verify_password(password, user.hashed_password):
        audit_service.log_action(
            db,
            action=AuditAction.LOGIN_FAILED,
            user_id=user.id if user else None,
            description=f"Muvaffaqiyatsiz kirish urinishi: {username}",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise AuthenticationError("Login yoki parol noto'g'ri")

    if not user.is_active:
        raise AuthenticationError("Foydalanuvchi faol emas")

    return user


def issue_tokens(db: Session, user: User) -> Token:
    """Create an access + refresh token pair for a user and persist the refresh token.

    Legacy users (``role is None``) get tokens exactly as before — no extra
    claims. Users migrated to the new multi-tenant identity additionally get
    ``role``/``company_id``/``store_id`` claims, via the pre-existing
    ``**extra`` mechanism in :mod:`app.auth.security`.
    """
    extra: dict[str, object] = {}
    if user.role is not None:
        extra["role"] = user.role.value
        extra["company_id"] = user.company_id
        extra["store_id"] = user.store_id

    access_token = security.create_access_token(user.id, **extra)
    raw_refresh_token = security.create_refresh_token(user.id, **extra)

    refresh_payload = security.decode_token(raw_refresh_token)
    refresh_token_crud.create(
        db,
        {
            "user_id": user.id,
            "token_hash": security.hash_refresh_token(raw_refresh_token),
            "expires_at": datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc),
        },
    )

    return Token(access_token=access_token, refresh_token=raw_refresh_token)


def login(
    db: Session,
    username: str,
    password: str,
    *,
    company_slug: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[User, Token]:
    """Authenticate, update last-login, record audit and return tokens."""
    user = authenticate(
        db,
        username,
        password,
        company_slug=company_slug,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)

    audit_service.log_action(
        db,
        action=AuditAction.LOGIN,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        description=f"{user.username} tizimga kirdi",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return user, issue_tokens(db, user)


def refresh_tokens(db: Session, raw_refresh_token: str) -> Token:
    """Validate a refresh token, rotate it, and issue a new token pair."""
    try:
        payload = security.decode_token(raw_refresh_token)
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Refresh token yaroqsiz yoki muddati o'tgan") from exc

    if payload.get("type") != security.REFRESH_TOKEN_TYPE:
        raise AuthenticationError("Token turi noto'g'ri")

    subject = payload.get("sub")
    if subject is None:
        raise AuthenticationError("Token mazmuni noto'g'ri")

    # A stored row may not exist for tokens issued before this feature shipped
    # (e.g. an older session) — those still work via JWT validity alone,
    # matching prior behaviour exactly. A stored, revoked row always blocks.
    stored = refresh_token_crud.get_by_hash(db, security.hash_refresh_token(raw_refresh_token))
    if stored is not None and stored.revoked_at is not None:
        raise AuthenticationError("Refresh token bekor qilingan")

    user = user_crud.get(db, int(subject))
    if user is None or not user.is_active:
        raise AuthenticationError("Foydalanuvchi topilmadi yoki faol emas")

    if stored is not None:
        stored.revoked_at = datetime.now(timezone.utc)
        db.add(stored)
        db.commit()

    return issue_tokens(db, user)


def logout(
    db: Session,
    user: User,
    *,
    refresh_token: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Record a logout event and, if given, revoke the session's refresh token."""
    if refresh_token:
        stored = refresh_token_crud.get_by_hash(db, security.hash_refresh_token(refresh_token))
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = datetime.now(timezone.utc)
            db.add(stored)
            db.commit()

    audit_service.log_action(
        db,
        action=AuditAction.LOGOUT,
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        description=f"{user.username} tizimdan chiqdi",
        ip_address=ip_address,
        user_agent=user_agent,
    )
