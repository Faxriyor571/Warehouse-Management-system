"""Permission-based authorization dependencies.

Usage in a route::

    @router.post("/", dependencies=[Depends(require_permission("product.manage"))])
    def create_product(...): ...
"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends

from app.auth.dependencies import get_current_active_user
from app.models.user import User
from app.utils.exceptions import PermissionDeniedError


def require_permission(*codes: str) -> Callable[[User], User]:
    """Build a dependency that requires ALL of the given permission codes.

    Superusers bypass the check. The resolved user is returned so the same
    dependency can also inject ``current_user`` if desired.
    """

    def checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.is_superuser:
            return current_user
        missing = [code for code in codes if not current_user.has_permission(code)]
        if missing:
            raise PermissionDeniedError(
                "Ushbu amal uchun ruxsat yo'q: " + ", ".join(missing)
            )
        return current_user

    return checker


def require_any_permission(*codes: str) -> Callable[[User], User]:
    """Build a dependency that requires AT LEAST ONE of the given codes."""

    def checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.is_superuser:
            return current_user
        if any(current_user.has_permission(code) for code in codes):
            return current_user
        raise PermissionDeniedError(
            "Ushbu amal uchun ruxsat yo'q: " + " yoki ".join(codes)
        )

    return checker


def require_superuser(current_user: User = Depends(get_current_active_user)) -> User:
    """Dependency that allows only the super administrator."""
    if not current_user.is_superuser:
        raise PermissionDeniedError("Faqat administrator uchun")
    return current_user
