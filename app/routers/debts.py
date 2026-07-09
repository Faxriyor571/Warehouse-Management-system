"""Debt (Qarz) endpoints (API_SPECIFICATION.md §11).

Company/store scoped, same shape as Sales/Stock In. Seller is confined to
their own store; CEO sees any store/company-wide and may filter by
``store_id``. The legacy single-tenant admin is admitted transitionally and
operates in the NULL-company scope. Super Admin has no access.

``POST /debts`` (a standalone debt not tied to a sale) is not part of the API
spec — Debts are only created automatically via Sales (SRS rule #7). It is
kept working for the legacy admin only (Option A), not extended to CEO/Seller.

Reminder endpoints (manual SMS send, reminder history) are not implemented:
they depend on a ``debt_reminders`` table not yet in the approved
DATABASE_DESIGN.md (see API_SPECIFICATION.md §16, gap #1).
"""
from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Query, status

from app.auth.dependencies import DbSession, ReqContext
from app.auth.legacy_compat import RequireDebtActor, RequireLegacyDebtManage
from app.crud.debt import debt as debt_crud
from app.crud.store import store as store_crud
from app.models.debt import Debt
from app.models.enums import DebtStatus, UserRole
from app.models.user import User
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

router = APIRouter(prefix="/debts", tags=["Debts (Qarzlar)"])


def _resolve_scope(
    current_user: User, requested_store_id: int | None, db: DbSession
) -> tuple[int | None, int | None]:
    """Resolve ``(company_id, store_filter)``. ``store_id`` filtering is
    CEO-only (spec); a Seller is always confined to their own store."""
    if current_user.role == UserRole.SELLER:
        return current_user.company_id, current_user.store_id
    if current_user.role == UserRole.CEO:
        if requested_store_id is not None:
            store = store_crud.get_for_company(db, requested_store_id, current_user.company_id)
            if store is None:
                raise NotFoundError(f"Do'kon (id={requested_store_id}) topilmadi")
        return current_user.company_id, requested_store_id
    return None, None  # legacy single-tenant admin


def _get_debt_or_404(db: DbSession, current_user: User, debt_id: int) -> Debt:
    company_id, store_filter = _resolve_scope(current_user, None, db)
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
    company_id, store_filter = _resolve_scope(current_user, store_id, db)
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
