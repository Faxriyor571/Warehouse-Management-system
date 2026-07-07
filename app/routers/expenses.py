"""Expense endpoints (API_SPECIFICATION.md §12).

Company/store scoped, same shape as Stock In. Writes and reads are available
to CEO and Seller (a Seller is confined to their own store); the legacy
single-tenant admin is admitted transitionally and operates in the NULL-company
scope. Super Admin has no access. Immutable — no PUT/DELETE (§12 notes).
"""
from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Query, status

from app.auth.dependencies import DbSession, ReqContext
from app.auth.legacy_compat import RequireExpenseActor
from app.crud.expense import expense as expense_crud
from app.crud.store import store as store_crud
from app.models.enums import ExpenseType, UserRole
from app.models.expense import Expense
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.expense import ExpenseCreate, ExpenseOut
from app.services import expense_service
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/expenses", tags=["Expenses (Xarajatlar)"])


def _resolve_write_scope(
    current_user: User, body_store_id: int | None, db: DbSession
) -> tuple[int | None, int | None]:
    if current_user.role == UserRole.SELLER:
        return current_user.company_id, current_user.store_id
    if current_user.role == UserRole.CEO:
        if body_store_id is None:
            raise ValidationError("store_id majburiy (CEO uchun)")
        store = store_crud.get_for_company(db, body_store_id, current_user.company_id)
        if store is None:
            raise NotFoundError(f"Do'kon (id={body_store_id}) topilmadi")
        return current_user.company_id, body_store_id
    return None, None  # legacy single-tenant admin


def _resolve_read_scope(
    current_user: User, requested_store_id: int | None, db: DbSession
) -> tuple[int | None, int | None]:
    if current_user.role == UserRole.SELLER:
        return current_user.company_id, current_user.store_id
    if current_user.role == UserRole.CEO:
        if requested_store_id is not None:
            store = store_crud.get_for_company(db, requested_store_id, current_user.company_id)
            if store is None:
                raise NotFoundError(f"Do'kon (id={requested_store_id}) topilmadi")
        return current_user.company_id, requested_store_id
    return None, None  # legacy single-tenant admin


@router.post(
    "",
    response_model=ExpenseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Xarajat qo'shish",
)
def create_expense(
    db: DbSession, ctx: ReqContext, current_user: RequireExpenseActor, data: ExpenseCreate
) -> Expense:
    company_id, store_id = _resolve_write_scope(current_user, data.store_id, db)
    return expense_service.create_expense(
        db,
        data,
        company_id=company_id,
        store_id=store_id,
        user_id=current_user.id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )


@router.get("", response_model=PaginatedResponse[ExpenseOut], summary="Xarajatlar ro'yxati")
def list_expenses(
    db: DbSession,
    current_user: RequireExpenseActor,
    store_id: int | None = Query(default=None, description="Faqat CEO uchun"),
    expense_type: ExpenseType | None = Query(default=None),
    date_from: date_type | None = Query(default=None),
    date_to: date_type | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[ExpenseOut]:
    company_id, store_filter = _resolve_read_scope(current_user, store_id, db)
    params = PageParams(page=page, page_size=page_size)
    items, total = expense_crud.list_for_scope(
        db,
        company_id,
        page_params=params,
        store_id=store_filter,
        expense_type=expense_type,
        date_from=date_from,
        date_to=date_to,
    )
    return PaginatedResponse[ExpenseOut](items=items, meta=make_meta(total, params))


@router.get("/{expense_id}", response_model=ExpenseOut, summary="Xarajat ma'lumoti")
def get_expense(db: DbSession, current_user: RequireExpenseActor, expense_id: int) -> Expense:
    company_id, store_filter = _resolve_read_scope(current_user, None, db)
    obj = expense_crud.get_for_scope(db, expense_id, company_id, store_id=store_filter)
    if obj is None:
        raise NotFoundError(f"Xarajat (id={expense_id}) topilmadi")
    return obj
