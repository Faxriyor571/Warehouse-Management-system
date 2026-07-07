"""Product catalogue endpoints (API_SPECIFICATION.md §6).

Company-scoped: writes are CEO-only, reads are CEO/Seller, Super Admin has no
access. Authorization goes through the transitional catalogue dependencies in
``app/auth/legacy_compat.py``. Scoping is uniform via ``current_user.company_id``.

Per §6 this catalogue module deliberately does not define barcode-lookup or
image-upload endpoints (SRS Future Roadmap), and per-store on-hand quantity is
an Inventory-phase concern.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.auth.dependencies import DbSession
from app.auth.legacy_compat import RequireCatalogueManage, RequireCatalogueRead
from app.crud.product import product as product_crud
from app.models.product import Product
from app.schemas.common import Message, PaginatedResponse
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.services import product_service
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "",
    response_model=PaginatedResponse[ProductOut],
    summary="Mahsulotlar ro'yxati (qidiruv, filtr, sahifalash)",
)
def list_products(
    db: DbSession,
    current_user: RequireCatalogueRead,
    search: str | None = Query(default=None, description="Nomi / SKU / shtrix kod"),
    category_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[ProductOut]:
    params = PageParams(page=page, page_size=page_size)
    items, total = product_crud.list_for_company(
        db, current_user.company_id, page_params=params, search=search, category_id=category_id
    )
    return PaginatedResponse[ProductOut](items=items, meta=make_meta(total, params))


@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    summary="Mahsulot qo'shish",
)
def create_product(
    db: DbSession, current_user: RequireCatalogueManage, data: ProductCreate
) -> Product:
    return product_service.create_product(db, current_user.company_id, data)


@router.get("/{product_id}", response_model=ProductOut, summary="Mahsulot ma'lumoti")
def get_product(db: DbSession, current_user: RequireCatalogueRead, product_id: int) -> Product:
    obj = product_crud.get_for_company(db, product_id, current_user.company_id)
    if obj is None:
        raise NotFoundError(f"Mahsulot (id={product_id}) topilmadi")
    return obj


@router.put("/{product_id}", response_model=ProductOut, summary="Mahsulotni yangilash")
def update_product(
    db: DbSession, current_user: RequireCatalogueManage, product_id: int, data: ProductUpdate
) -> Product:
    obj = product_crud.get_for_company(db, product_id, current_user.company_id)
    if obj is None:
        raise NotFoundError(f"Mahsulot (id={product_id}) topilmadi")
    return product_service.update_product(db, obj, current_user.company_id, data)


@router.delete("/{product_id}", response_model=Message, summary="Mahsulotni o'chirish")
def delete_product(
    db: DbSession, current_user: RequireCatalogueManage, product_id: int
) -> Message:
    obj = product_crud.get_for_company(db, product_id, current_user.company_id)
    if obj is None:
        raise NotFoundError(f"Mahsulot (id={product_id}) topilmadi")
    product_service.delete_product(db, obj)
    return Message(detail="Mahsulot o'chirildi")
