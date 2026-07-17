"""Store endpoints (API_SPECIFICATION.md §3).

Writes (create/update/deactivate) are CEO-only; reads (list/detail) are
available to CEO and Seller, scoped and shaped per role. Super Admin has no
access to stores (SRS §3.1 — stores are company business data).
"""
from __future__ import annotations

from fastapi import APIRouter, status

from app.auth.dependencies import DbSession, RequireCEO, RequireCEOOrSeller
from app.crud.store import store as store_crud
from app.models.enums import UserRole
from app.models.store import Store
from app.schemas.store import StoreCreate, StoreNameOut, StoreOut, StoreUpdate
from app.services import store_service
from app.utils.exceptions import NotFoundError, PermissionDeniedError

router = APIRouter(prefix="/stores", tags=["Stores"])


@router.post(
    "",
    response_model=StoreOut,
    status_code=status.HTTP_201_CREATED,
    summary="Do'kon yaratish (CEO)",
)
def create_store(db: DbSession, current_user: RequireCEO, data: StoreCreate) -> Store:
    return store_service.create_store(db, current_user.company_id, data)  # type: ignore[arg-type]


@router.get(
    "",
    response_model=None,
    summary="Do'konlar ro'yxati (CEO: to'liq, Sotuvchi: faqat nom)",
)
def list_stores(
    db: DbSession, current_user: RequireCEOOrSeller
) -> list[StoreOut] | list[StoreNameOut]:
    """List the company's stores.

    Explicit, deterministic per-role serialization (no Union response model):
    a CEO receives the full ``StoreOut`` shape; a Seller receives the reduced
    ``StoreNameOut`` shape (id + name only).
    """
    stores = store_crud.list_for_company(db, current_user.company_id)  # type: ignore[arg-type]
    if current_user.role == UserRole.CEO:
        return [StoreOut.model_validate(s) for s in stores]
    return [StoreNameOut.model_validate(s) for s in stores]


@router.get("/{store_id}", response_model=StoreOut, summary="Do'kon ma'lumoti")
def get_store(db: DbSession, current_user: RequireCEOOrSeller, store_id: int) -> Store:
    # A Seller may only access their own assigned store (API_SPECIFICATION.md §3).
    if current_user.role == UserRole.SELLER and current_user.store_id != store_id:
        raise PermissionDeniedError("Sotuvchi faqat o'z do'konini ko'ra oladi")

    store = store_crud.get_for_company(db, store_id, current_user.company_id)  # type: ignore[arg-type]
    if store is None:
        raise NotFoundError(f"Do'kon (id={store_id}) topilmadi")
    return store


@router.put("/{store_id}", response_model=StoreOut, summary="Do'konni yangilash (CEO)")
def update_store(
    db: DbSession, current_user: RequireCEO, store_id: int, data: StoreUpdate
) -> Store:
    store = store_crud.get_for_company(db, store_id, current_user.company_id)  # type: ignore[arg-type]
    if store is None:
        raise NotFoundError(f"Do'kon (id={store_id}) topilmadi")
    return store_service.update_store(db, store, data)


@router.post(
    "/{store_id}/deactivate",
    response_model=StoreOut,
    summary="Do'konni o'chirish / nofaol qilish (CEO)",
)
def deactivate_store(db: DbSession, current_user: RequireCEO, store_id: int) -> Store:
    store = store_crud.get_for_company(db, store_id, current_user.company_id)  # type: ignore[arg-type]
    if store is None:
        raise NotFoundError(f"Do'kon (id={store_id}) topilmadi")
    return store_service.deactivate_store(db, store)
