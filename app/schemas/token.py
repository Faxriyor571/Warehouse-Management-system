"""Authentication token schemas."""
from __future__ import annotations

from pydantic import BaseModel


class Token(BaseModel):
    """Access + refresh token pair returned on login/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Decoded JWT payload of interest."""

    sub: str | None = None
    type: str | None = None


class RefreshRequest(BaseModel):
    """Body for the refresh-token endpoint."""

    refresh_token: str


class LoginRequest(BaseModel):
    """JSON login body (alternative to OAuth2 form)."""

    username: str
    password: str
