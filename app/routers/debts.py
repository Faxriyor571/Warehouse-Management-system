"""Debt (Qarz) endpoints (API_SPECIFICATION.md §11).

Company/store scoped, same shape as Sales/Stock In, gated by
``Perm.DEBTS_MANAGE`` (view+manage combined — no split exists for Debts
today; granted to CEO, Cashier, and Accountant). A Cashier is confined to
their own store; CEO/Accountant see any store/company-wide and may filter by
``store_id``. The legacy single-tenant admin bypasses via ``is_superuser``
inside ``require_perm`` and operates in the NULL-company scope. Super Admin
has no access.

``POST /debts`` (a standalone debt not tied to a sale) is not part of the API
spec — Debts are only created automatically via Sales (SRS rule #7). It stays
on the untouched ``legacy_compat.RequireLegacyDebtManage`` (legacy admin only,
Option A), not migrated to ``require_perm``/extended to any new role.

Reminder endpoints (manual SMS send, reminder history) are not implemented:
they depend on a ``debt_reminders`` table not yet in the approved
DATABASE_DESIGN.md (see API_SPECIFICATION.md §16, gap #1).
"""
from __future__ import annotations

from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import DbSession, ReqContext
from app.auth.legacy_compat import RequireLegacyDebtManage
from app.auth.permissions import require_perm
from app.crud.debt import debt as debt_crud
from app.models.debt import Debt
from app.models.enums import DebtStatus
from app.models.user import User
from app.permissions.employee_matrix import Perm
from app.schemas.common import PaginatedResponse
from app.schemas.debt import (
    DebtCreate,
    DebtDetail,
    DebtDueDateUpdate,
    DebtOut,
    DebtPaymentCreate,
    DebtPaymentOut,
)
from app.services import debt_service
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PageParams, make_meta
from app.utils.scope import resolve_scope

router = APIRouter(prefix="/debts", tags=["Debts (Qarzlar)"])

RequireDebtActor = Annotated[User, Depends(require_perm(Perm.DEBTS_MANAGE))]


def _get_debt_or_404(db: DbSession, current_user: User, debt_id: int) -> Debt:
    company_id, store_filter = resolve_scope(current_user, None, db)
    obj = debt_crud.get_for_scope(db, debt_id, company_id, store_id=store_filter)
    if obj is None:
        raise NotFoundError(f"Qarz (id={debt_id}) topilmadi")
    return obj


@router.get("", response_model=PaginatedResponse[DebtOut], summary="Qarzlar ro'yxati")
def list_debts(
    db: DbSession,
    current_user: RequireDebtActor,
    store_id: int | None = Query(default=None, description="Faqat CEO uchun"),
    customer_id: int | None = Query(default=None),
    status_filter: DebtStatus | None = Query(default=None, alias="status"),
    only_open: bool = Query(default=False, description="Faqat qoldig'i borlar"),
    due_before: date_type | None = Query(default=None),
    due_after: date_type | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[DebtOut]:
    company_id, store_filter = resolve_scope(current_user, store_id, db)
    debt_service.refresh_overdue(db, company_id=company_id, store_id=store_filter)
    params = PageParams(page=page, page_size=page_size)
    items, total = debt_crud.list_for_scope(
        db,
        company_id,
        page_params=params,
        store_id=store_filter,
        customer_id=customer_id,
        status=status_filter,
        only_open=only_open,
        due_before=due_before,
        due_after=due_after,
    )
    return PaginatedResponse[DebtOut](items=items, meta=make_meta(total, params))


@router.post(
    "",
    response_model=DebtOut,
    status_code=status.HTTP_201_CREATED,
    summary="Qarz yaratish (faqat legacy admin)",
)
def create_debt(
    db: DbSession, ctx: ReqContext, current_user: RequireLegacyDebtManage, data: DebtCreate
) -> Debt:
    return debt_service.create_debt(
        db, data, user_id=current_user.id, ip_address=ctx.ip_address, user_agent=ctx.user_agent
    )


@router.get(
    "/{debt_id}",
    response_model=DebtDetail,
    summary="Qarz ma'lumoti (to'lovlar tarixi bilan)",
)
def get_debt(db: DbSession, current_user: RequireDebtActor, debt_id: int) -> Debt:
    return _get_debt_or_404(db, current_user, debt_id)


@router.post(
    "/{debt_id}/payments",
    response_model=DebtPaymentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Qarzga to'lov qilish",
)
def add_debt_payment(
    db: DbSession,
    ctx: ReqContext,
    current_user: RequireDebtActor,
    debt_id: int,
    data: DebtPaymentCreate,
):
    debt = _get_debt_or_404(db, current_user, debt_id)
    return debt_service.add_payment(
        db, debt, data, user_id=current_user.id, ip_address=ctx.ip_address, user_agent=ctx.user_agent
    )


@router.put(
    "/{debt_id}/due-date",
    response_model=DebtOut,
    summary="Qarz muddatini o'zgartirish",
)
def update_due_date(
    db: DbSession,
    ctx: ReqContext,
    current_user: RequireDebtActor,
    debt_id: int,
    data: DebtDueDateUpdate,
) -> Debt:
    debt = _get_debt_or_404(db, current_user, debt_id)
    return debt_service.update_due_date(
        db, debt, data, user_id=current_user.id, ip_address=ctx.ip_address, user_agent=ctx.user_agent
    )
