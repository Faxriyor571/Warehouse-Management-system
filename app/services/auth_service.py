"""Authentication service: credential verification and token issuance."""
from __future__ import annotations

import jwt
from sqlalchemy.orm import Session

from app.auth import security
from app.crud.user import user as user_crud
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.token import Token
from app.services import audit_service
from app.utils.exceptions import AuthenticationError


def authenticate(
    db: Session,
    username: str,
    password: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User:
    """Verify credentials and return the user, or raise ``AuthenticationError``."""
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


def issue_tokens(user: User) -> Token:
    """Create an access + refresh token pair for a user."""
    return Token(
        access_token=security.create_access_token(user.id),
        refresh_token=security.create_refresh_token(user.id),
    )


def login(
    db: Session,
    username: str,
    password: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[User, Token]:
    """Authenticate, update last-login, record audit and return tokens."""
    from datetime import datetime, timezone

    user = authenticate(
        db, username, password, ip_address=ip_address, user_agent=user_agent
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
    return user, issue_tokens(user)


def refresh_tokens(db: Session, refresh_token: str) -> Token:
    """Validate a refresh token and issue a new token pair."""
    try:
        payload = security.decode_token(refresh_token)
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Refresh token yaroqsiz yoki muddati o'tgan") from exc

    if payload.get("type") != security.REFRESH_TOKEN_TYPE:
        raise AuthenticationError("Token turi noto'g'ri")

    subject = payload.get("sub")
    if subject is None:
        raise AuthenticationError("Token mazmuni noto'g'ri")

    user = user_crud.get(db, int(subject))
    if user is None or not user.is_active:
        raise AuthenticationError("Foydalanuvchi topilmadi yoki faol emas")

    return issue_tokens(user)


def logout(
    db: Session,
    user: User,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Record a logout event.

    Tokens are stateless JWTs; the client discards them. We record the event
    for the audit trail.
    """
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
