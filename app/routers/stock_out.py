"""Sales (Chiqim / Sale) endpoints (API_SPECIFICATION.md §9).

Company/store scoped, same shape as Stock In. Reading requires
``Perm.SALES_VIEW`` (CEO, Cashier); recording a sale/return requires
``Perm.SALES_MANAGE`` (Cashier only — the Company Owner can see this data but
does not sell products themselves, per the ERP role redesign). The legacy
single-tenant admin bypasses via ``is_superuser`` inside ``require_perm`` and
operates in the NULL-company scope. ``store_id`` is never trusted from a
Seller's request — it is taken from the token.

Mounted twice in ``app/routers/api.py`` — at ``/stock-out`` (legacy, kept for
``test_stock_flow.py`` and any existing integrations) and at ``/sales`` (the
name used by API_SPECIFICATION.md §9) — both prefixes serve the same router,
so there is exactly one implementation.
"""
from __future__ import annotations

from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.auth.dependencies import DbSession, ReqContext
from app.auth.permissions import require_perm
from app.crud.sales_return import sales_return as sales_return_crud
from app.crud.stock_out import stock_out as stock_out_crud
from app.models.enums import PaymentStatus
from app.models.sales_return import SalesReturn
from app.models.stock_out import StockOut
from app.models.user import User
from app.permissions.employee_matrix import Perm
from app.schemas.common import PaginatedResponse
from app.schemas.sales_return import SalesReturnCreate, SalesReturnOut
from app.schemas.stock_out import StockOutCreate, StockOutOut
from app.services import stock_out_service
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PageParams, make_meta
from app.utils.scope import resolve_scope

router = APIRouter(tags=["Sales (Savdo)"])

RequireSalesRead = Annotated[User, Depends(require_perm(Perm.SALES_VIEW))]
RequireSalesWrite = Annotated[User, Depends(require_perm(Perm.SALES_MANAGE))]


def _get_sale_or_404(
    db: DbSession, current_user: User, stock_out_id: int
) -> tuple[StockOut, int | None, int | None]:
    company_id, store_filter = resolve_scope(current_user, None, db)
    obj = stock_out_crud.get_for_scope(db, stock_out_id, company_id, store_id=store_filter)
    if obj is None:
        raise NotFoundError(f"Chiqim hujjati (id={stock_out_id}) topilmadi")
    return obj, company_id, store_filter


@router.post(
    "",
    response_model=StockOutOut,
    status_code=status.HTTP_201_CREATED,
    summary="Chiqim / savdo qilish (ombor kamayadi, qarz avtomatik)",
)
def create_stock_out(
    db: DbSession, ctx: ReqContext, current_user: RequireSalesWrite, data: StockOutCreate
) -> StockOut:
    company_id, store_id = resolve_scope(current_user, data.store_id, db, require_store_id=True)
    return stock_out_service.create_stock_out(
        db,
        data,
        company_id=company_id,
        store_id=store_id,
        user_id=current_user.id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )


@router.get("", response_model=PaginatedResponse[StockOutOut], summary="Chiqimlar ro'yxati")
def list_stock_out(
    db: DbSession,
    current_user: RequireSalesRead,
    store_id: int | None = Query(default=None),
    customer_id: int | None = Query(default=None),
    payment_status: PaymentStatus | None = Query(default=None),
    search: str | None = Query(default=None, description="Hujjat raqami"),
    date_from: date_type | None = Query(default=None),
    date_to: date_type | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[StockOutOut]:
    company_id, store_filter = resolve_scope(current_user, store_id, db)
    params = PageParams(page=page, page_size=page_size)
    items, total = stock_out_crud.list_for_scope(
        db,
        company_id,
        page_params=params,
        store_id=store_filter,
        customer_id=customer_id,
        payment_status=payment_status,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return PaginatedResponse[StockOutOut](items=items, meta=make_meta(total, params))


@router.get(
    "/{stock_out_id}",
    response_model=StockOutOut,
    summary="Chiqim hujjati (chop etish uchun ham)",
)
def get_stock_out(db: DbSession, current_user: RequireSalesRead, stock_out_id: int) -> StockOut:
    obj, _, _ = _get_sale_or_404(db, current_user, stock_out_id)
    return obj


@router.post(
    "/{stock_out_id}/returns",
    response_model=SalesReturnOut,
    status_code=status.HTTP_201_CREATED,
    summary="Savdoni qaytarish (ombor tiklanadi, qarz kamayadi)",
)
def create_sales_return(
    db: DbSession,
    ctx: ReqContext,
    current_user: RequireSalesWrite,
    stock_out_id: int,
    data: SalesReturnCreate,
) -> SalesReturn:
    sale, company_id, store_filter = _get_sale_or_404(db, current_user, stock_out_id)
    return stock_out_service.create_sales_return(
        db,
        sale,
        data,
        company_id=company_id,
        store_id=sale.store_id,
        user_id=current_user.id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )


@router.get(
    "/{stock_out_id}/returns",
    response_model=list[SalesReturnOut],
    summary="Savdo bo'yicha qaytarishlar ro'yxati",
)
def list_sales_returns(
    db: DbSession, current_user: RequireSalesRead, stock_out_id: int
) -> list[SalesReturn]:
    sale, _, _ = _get_sale_or_404(db, current_user, stock_out_id)
    return list(sales_return_crud.list_for_sale(db, sale.id))
