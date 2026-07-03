"""Stock-in (Kirim) endpoints."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func

from app.auth.dependencies import CurrentUser, DbSession, ReqContext
from app.crud.stock_in import stock_in as stock_in_crud
from app.models.stock_in import StockIn
from app.permissions.dependencies import require_permission
from app.schemas.common import PaginatedResponse
from app.schemas.stock_in import StockInCreate, StockInOut
from app.services import stock_in_service
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/stock-in", tags=["Stock In (Kirim)"])


@router.post(
    "",
    response_model=StockInOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("stock_in.manage"))],
    summary="Kirim qilish (ombor avtomatik oshadi)",
)
def create_stock_in(
    db: DbSession, ctx: ReqContext, current_user: CurrentUser, data: StockInCreate
) -> StockIn:
    return stock_in_service.create_stock_in(
        db, data, user_id=current_user.id, ip_address=ctx.ip_address, user_agent=ctx.user_agent
    )


@router.get(
    "",
    response_model=PaginatedResponse[StockInOut],
    dependencies=[Depends(require_permission("stock_in.view"))],
    summary="Kirimlar ro'yxati",
)
def list_stock_in(
    db: DbSession,
    search: str | None = Query(default=None, description="Hujjat raqami"),
    supplier_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[StockInOut]:
    filters: list = []
    if supplier_id is not None:
        filters.append(StockIn.supplier_id == supplier_id)
    if date_from is not None:
        filters.append(func.date(StockIn.date) >= date_from)
    if date_to is not None:
        filters.append(func.date(StockIn.date) <= date_to)

    params = PageParams(page=page, page_size=page_size)
    items, total = stock_in_crud.list(
        db,
        page_params=params,
        search=search,
        search_fields=[StockIn.reference],
        filters=filters,
        order_by=StockIn.date.desc(),
    )
    return PaginatedResponse[StockInOut](items=items, meta=make_meta(total, params))


@router.get(
    "/{stock_in_id}",
    response_model=StockInOut,
    dependencies=[Depends(require_permission("stock_in.view"))],
    summary="Kirim hujjati (chop etish uchun ham)",
)
def get_stock_in(db: DbSession, stock_in_id: int) -> StockIn:
    return stock_in_crud.get_or_404(db, stock_in_id)
