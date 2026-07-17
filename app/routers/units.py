"""Unit-of-measurement endpoints (part of the product catalogue).

Company-scoped. No dedicated sidebar page exists for Units — it's purely an
implementation detail of the Products form (unit dropdown + inline "add new
unit"), so it's gated by the same ``Perm.PRODUCTS_VIEW``/``MANAGE`` as
Products itself rather than its own permission pair. The legacy single-tenant
admin bypasses via ``is_superuser`` inside ``require_perm``. Scoping is
uniform via ``current_user.company_id``.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import DbSession
from app.auth.permissions import require_perm
from app.crud.unit import unit as unit_crud
from app.models.unit import Unit
from app.models.user import User
from app.permissions.employee_matrix import Perm
from app.schemas.common import Message, PaginatedResponse
from app.schemas.unit import UnitCreate, UnitOut, UnitUpdate
from app.services import unit_service
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/units", tags=["Units"])

RequireCatalogueRead = Annotated[User, Depends(require_perm(Perm.PRODUCTS_VIEW))]
RequireCatalogueManage = Annotated[User, Depends(require_perm(Perm.PRODUCTS_MANAGE))]


@router.get("", response_model=PaginatedResponse[UnitOut], summary="Birliklar ro'yxati")
def list_units(
    db: DbSession,
    current_user: RequireCatalogueRead,
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[UnitOut]:
    params = PageParams(page=page, page_size=page_size)
    items, total = unit_crud.list_for_company(
        db, current_user.company_id, page_params=params, search=search
    )
    return PaginatedResponse[UnitOut](items=items, meta=make_meta(total, params))


@router.post(
    "",
    response_model=UnitOut,
    status_code=status.HTTP_201_CREATED,
    summary="Birlik qo'shish",
)
def create_unit(db: DbSession, current_user: RequireCatalogueManage, data: UnitCreate) -> Unit:
    return unit_service.create_unit(db, current_user.company_id, data)


@router.get("/{unit_id}", response_model=UnitOut, summary="Birlik ma'lumoti")
def get_unit(db: DbSession, current_user: RequireCatalogueRead, unit_id: int) -> Unit:
    obj = unit_crud.get_for_company(db, unit_id, current_user.company_id)
    if obj is None:
        raise NotFoundError(f"Birlik (id={unit_id}) topilmadi")
    return obj


@router.put("/{unit_id}", response_model=UnitOut, summary="Birlikni yangilash")
def update_unit(
    db: DbSession, current_user: RequireCatalogueManage, unit_id: int, data: UnitUpdate
) -> Unit:
    obj = unit_crud.get_for_company(db, unit_id, current_user.company_id)
    if obj is None:
        raise NotFoundError(f"Birlik (id={unit_id}) topilmadi")
    return unit_service.update_unit(db, obj, current_user.company_id, data)


@router.delete("/{unit_id}", response_model=Message, summary="Birlikni o'chirish")
def delete_unit(db: DbSession, current_user: RequireCatalogueManage, unit_id: int) -> Message:
    obj = unit_crud.get_for_company(db, unit_id, current_user.company_id)
    if obj is None:
        raise NotFoundError(f"Birlik (id={unit_id}) topilmadi")
    unit_service.delete_unit(db, obj)
    return Message(detail="Birlik o'chirildi")
