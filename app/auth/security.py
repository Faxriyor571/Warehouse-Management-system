"""Security primitives: password hashing and JWT token handling.

- Passwords are hashed with bcrypt (used directly, no passlib) so the project
  runs cleanly on Python 3.13 where the ``crypt`` stdlib module was removed and
  passlib's bcrypt version detection is broken.
- Tokens are signed JWTs (access + refresh) using the secret key from settings.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.config import settings

# bcrypt operates on bytes and only considers the first 72 bytes of a password.
_BCRYPT_MAX_BYTES = 72

# Token type claim values.
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def _encode(password: str) -> bytes:
    """Encode a password to bytes, respecting bcrypt's 72-byte limit."""
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash (utf-8 string) for the given plaintext password."""
    hashed = bcrypt.hashpw(_encode(plain_password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(_encode(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed / empty hash -> treat as a failed verification, never crash.
        return False


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------
def _create_token(subject: str | int, token_type: str, expires_delta: timedelta, **extra: Any) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        **extra,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(subject: str | int, **extra: Any) -> str:
    """Create a short-lived access token for the given subject (user id)."""
    return _create_token(
        subject,
        ACCESS_TOKEN_TYPE,
        timedelta(minutes=settings.access_token_expire_minutes),
        **extra,
    )


def create_refresh_token(subject: str | int, **extra: Any) -> str:
    """Create a long-lived refresh token for the given subject (user id)."""
    return _create_token(
        subject,
        REFRESH_TOKEN_TYPE,
        timedelta(days=settings.refresh_token_expire_days),
        **extra,
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT, returning its payload.

    Raises:
        jwt.PyJWTError: if the token is invalid or expired.
    """
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
