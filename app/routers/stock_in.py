"""Stock-in (Kirim) endpoints (API_SPECIFICATION.md §8).

Company/store scoped. Reading is available to whoever has ``Perm.STOCK_IN_VIEW``
(CEO, Warehouse Employee); recording a stock-in requires ``Perm.STOCK_IN_MANAGE``
(Warehouse Employee only — the Company Owner can see this data but does not
receive inventory themselves, per the ERP role redesign). The legacy
single-tenant admin bypasses via ``is_superuser`` inside ``require_perm`` and
operates in the NULL-company scope. ``store_id`` is never trusted from a
Seller/Warehouse-Employee's request — it is taken from the token.
"""
from __future__ import annotations

from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import DbSession, ReqContext
from app.auth.permissions import require_perm
from app.crud.stock_in import stock_in as stock_in_crud
from app.models.stock_in import StockIn
from app.models.user import User
from app.permissions.employee_matrix import Perm
from app.schemas.common import PaginatedResponse
from app.schemas.stock_in import StockInCreate, StockInOut
from app.services import stock_in_service
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PageParams, make_meta
from app.utils.scope import resolve_scope

router = APIRouter(prefix="/stock-in", tags=["Stock In (Kirim)"])

RequireStockInRead = Annotated[User, Depends(require_perm(Perm.STOCK_IN_VIEW))]
RequireStockInWrite = Annotated[User, Depends(require_perm(Perm.STOCK_IN_MANAGE))]


@router.post(
    "",
    response_model=StockInOut,
    status_code=status.HTTP_201_CREATED,
    summary="Kirim qilish (ombor avtomatik oshadi)",
)
def create_stock_in(
    db: DbSession, ctx: ReqContext, current_user: RequireStockInWrite, data: StockInCreate
) -> StockIn:
    company_id, store_id = resolve_scope(current_user, data.store_id, db, require_store_id=True)
    return stock_in_service.create_stock_in(
        db,
        data,
        company_id=company_id,
        store_id=store_id,
        user_id=current_user.id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )


@router.get("", response_model=PaginatedResponse[StockInOut], summary="Kirimlar ro'yxati")
def list_stock_in(
    db: DbSession,
    current_user: RequireStockInRead,
    store_id: int | None = Query(default=None),
    supplier_id: int | None = Query(default=None),
    search: str | None = Query(default=None, description="Hujjat raqami"),
    date_from: date_type | None = Query(default=None),
    date_to: date_type | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[StockInOut]:
    company_id, store_filter = resolve_scope(current_user, store_id, db)
    params = PageParams(page=page, page_size=page_size)
    items, total = stock_in_crud.list_for_scope(
        db,
        company_id,
        page_params=params,
        store_id=store_filter,
        supplier_id=supplier_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return PaginatedResponse[StockInOut](items=items, meta=make_meta(total, params))


@router.get(
    "/{stock_in_id}",
    response_model=StockInOut,
    summary="Kirim hujjati (chop etish uchun ham)",
)
def get_stock_in(db: DbSession, current_user: RequireStockInRead, stock_in_id: int) -> StockIn:
    company_id, store_filter = resolve_scope(current_user, None, db)
    obj = stock_in_crud.get_for_scope(db, stock_in_id, company_id, store_id=store_filter)
    if obj is None:
        raise NotFoundError(f"Kirim hujjati (id={stock_in_id}) topilmadi")
    return obj
