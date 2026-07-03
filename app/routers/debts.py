"""Debt (Qarz) endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import CurrentUser, DbSession, ReqContext
from app.crud.debt import debt as debt_crud
from app.models.debt import Debt
from app.models.enums import DebtStatus
from app.permissions.dependencies import require_permission
from app.schemas.common import PaginatedResponse
from app.schemas.debt import (
    DebtCreate,
    DebtDetail,
    DebtOut,
    DebtPaymentCreate,
    DebtPaymentOut,
)
from app.services import debt_service
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/debts", tags=["Debts (Qarzlar)"])


@router.get(
    "",
    response_model=PaginatedResponse[DebtOut],
    dependencies=[Depends(require_permission("debt.view"))],
    summary="Qarzlar ro'yxati",
)
def list_debts(
    db: DbSession,
    customer_id: int | None = Query(default=None),
    status_filter: DebtStatus | None = Query(default=None, alias="status"),
    only_open: bool = Query(default=False, description="Faqat qoldig'i borlar"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[DebtOut]:
    filters: list = []
    if customer_id is not None:
        filters.append(Debt.customer_id == customer_id)
    if status_filter is not None:
        filters.append(Debt.status == status_filter)
    if only_open:
        filters.append(Debt.remaining_amount > 0)

    params = PageParams(page=page, page_size=page_size)
    items, total = debt_crud.list(
        db, page_params=params, filters=filters, order_by=Debt.due_date.asc().nulls_last()
    )
    return PaginatedResponse[DebtOut](items=items, meta=make_meta(total, params))


@router.post(
    "",
    response_model=DebtOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("debt.manage"))],
    summary="Qarz yaratish",
)
def create_debt(
    db: DbSession, ctx: ReqContext, current_user: CurrentUser, data: DebtCreate
) -> Debt:
    return debt_service.create_debt(
        db, data, user_id=current_user.id, ip_address=ctx.ip_address, user_agent=ctx.user_agent
    )


@router.get(
    "/{debt_id}",
    response_model=DebtDetail,
    dependencies=[Depends(require_permission("debt.view"))],
    summary="Qarz ma'lumoti (to'lovlar tarixi bilan)",
)
def get_debt(db: DbSession, debt_id: int) -> Debt:
    return debt_crud.get_or_404(db, debt_id)


@router.post(
    "/{debt_id}/payments",
    response_model=DebtPaymentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("debt.manage"))],
    summary="Qarzga to'lov qilish",
)
def add_debt_payment(
    db: DbSession,
    ctx: ReqContext,
    current_user: CurrentUser,
    debt_id: int,
    data: DebtPaymentCreate,
):
    debt = debt_crud.get_or_404(db, debt_id)
    return debt_service.add_payment(
        db, debt, data, user_id=current_user.id, ip_address=ctx.ip_address, user_agent=ctx.user_agent
    )
