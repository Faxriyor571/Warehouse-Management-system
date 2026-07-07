"""Sales (Chiqim / Sale) endpoints (API_SPECIFICATION.md §9).

Company/store scoped, same shape as Stock In. Writes and reads are available
to CEO and Seller (a Seller is confined to their own store); the legacy
single-tenant admin is admitted transitionally and operates in the NULL-company
scope. ``store_id`` is never trusted from a Seller's request — it is taken
from the token.

Mounted twice in ``app/routers/api.py`` — at ``/stock-out`` (legacy, kept for
``test_stock_flow.py`` and any existing integrations) and at ``/sales`` (the
name used by API_SPECIFICATION.md §9) — both prefixes serve the same router,
so there is exactly one implementation.
"""
from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Query, status

from app.auth.dependencies import DbSession, ReqContext
from app.auth.legacy_compat import RequireSalesActor
from app.crud.sales_return import sales_return as sales_return_crud
from app.crud.stock_out import stock_out as stock_out_crud
from app.crud.store import store as store_crud
from app.models.enums import PaymentStatus, UserRole
from app.models.sales_return import SalesReturn
from app.models.stock_out import StockOut
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.sales_return import SalesReturnCreate, SalesReturnOut
from app.schemas.stock_out import StockOutCreate, StockOutOut
from app.services import stock_out_service
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.pagination import PageParams, make_meta

router = APIRouter(tags=["Sales (Savdo)"])


def _resolve_write_scope(
    current_user: User, body_store_id: int | None, db: DbSession
) -> tuple[int | None, int | None]:
    """Resolve ``(company_id, store_id)`` for a new sale/return.

    Seller → own store (body ``store_id`` ignored). CEO → the body ``store_id``
    (required, validated to belong to the company). Legacy admin → ``(None,
    None)``, the transitional product.quantity path.
    """
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
    """Resolve ``(company_id, store_filter)`` for reading sale documents."""
    if current_user.role == UserRole.SELLER:
        return current_user.company_id, current_user.store_id
    if current_user.role == UserRole.CEO:
        if requested_store_id is not None:
            store = store_crud.get_for_company(db, requested_store_id, current_user.company_id)
            if store is None:
                raise NotFoundError(f"Do'kon (id={requested_store_id}) topilmadi")
        return current_user.company_id, requested_store_id
    return None, None  # legacy single-tenant admin


def _get_sale_or_404(
    db: DbSession, current_user: User, stock_out_id: int
) -> tuple[StockOut, int | None, int | None]:
    company_id, store_filter = _resolve_read_scope(current_user, None, db)
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
    db: DbSession, ctx: ReqContext, current_user: RequireSalesActor, data: StockOutCreate
) -> StockOut:
    company_id, store_id = _resolve_write_scope(current_user, data.store_id, db)
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
    current_user: RequireSalesActor,
    store_id: int | None = Query(default=None),
    customer_id: int | None = Query(default=None),
    payment_status: PaymentStatus | None = Query(default=None),
    search: str | None = Query(default=None, description="Hujjat raqami"),
    date_from: date_type | None = Query(default=None),
    date_to: date_type | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[StockOutOut]:
    company_id, store_filter = _resolve_read_scope(current_user, store_id, db)
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
def get_stock_out(db: DbSession, current_user: RequireSalesActor, stock_out_id: int) -> StockOut:
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
    current_user: RequireSalesActor,
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
    db: DbSession, current_user: RequireSalesActor, stock_out_id: int
) -> list[SalesReturn]:
    sale, _, _ = _get_sale_or_404(db, current_user, stock_out_id)
    return list(sales_return_crud.list_for_sale(db, sale.id))
