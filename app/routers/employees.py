"""Employee (Seller) endpoints (API_SPECIFICATION.md §4). CEO only.

All operations are scoped to the CEO's own company (``company_id`` from the
token, never client-supplied). Super Admin and Seller have no access.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Response, status

from app.auth.dependencies import DbSession, RequireCEO
from app.crud.user import user as user_crud
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeOut,
    EmployeePasswordReset,
    EmployeeUpdate,
)
from app.services import employee_service
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/employees", tags=["Employees"])


def _to_out(seller: User, store_name: str) -> EmployeeOut:
    return EmployeeOut(
        id=seller.id,
        username=seller.username,
        full_name=seller.full_name,
        email=seller.email,
        phone=seller.phone,
        role=seller.role,  # type: ignore[arg-type]
        store_id=seller.store_id,  # type: ignore[arg-type]
        store_name=store_name,
        is_active=seller.is_active,
        last_login_at=seller.last_login_at,
        created_at=seller.created_at,
    )


def _get_seller_or_404(db: DbSession, company_id: int, seller_id: int) -> User:
    seller = user_crud.get_seller_for_company(db, seller_id, company_id)
    if seller is None:
        raise NotFoundError(f"Sotuvchi (id={seller_id}) topilmadi")
    return seller


@router.post(
    "",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Sotuvchi qo'shish (CEO)",
)
def create_employee(db: DbSession, current_user: RequireCEO, data: EmployeeCreate) -> EmployeeOut:
    seller, store_name = employee_service.create_seller(db, current_user.company_id, data)  # type: ignore[arg-type]
    return _to_out(seller, store_name)


@router.get("", response_model=PaginatedResponse[EmployeeOut], summary="Sotuvchilar ro'yxati (CEO)")
def list_employees(
    db: DbSession,
    current_user: RequireCEO,
    search: str | None = Query(default=None, description="Username / ism bo'yicha qidiruv"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[EmployeeOut]:
    params = PageParams(page=page, page_size=page_size)
    rows, total = user_crud.list_sellers_for_company(
        db, current_user.company_id, page_params=params, search=search  # type: ignore[arg-type]
    )
    items = [_to_out(seller, store_name) for seller, store_name in rows]
    return PaginatedResponse[EmployeeOut](items=items, meta=make_meta(total, params))


@router.get("/{employee_id}", response_model=EmployeeOut, summary="Sotuvchi ma'lumoti (CEO)")
def get_employee(db: DbSession, current_user: RequireCEO, employee_id: int) -> EmployeeOut:
    seller = _get_seller_or_404(db, current_user.company_id, employee_id)  # type: ignore[arg-type]
    store_name = employee_service.store_name_for(db, current_user.company_id, seller.store_id)  # type: ignore[arg-type]
    return _to_out(seller, store_name)


@router.put("/{employee_id}", response_model=EmployeeOut, summary="Sotuvchini yangilash (CEO)")
def update_employee(
    db: DbSession, current_user: RequireCEO, employee_id: int, data: EmployeeUpdate
) -> EmployeeOut:
    seller = _get_seller_or_404(db, current_user.company_id, employee_id)  # type: ignore[arg-type]
    seller, store_name = employee_service.update_seller(db, seller, current_user.company_id, data)  # type: ignore[arg-type]
    return _to_out(seller, store_name)


@router.post("/{employee_id}/activate", response_model=EmployeeOut, summary="Sotuvchini faollashtirish (CEO)")
def activate_employee(db: DbSession, current_user: RequireCEO, employee_id: int) -> EmployeeOut:
    seller = _get_seller_or_404(db, current_user.company_id, employee_id)  # type: ignore[arg-type]
    seller, store_name = employee_service.set_seller_active(db, seller, current_user.company_id, True)  # type: ignore[arg-type]
    return _to_out(seller, store_name)


@router.post("/{employee_id}/deactivate", response_model=EmployeeOut, summary="Sotuvchini nofaol qilish (CEO)")
def deactivate_employee(db: DbSession, current_user: RequireCEO, employee_id: int) -> EmployeeOut:
    seller = _get_seller_or_404(db, current_user.company_id, employee_id)  # type: ignore[arg-type]
    seller, store_name = employee_service.set_seller_active(db, seller, current_user.company_id, False)  # type: ignore[arg-type]
    return _to_out(seller, store_name)


@router.post(
    "/{employee_id}/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sotuvchi parolini tiklash (CEO)",
)
def reset_employee_password(
    db: DbSession, current_user: RequireCEO, employee_id: int, data: EmployeePasswordReset
) -> Response:
    seller = _get_seller_or_404(db, current_user.company_id, employee_id)  # type: ignore[arg-type]
    employee_service.reset_seller_password(db, seller, data.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
