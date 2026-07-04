"""Stock-out (Chiqim / Sale) endpoints."""
from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func

from app.auth.dependencies import CurrentUser, DbSession, ReqContext
from app.crud.stock_out import stock_out as stock_out_crud
from app.models.enums import PaymentStatus
from app.models.stock_out import StockOut
from app.permissions.dependencies import require_permission
from app.schemas.common import PaginatedResponse
from app.schemas.stock_out import StockOutCreate, StockOutOut
from app.services import stock_out_service
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/stock-out", tags=["Stock Out (Chiqim)"])


@router.post(
    "",
    response_model=StockOutOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("stock_out.manage"))],
    summary="Chiqim / savdo qilish (ombor kamayadi, qarz avtomatik)",
)
def create_stock_out(
    db: DbSession, ctx: ReqContext, current_user: CurrentUser, data: StockOutCreate
) -> StockOut:
    return stock_out_service.create_stock_out(
        db, data, user_id=current_user.id, ip_address=ctx.ip_address, user_agent=ctx.user_agent
    )


@router.get(
    "",
    response_model=PaginatedResponse[StockOutOut],
    dependencies=[Depends(require_permission("stock_out.view"))],
    summary="Chiqimlar ro'yxati",
)
def list_stock_out(
    db: DbSession,
    search: str | None = Query(default=None, description="Hujjat raqami"),
    customer_id: int | None = Query(default=None),
    payment_status: PaymentStatus | None = Query(default=None),
    date_from: date_type | None = Query(default=None),
    date_to: date_type | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[StockOutOut]:
    filters: list = []
    if customer_id is not None:
        filters.append(StockOut.customer_id == customer_id)
    if payment_status is not None:
        filters.append(StockOut.payment_status == payment_status)
    if date_from is not None:
        filters.append(func.date(StockOut.date) >= date_from)
    if date_to is not None:
        filters.append(func.date(StockOut.date) <= date_to)

    params = PageParams(page=page, page_size=page_size)
    items, total = stock_out_crud.list(
        db,
        page_params=params,
        search=search,
        search_fields=[StockOut.reference],
        filters=filters,
        order_by=StockOut.date.desc(),
    )
    return PaginatedResponse[StockOutOut](items=items, meta=make_meta(total, params))


@router.get(
    "/{stock_out_id}",
    response_model=StockOutOut,
    dependencies=[Depends(require_permission("stock_out.view"))],
    summary="Chiqim hujjati (chop etish uchun ham)",
)
def get_stock_out(db: DbSession, stock_out_id: int) -> StockOut:
    return stock_out_crud.get_or_404(db, stock_out_id)
