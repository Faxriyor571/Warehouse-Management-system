"""Authentication & authorization dependencies for FastAPI routes."""
from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth import security
from app.crud.user import user as user_crud
from app.database import get_db
from app.models.user import User
from app.utils.exceptions import AuthenticationError

# tokenUrl is used by the OpenAPI docs "Authorize" button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve the authenticated user from a bearer access token."""
    try:
        payload = security.decode_token(token)
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Token yaroqsiz yoki muddati o'tgan") from exc

    if payload.get("type") != security.ACCESS_TOKEN_TYPE:
        raise AuthenticationError("Access token talab qilinadi")

    subject = payload.get("sub")
    if subject is None:
        raise AuthenticationError("Token mazmuni noto'g'ri")

    user = user_crud.get(db, int(subject))
    if user is None:
        raise AuthenticationError("Foydalanuvchi topilmadi")
    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the authenticated user is active."""
    if not current_user.is_active:
        raise AuthenticationError("Foydalanuvchi faol emas")
    return current_user


CurrentUser = Annotated[User, Depends(get_current_active_user)]
DbSession = Annotated[Session, Depends(get_db)]


class RequestContext:
    """Lightweight request metadata used for audit logging."""

    def __init__(self, ip_address: str | None, user_agent: str | None) -> None:
        self.ip_address = ip_address
        self.user_agent = user_agent


def get_request_context(request: Request) -> RequestContext:
    """Extract client IP and user-agent from the incoming request."""
    client_ip = request.client.host if request.client else None
    # Respect a reverse-proxy forwarded header when present.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    user_agent = request.headers.get("user-agent")
    return RequestContext(ip_address=client_ip, user_agent=user_agent)


ReqContext = Annotated[RequestContext, Depends(get_request_context)]
