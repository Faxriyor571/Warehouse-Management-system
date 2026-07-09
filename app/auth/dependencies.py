"""Authentication & authorization dependencies for FastAPI routes."""
from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth import security
from app.auth.support_session import ActingUser
from app.crud.company import company as company_crud
from app.crud.user import user as user_crud
from app.database import get_db
from app.models.enums import CompanyStatus, UserRole
from app.models.user import User
from app.utils.exceptions import AuthenticationError, PermissionDeniedError

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

    # A System Owner support session (see app.auth.support_session) carries
    # this claim. Re-verify the real user is actually a Super Admin against
    # the DB on every request — never trust the claim alone — before
    # resolving to the CEO-equivalent ActingUser every router/service reads.
    support_company_id = payload.get("support_company_id")
    if support_company_id is not None:
        if user.role != UserRole.SUPER_ADMIN:
            raise AuthenticationError("Seans yaroqsiz")
        company = company_crud.get(db, support_company_id)
        if company is None or company.status != CompanyStatus.ACTIVE:
            raise AuthenticationError("Kompaniya topilmadi yoki faol emas")
        return ActingUser(user, company=company)  # type: ignore[return-value]

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


def require_super_admin(current_user: CurrentUser) -> User:
    """Restrict a route to the new multi-tenant Super Admin role only.

    This checks the new ``role`` field exclusively — it does not consult the
    legacy ``is_superuser``/RBAC system, which remains a separate
    authorization path during the incremental migration.
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise PermissionDeniedError("Faqat platforma administratori uchun")
    return current_user


def require_ceo(current_user: CurrentUser) -> User:
    """Restrict a route to a company CEO (new multi-tenant role)."""
    if current_user.role != UserRole.CEO:
        raise PermissionDeniedError("Faqat kompaniya rahbari (CEO) uchun")
    return current_user


def require_ceo_or_seller(current_user: CurrentUser) -> User:
    """Allow either a CEO or a Seller (new multi-tenant roles)."""
    if current_user.role not in (UserRole.CEO, UserRole.SELLER):
        raise PermissionDeniedError("Faqat CEO yoki sotuvchi uchun")
    return current_user


RequireSuperAdmin = Annotated[User, Depends(require_super_admin)]
RequireCEO = Annotated[User, Depends(require_ceo)]
RequireCEOOrSeller = Annotated[User, Depends(require_ceo_or_seller)]


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
