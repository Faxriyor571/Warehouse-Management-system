"""Stock-in (Kirim) endpoints (API_SPECIFICATION.md §8).

Company/store scoped. Writes and reads are available to CEO and Seller (a
Seller is confined to their own store); the legacy single-tenant admin is
admitted transitionally and operates in the NULL-company scope. Super Admin has
no access. ``store_id`` is never trusted from a Seller's request — it is taken
from the token.
"""
from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Query, status

from app.auth.dependencies import DbSession, ReqContext
from app.auth.legacy_compat import RequireStockInActor
from app.crud.stock_in import stock_in as stock_in_crud
from app.crud.store import store as store_crud
from app.models.enums import UserRole
from app.models.stock_in import StockIn
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.stock_in import StockInCreate, StockInOut
from app.services import stock_in_service
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/stock-in", tags=["Stock In (Kirim)"])


def _resolve_write_scope(
    current_user: User, body_store_id: int | None, db: DbSession
) -> tuple[int | None, int | None]:
    """Resolve ``(company_id, store_id)`` for a new stock-in.

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
    """Resolve ``(company_id, store_filter)`` for reading stock-in documents."""
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
    response_model=StockInOut,
    status_code=status.HTTP_201_CREATED,
    summary="Kirim qilish (ombor avtomatik oshadi)",
)
def create_stock_in(
    db: DbSession, ctx: ReqContext, current_user: RequireStockInActor, data: StockInCreate
) -> StockIn:
    company_id, store_id = _resolve_write_scope(current_user, data.store_id, db)
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
    current_user: RequireStockInActor,
    store_id: int | None = Query(default=None),
    supplier_id: int | None = Query(default=None),
    search: str | None = Query(default=None, description="Hujjat raqami"),
    date_from: date_type | None = Query(default=None),
    date_to: date_type | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[StockInOut]:
    company_id, store_filter = _resolve_read_scope(current_user, store_id, db)
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
def get_stock_in(db: DbSession, current_user: RequireStockInActor, stock_in_id: int) -> StockIn:
    company_id, store_filter = _resolve_read_scope(current_user, None, db)
    obj = stock_in_crud.get_for_scope(db, stock_in_id, company_id, store_id=store_filter)
    if obj is None:
        raise NotFoundError(f"Kirim hujjati (id={stock_in_id}) topilmadi")
    return obj
