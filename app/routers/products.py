"""Product CRUD endpoints with search, filtering, barcode lookup and image upload."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.auth.dependencies import CurrentUser, DbSession, ReqContext
from app.crud.product import product as product_crud
from app.models.enums import AuditAction
from app.models.product import Product
from app.permissions.dependencies import require_permission
from app.schemas.common import Message, PaginatedResponse
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.services import audit_service, product_service
from app.utils.files import save_image
from app.utils.pagination import PageParams, make_meta

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "",
    response_model=PaginatedResponse[ProductOut],
    dependencies=[Depends(require_permission("product.view"))],
    summary="Mahsulotlar ro'yxati (qidiruv, filtr, sahifalash)",
)
def list_products(
    db: DbSession,
    search: str | None = Query(default=None, description="Nomi / SKU / shtrix kod"),
    category_id: int | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    low_stock: bool = Query(default=False, description="Faqat kam qolganlar"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[ProductOut]:
    filters: list = []
    if category_id is not None:
        filters.append(Product.category_id == category_id)
    if is_active is not None:
        filters.append(Product.is_active.is_(is_active))
    if low_stock:
        filters.append(Product.quantity <= Product.min_quantity)

    params = PageParams(page=page, page_size=page_size)
    items, total = product_crud.list(
        db,
        page_params=params,
        search=search,
        search_fields=[Product.name, Product.sku, Product.barcode],
        filters=filters,
        order_by=Product.name.asc(),
    )
    return PaginatedResponse[ProductOut](items=items, meta=make_meta(total, params))


@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("product.manage"))],
    summary="Mahsulot qo'shish",
)
def create_product(
    db: DbSession, ctx: ReqContext, current_user: CurrentUser, data: ProductCreate
) -> Product:
    return product_service.create_product(
        db, data, user_id=current_user.id, ip_address=ctx.ip_address, user_agent=ctx.user_agent
    )


@router.get(
    "/barcode/{barcode}",
    response_model=ProductOut,
    dependencies=[Depends(require_permission("product.view"))],
    summary="Shtrix kod bo'yicha qidirish",
)
def get_product_by_barcode(db: DbSession, barcode: str) -> Product:
    from app.utils.exceptions import NotFoundError

    obj = product_crud.get_by_barcode(db, barcode)
    if obj is None:
        raise NotFoundError(f"Shtrix kod '{barcode}' bo'yicha mahsulot topilmadi")
    return obj


@router.get(
    "/{product_id}",
    response_model=ProductOut,
    dependencies=[Depends(require_permission("product.view"))],
    summary="Mahsulot ma'lumoti",
)
def get_product(db: DbSession, product_id: int) -> Product:
    return product_crud.get_or_404(db, product_id)


@router.put(
    "/{product_id}",
    response_model=ProductOut,
    dependencies=[Depends(require_permission("product.manage"))],
    summary="Mahsulotni yangilash",
)
def update_product(
    db: DbSession, ctx: ReqContext, current_user: CurrentUser, product_id: int, data: ProductUpdate
) -> Product:
    obj = product_crud.get_or_404(db, product_id)
    return product_service.update_product(
        db, obj, data, user_id=current_user.id, ip_address=ctx.ip_address, user_agent=ctx.user_agent
    )


@router.post(
    "/{product_id}/image",
    response_model=ProductOut,
    dependencies=[Depends(require_permission("product.manage"))],
    summary="Mahsulot rasmini yuklash",
)
def upload_product_image(
    db: DbSession, product_id: int, file: UploadFile = File(...)
) -> Product:
    obj = product_crud.get_or_404(db, product_id)
    relative_path = save_image(file, subdir="products")
    return product_crud.update(db, obj, {"image": relative_path})


@router.delete(
    "/{product_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("product.manage"))],
    summary="Mahsulotni o'chirish",
)
def delete_product(
    db: DbSession, ctx: ReqContext, current_user: CurrentUser, product_id: int
) -> Message:
    obj = product_crud.get_or_404(db, product_id)
    product_crud.remove(db, obj)
    audit_service.log_action(
        db,
        action=AuditAction.DELETE,
        user_id=current_user.id,
        entity_type="product",
        entity_id=product_id,
        description=f"Mahsulot o'chirildi: {obj.sku} - {obj.name}",
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return Message(detail="Mahsulot o'chirildi")
