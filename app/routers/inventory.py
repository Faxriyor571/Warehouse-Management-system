"""Inventory endpoints (API_SPECIFICATION.md §7). Read-only.

Per-store on-hand stock, the cross-store quantity view, and the movement
ledger. ``store_stock``/``stock_movements`` are mutated only as a side effect
of Stock In / Sales / Sale Returns (via ``inventory_service``); there are no
write endpoints here.

Access: CEO and Seller. Super Admin (and the legacy admin) have no access.
A Seller is confined to their own store for store-stock and movements, with the
single explicit exception of the cross-store quantity view (SRS rule #4).
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query, status

from app.auth.dependencies import DbSession, RequireCEOOrSeller
from app.crud.product import product as product_crud
from app.crud.stock_movement import stock_movement as stock_movement_crud
from app.crud.store import store as store_crud
from app.crud.store_stock import store_stock as store_stock_crud
from app.models.enums import MovementType, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.inventory import CrossStoreRow, StockMovementOut, StoreStockRow
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/inventory", tags=["Inventory"])


def _resolve_store_scope(current_user, requested_store_id: int | None, db) -> int | None:
    """Return the store id to scope by, or None for a company-wide view.

    A Seller is always confined to their own store (any requested store_id is
    ignored). A CEO may target any store in their company, or omit it for the
    company-wide view; a foreign store id yields 404.
    """
    if current_user.role == UserRole.SELLER:
        return current_user.store_id
    if requested_store_id is None:
        return None
    store = store_crud.get_for_company(db, requested_store_id, current_user.company_id)
    if store is None:
        raise NotFoundError(f"Do'kon (id={requested_store_id}) topilmadi")
    return requested_store_id


@router.get(
    "/store-stock",
    response_model=PaginatedResponse[StoreStockRow],
    summary="Do'kon zaxirasi (CEO: do'kon yoki kompaniya bo'yicha; Sotuvchi: o'z do'koni)",
)
def store_stock(
    db: DbSession,
    current_user: RequireCEOOrSeller,
    store_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[StoreStockRow]:
    params = PageParams(page=page, page_size=page_size)
    resolved = _resolve_store_scope(current_user, store_id, db)

    if resolved is None:  # CEO company-wide totals
        rows, total = store_stock_crud.list_company_wide(
            db, current_user.company_id, page_params=params, search=search
        )
    else:
        rows, total = store_stock_crud.list_for_store(
            db, resolved, page_params=params, search=search
        )

    items = [
        StoreStockRow(
            product_id=r.product_id,
            product_name=r.product_name,
            sku=r.sku,
            quantity=r.quantity,
        )
        for r in rows
    ]
    return PaginatedResponse[StoreStockRow](items=items, meta=make_meta(total, params))


@router.get(
    "/store-stock/cross-store",
    response_model=list[CrossStoreRow],
    summary="Mahsulot zaxirasi barcha do'konlar bo'yicha (faqat miqdor)",
)
def cross_store(
    db: DbSession,
    current_user: RequireCEOOrSeller,
    product_id: int = Query(...),
) -> list[CrossStoreRow]:
    # The product must belong to the caller's company (404 otherwise).
    if product_crud.get_for_company(db, product_id, current_user.company_id) is None:
        raise NotFoundError(f"Mahsulot (id={product_id}) topilmadi")

    rows = store_stock_crud.cross_store_for_product(db, current_user.company_id, product_id)
    return [
        CrossStoreRow(store_id=r.store_id, store_name=r.store_name, quantity=r.quantity)
        for r in rows
    ]


@router.get(
    "/movements",
    response_model=PaginatedResponse[StockMovementOut],
    summary="Zaxira harakatlari jurnali",
)
def movements(
    db: DbSession,
    current_user: RequireCEOOrSeller,
    store_id: int | None = Query(default=None),
    product_id: int | None = Query(default=None),
    movement_type: MovementType | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[StockMovementOut]:
    params = PageParams(page=page, page_size=page_size)
    resolved = _resolve_store_scope(current_user, store_id, db)

    rows, total = stock_movement_crud.list(
        db,
        current_user.company_id,
        page_params=params,
        store_id=resolved,
        product_id=product_id,
        movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
    )
    items = [
        StockMovementOut(
            id=mv.id,
            store_id=mv.store_id,
            product_id=mv.product_id,
            movement_type=mv.movement_type,
            quantity_delta=mv.quantity_delta,
            reference_type=mv.reference_type,
            reference_id=mv.reference_id,
            created_by=created_by,
            created_at=mv.created_at,
        )
        for mv, created_by in rows
    ]
    return PaginatedResponse[StockMovementOut](items=items, meta=make_meta(total, params))
