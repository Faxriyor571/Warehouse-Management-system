"""Dashboard endpoint (API_SPECIFICATION.md §13).

Gated by ``Perm.DASHBOARD_VIEW``, granted to every multi-tenant identity
(CEO and every employee job function). ``scope`` differs: a Cashier sees
their own store; everyone else (CEO, Warehouse Employee, Accountant) sees the
whole company. The legacy single-tenant admin bypasses via ``is_superuser``
inside ``require_perm`` (company-wide/NULL-scope view). Super Admin has no
access.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import DbSession
from app.auth.permissions import require_perm
from app.models.enums import EmployeeRole, UserRole
from app.models.user import User
from app.permissions.employee_matrix import Perm
from app.schemas.dashboard import DashboardStats
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

RequireDashboardActor = Annotated[User, Depends(require_perm(Perm.DASHBOARD_VIEW))]


@router.get("", response_model=DashboardStats, summary="Dashboard statistikasi va grafiklari")
def get_dashboard(db: DbSession, current_user: RequireDashboardActor) -> DashboardStats:
    is_store_confined = (
        current_user.role == UserRole.SELLER and current_user.employee_role == EmployeeRole.CASHIER
    )
    store_id = current_user.store_id if is_store_confined else None
    return dashboard_service.get_stats(db, company_id=current_user.company_id, store_id=store_id)
