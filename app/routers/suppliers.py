"""Supplier CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import CurrentUser, DbSession
from app.crud.supplier import supplier as supplier_crud
from app.models.enums import AuditAction
from app.models.supplier import Supplier
from app.permissions.dependencies import require_permission
from app.schemas.common import Message, PaginatedResponse
from app.schemas.supplier import SupplierCreate, SupplierOut, SupplierUpdate
from app.services import audit_service
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.get(
    "",
    response_model=PaginatedResponse[SupplierOut],
    dependencies=[Depends(require_permission("supplier.view"))],
    summary="Yetkazib beruvchilar ro'yxati",
)
def list_suppliers(
    db: DbSession,
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[SupplierOut]:
    params = PageParams(page=page, page_size=page_size)
    items, total = supplier_crud.list(
        db,
        page_params=params,
        search=search,
        search_fields=[Supplier.name, Supplier.phone, Supplier.responsible_person],
    )
    return PaginatedResponse[SupplierOut](items=items, meta=make_meta(total, params))


@router.post(
    "",
    response_model=SupplierOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("supplier.manage"))],
    summary="Yetkazib beruvchi qo'shish",
)
def create_supplier(db: DbSession, current_user: CurrentUser, data: SupplierCreate) -> Supplier:
    obj = supplier_crud.create(db, data.model_dump())
    audit_service.log_action(
        db,
        action=AuditAction.CREATE,
        user_id=current_user.id,
        entity_type="supplier",
        entity_id=obj.id,
        description=f"Yetkazib beruvchi qo'shildi: {obj.name}",
    )
    return obj


@router.get(
    "/{supplier_id}",
    response_model=SupplierOut,
    dependencies=[Depends(require_permission("supplier.view"))],
    summary="Yetkazib beruvchi ma'lumoti",
)
def get_supplier(db: DbSession, supplier_id: int) -> Supplier:
    return supplier_crud.get_or_404(db, supplier_id)


@router.put(
    "/{supplier_id}",
    response_model=SupplierOut,
    dependencies=[Depends(require_permission("supplier.manage"))],
    summary="Yetkazib beruvchini yangilash",
)
def update_supplier(
    db: DbSession, current_user: CurrentUser, supplier_id: int, data: SupplierUpdate
) -> Supplier:
    obj = supplier_crud.get_or_404(db, supplier_id)
    updated = supplier_crud.update(db, obj, data.model_dump(exclude_unset=True))
    audit_service.log_action(
        db,
        action=AuditAction.UPDATE,
        user_id=current_user.id,
        entity_type="supplier",
        entity_id=updated.id,
        description=f"Yetkazib beruvchi yangilandi: {updated.name}",
    )
    return updated


@router.delete(
    "/{supplier_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("supplier.manage"))],
    summary="Yetkazib beruvchini o'chirish",
)
def delete_supplier(db: DbSession, current_user: CurrentUser, supplier_id: int) -> Message:
    obj = supplier_crud.get_or_404(db, supplier_id)
    supplier_crud.remove(db, obj)
    audit_service.log_action(
        db,
        action=AuditAction.DELETE,
        user_id=current_user.id,
        entity_type="supplier",
        entity_id=supplier_id,
        description=f"Yetkazib beruvchi o'chirildi: {obj.name}",
    )
    return Message(detail="Yetkazib beruvchi o'chirildi")
