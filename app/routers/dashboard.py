"""Dashboard endpoint (API_SPECIFICATION.md §13).

Role-based, same response shape for CEO/Seller (``scope`` differs): a Seller
sees their own store; a CEO sees the whole company. The legacy single-tenant
admin is admitted transitionally (company-wide/NULL-scope view). Super Admin
has no access.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.auth.dependencies import DbSession
from app.auth.legacy_compat import RequireDashboardActor
from app.models.enums import UserRole
from app.schemas.dashboard import DashboardStats
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardStats, summary="Dashboard statistikasi va grafiklari")
def get_dashboard(db: DbSession, current_user: RequireDashboardActor) -> DashboardStats:
    store_id = current_user.store_id if current_user.role == UserRole.SELLER else None
    return dashboard_service.get_stats(db, company_id=current_user.company_id, store_id=store_id)
