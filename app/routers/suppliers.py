"""Supplier endpoints. Company-scoped (DATABASE_DESIGN.md §3.10, "Partners"
category, same pattern as Customers).

Company-wide (no store scope), gated by ``Perm.SUPPLIERS_MANAGE`` (a supplier
is looked up/created inline while recording a Stock In — no debt/lifecycle
concept exists for Suppliers, so there's no separate view/manage split). The
legacy single-tenant admin bypasses via ``is_superuser`` inside
``require_perm`` and operates in the NULL-company scope. Super Admin has no
access.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import DbSession
from app.auth.permissions import require_perm
from app.crud.supplier import supplier as supplier_crud
from app.models.enums import AuditAction
from app.models.supplier import Supplier
from app.models.user import User
from app.permissions.employee_matrix import Perm
from app.schemas.common import Message, PaginatedResponse
from app.schemas.supplier import SupplierCreate, SupplierOut, SupplierUpdate
from app.services import audit_service
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])

RequireSupplierActor = Annotated[User, Depends(require_perm(Perm.SUPPLIERS_MANAGE))]


def _resolve_company(current_user: User) -> int | None:
    return current_user.company_id  # None for the legacy single-tenant admin


def _get_supplier_or_404(db: DbSession, current_user: User, supplier_id: int) -> Supplier:
    obj = supplier_crud.get_for_company(db, supplier_id, _resolve_company(current_user))
    if obj is None:
        raise NotFoundError(f"Yetkazib beruvchi (id={supplier_id}) topilmadi")
    return obj


@router.get("", response_model=PaginatedResponse[SupplierOut], summary="Yetkazib beruvchilar ro'yxati")
def list_suppliers(
    db: DbSession,
    current_user: RequireSupplierActor,
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[SupplierOut]:
    params = PageParams(page=page, page_size=page_size)
    items, total = supplier_crud.list_for_company(
        db, _resolve_company(current_user), page_params=params, search=search
    )
    return PaginatedResponse[SupplierOut](items=items, meta=make_meta(total, params))


@router.post(
    "",
    response_model=SupplierOut,
    status_code=status.HTTP_201_CREATED,
    summary="Yetkazib beruvchi qo'shish",
)
def create_supplier(db: DbSession, current_user: RequireSupplierActor, data: SupplierCreate) -> Supplier:
    payload = data.model_dump()
    payload["company_id"] = _resolve_company(current_user)
    obj = supplier_crud.create(db, payload)
    audit_service.log_action(
        db,
        action=AuditAction.CREATE,
        user_id=current_user.id,
        entity_type="supplier",
        entity_id=obj.id,
        description=f"Yetkazib beruvchi qo'shildi: {obj.name}",
    )
    return obj


@router.get("/{supplier_id}", response_model=SupplierOut, summary="Yetkazib beruvchi ma'lumoti")
def get_supplier(db: DbSession, current_user: RequireSupplierActor, supplier_id: int) -> Supplier:
    return _get_supplier_or_404(db, current_user, supplier_id)


@router.put("/{supplier_id}", response_model=SupplierOut, summary="Yetkazib beruvchini yangilash")
def update_supplier(
    db: DbSession, current_user: RequireSupplierActor, supplier_id: int, data: SupplierUpdate
) -> Supplier:
    obj = _get_supplier_or_404(db, current_user, supplier_id)
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


@router.delete("/{supplier_id}", response_model=Message, summary="Yetkazib beruvchini o'chirish")
def delete_supplier(db: DbSession, current_user: RequireSupplierActor, supplier_id: int) -> Message:
    obj = _get_supplier_or_404(db, current_user, supplier_id)
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
