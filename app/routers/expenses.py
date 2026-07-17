"""Expense endpoints (API_SPECIFICATION.md §12).

Company/store scoped, same shape as Stock In, gated by ``Perm.EXPENSES_MANAGE``
(view+manage combined — no split exists for Expenses today; granted to CEO
and Accountant. A Cashier/Warehouse Employee has no access, matching the ERP
role redesign). The legacy single-tenant admin bypasses via ``is_superuser``
inside ``require_perm`` and operates in the NULL-company scope. Super Admin
has no access. Immutable — no PUT/DELETE (§12 notes).
"""
from __future__ import annotations

from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import DbSession, ReqContext
from app.auth.permissions import require_perm
from app.crud.expense import expense as expense_crud
from app.models.enums import ExpenseType
from app.models.expense import Expense
from app.models.user import User
from app.permissions.employee_matrix import Perm
from app.schemas.common import PaginatedResponse
from app.schemas.expense import ExpenseCreate, ExpenseOut
from app.services import expense_service
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PageParams, make_meta
from app.utils.scope import resolve_scope

router = APIRouter(prefix="/expenses", tags=["Expenses (Xarajatlar)"])

RequireExpenseActor = Annotated[User, Depends(require_perm(Perm.EXPENSES_MANAGE))]


@router.post(
    "",
    response_model=ExpenseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Xarajat qo'shish",
)
def create_expense(
    db: DbSession, ctx: ReqContext, current_user: RequireExpenseActor, data: ExpenseCreate
) -> Expense:
    company_id, store_id = resolve_scope(current_user, data.store_id, db, require_store_id=True)
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
    company_id, store_filter = resolve_scope(current_user, store_id, db)
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
    company_id, store_filter = resolve_scope(current_user, None, db)
    obj = expense_crud.get_for_scope(db, expense_id, company_id, store_id=store_filter)
    if obj is None:
        raise NotFoundError(f"Xarajat (id={expense_id}) topilmadi")
    return obj
