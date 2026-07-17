"""Permission-code authorization for the new multi-tenant model.

Single dependency factory, ``require_perm(perm)``, replacing the ~15
individual per-module functions in ``app/auth/legacy_compat.py``. Every
router previously importing a ``legacy_compat.Require*`` alias should import
``require_perm`` instead and depend on the specific ``Perm`` its endpoint
needs (see ``app/permissions/employee_matrix.py`` for the full code list and
per-role grants).

The legacy single-tenant admin's ``is_superuser`` bypass is preserved
unchanged — this is the one thing every ``legacy_compat`` function did, and
it's kept here for full backward compatibility.
"""
from __future__ import annotations

from collections.abc import Callable

from app.auth.dependencies import CurrentUser
from app.models.user import User
from app.permissions.employee_matrix import Perm, permissions_for
from app.utils.exceptions import PermissionDeniedError


def require_perm(perm: Perm) -> Callable[[CurrentUser], User]:
    """Build a dependency that requires the given permission code.

    The legacy admin (``is_superuser=True``) bypasses this check entirely,
    exactly as every ``legacy_compat`` function did. A CEO or Seller is
    checked against ``employee_matrix.permissions_for`` — CEO's set already
    excludes the operational "manage" actions the ERP redesign reserves for
    employees (see that module for the full rationale).
    """

    def checker(current_user: CurrentUser) -> User:
        if current_user.is_superuser:  # TRANSITIONAL: legacy single-tenant admin
            return current_user
        allowed = permissions_for(current_user.role, current_user.employee_role)
        if perm not in allowed:
            raise PermissionDeniedError(f"Ushbu amal uchun ruxsat yo'q: {perm.value}")
        return current_user

    return checker
