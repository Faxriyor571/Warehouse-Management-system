"""Unit-of-measurement CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import CurrentUser, DbSession
from app.crud.unit import unit as unit_crud
from app.models.enums import AuditAction
from app.models.unit import Unit
from app.permissions.dependencies import require_permission
from app.schemas.common import Message, PaginatedResponse
from app.schemas.unit import UnitCreate, UnitOut, UnitUpdate
from app.services import audit_service
from app.utils.exceptions import ConflictError
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/units", tags=["Units"])


@router.get(
    "",
    response_model=PaginatedResponse[UnitOut],
    dependencies=[Depends(require_permission("unit.view"))],
    summary="Birliklar ro'yxati",
)
def list_units(
    db: DbSession,
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> PaginatedResponse[UnitOut]:
    params = PageParams(page=page, page_size=page_size)
    items, total = unit_crud.list(
        db, page_params=params, search=search, search_fields=[Unit.name, Unit.short_name]
    )
    return PaginatedResponse[UnitOut](items=items, meta=make_meta(total, params))


@router.post(
    "",
    response_model=UnitOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("unit.manage"))],
    summary="Birlik qo'shish",
)
def create_unit(db: DbSession, current_user: CurrentUser, data: UnitCreate) -> Unit:
    if unit_crud.get_by_name(db, data.name) is not None:
        raise ConflictError(f"'{data.name}' birligi allaqachon mavjud")
    obj = unit_crud.create(db, data.model_dump())
    audit_service.log_action(
        db,
        action=AuditAction.CREATE,
        user_id=current_user.id,
        entity_type="unit",
        entity_id=obj.id,
        description=f"Birlik qo'shildi: {obj.name}",
    )
    return obj


@router.get(
    "/{unit_id}",
    response_model=UnitOut,
    dependencies=[Depends(require_permission("unit.view"))],
    summary="Birlik ma'lumoti",
)
def get_unit(db: DbSession, unit_id: int) -> Unit:
    return unit_crud.get_or_404(db, unit_id)


@router.put(
    "/{unit_id}",
    response_model=UnitOut,
    dependencies=[Depends(require_permission("unit.manage"))],
    summary="Birlikni yangilash",
)
def update_unit(db: DbSession, current_user: CurrentUser, unit_id: int, data: UnitUpdate) -> Unit:
    obj = unit_crud.get_or_404(db, unit_id)
    updated = unit_crud.update(db, obj, data.model_dump(exclude_unset=True))
    audit_service.log_action(
        db,
        action=AuditAction.UPDATE,
        user_id=current_user.id,
        entity_type="unit",
        entity_id=updated.id,
        description=f"Birlik yangilandi: {updated.name}",
    )
    return updated


@router.delete(
    "/{unit_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("unit.manage"))],
    summary="Birlikni o'chirish",
)
def delete_unit(db: DbSession, current_user: CurrentUser, unit_id: int) -> Message:
    obj = unit_crud.get_or_404(db, unit_id)
    unit_crud.hard_delete(db, obj)
    audit_service.log_action(
        db,
        action=AuditAction.DELETE,
        user_id=current_user.id,
        entity_type="unit",
        entity_id=unit_id,
        description=f"Birlik o'chirildi: {obj.name}",
    )
    return Message(detail="Birlik o'chirildi")
