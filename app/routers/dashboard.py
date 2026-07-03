"""Dashboard endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import DbSession
from app.permissions.dependencies import require_permission
from app.schemas.dashboard import DashboardStats
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "",
    response_model=DashboardStats,
    dependencies=[Depends(require_permission("dashboard.view"))],
    summary="Dashboard statistikasi va grafiklari",
)
def get_dashboard(db: DbSession) -> DashboardStats:
    return dashboard_service.get_stats(db)
