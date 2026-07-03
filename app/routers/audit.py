"""Audit log endpoints (read-only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import DbSession
from app.crud.audit_log import audit_log as audit_crud
from app.models.audit_log import AuditLog
from app.models.enums import AuditAction
from app.permissions.dependencies import require_permission
from app.schemas.audit import AuditLogOut
from app.schemas.common import PaginatedResponse
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/audit-logs", tags=["Audit Log"])


@router.get(
    "",
    response_model=PaginatedResponse[AuditLogOut],
    dependencies=[Depends(require_permission("audit.view"))],
    summary="Audit jurnali",
)
def list_audit_logs(
    db: DbSession,
    user_id: int | None = Query(default=None),
    action: AuditAction | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> PaginatedResponse[AuditLogOut]:
    filters: list = []
    if user_id is not None:
        filters.append(AuditLog.user_id == user_id)
    if action is not None:
        filters.append(AuditLog.action == action)
    if entity_type is not None:
        filters.append(AuditLog.entity_type == entity_type)

    params = PageParams(page=page, page_size=page_size)
    items, total = audit_crud.list(
        db, page_params=params, filters=filters, order_by=AuditLog.id.desc()
    )
    return PaginatedResponse[AuditLogOut](items=items, meta=make_meta(total, params))
