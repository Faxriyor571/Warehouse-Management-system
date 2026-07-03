"""Authentication endpoints: login, logout, refresh, current user."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.dependencies import CurrentUser, DbSession, ReqContext
from app.schemas.common import Message
from app.schemas.token import RefreshRequest, Token
from app.schemas.user import UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token, summary="Tizimga kirish (OAuth2 form)")
def login(
    db: DbSession,
    ctx: ReqContext,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """Authenticate with username/password and receive access + refresh tokens."""
    _, token = auth_service.login(
        db,
        form_data.username,
        form_data.password,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return token


@router.post("/refresh", response_model=Token, summary="Access tokenni yangilash")
def refresh(db: DbSession, body: RefreshRequest) -> Token:
    """Exchange a valid refresh token for a new token pair."""
    return auth_service.refresh_tokens(db, body.refresh_token)


@router.post("/logout", response_model=Message, summary="Tizimdan chiqish")
def logout(db: DbSession, current_user: CurrentUser, ctx: ReqContext) -> Message:
    """Record a logout event (client should discard its tokens)."""
    auth_service.logout(
        db, current_user, ip_address=ctx.ip_address, user_agent=ctx.user_agent
    )
    return Message(detail="Tizimdan muvaffaqiyatli chiqdingiz")


@router.get("/me", response_model=UserOut, summary="Joriy foydalanuvchi")
def me(current_user: CurrentUser) -> UserOut:
    """Return the currently authenticated user."""
    return current_user  # type: ignore[return-value]
