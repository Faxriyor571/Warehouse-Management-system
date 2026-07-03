"""Product business logic: validation and audited create/update."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.crud.category import category as category_crud
from app.crud.product import product as product_crud
from app.crud.unit import unit as unit_crud
from app.models.enums import AuditAction
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.services import audit_service
from app.utils.exceptions import ConflictError, NotFoundError


def _validate_refs(db: Session, category_id: int, unit_id: int) -> None:
    if category_crud.get(db, category_id) is None:
        raise NotFoundError(f"Kategoriya (id={category_id}) topilmadi")
    if unit_crud.get(db, unit_id) is None:
        raise NotFoundError(f"Birlik (id={unit_id}) topilmadi")


def _check_unique(db: Session, sku: str, barcode: str | None, exclude_id: int | None = None) -> None:
    existing = product_crud.get_by_sku(db, sku)
    if existing and existing.id != exclude_id:
        raise ConflictError(f"SKU '{sku}' allaqachon mavjud")
    if barcode:
        existing_bc = product_crud.get_by_barcode(db, barcode)
        if existing_bc and existing_bc.id != exclude_id:
            raise ConflictError(f"Shtrix kod '{barcode}' allaqachon mavjud")


def create_product(
    db: Session,
    data: ProductCreate,
    *,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Product:
    _check_unique(db, data.sku, data.barcode)
    _validate_refs(db, data.category_id, data.unit_id)

    obj = product_crud.create(db, data.model_dump())
    audit_service.log_action(
        db,
        action=AuditAction.CREATE,
        user_id=user_id,
        entity_type="product",
        entity_id=obj.id,
        description=f"Mahsulot qo'shildi: {obj.sku} - {obj.name}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return obj


def update_product(
    db: Session,
    product: Product,
    data: ProductUpdate,
    *,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Product:
    payload = data.model_dump(exclude_unset=True)

    new_sku = payload.get("sku", product.sku)
    new_barcode = payload.get("barcode", product.barcode)
    if "sku" in payload or "barcode" in payload:
        _check_unique(db, new_sku, new_barcode, exclude_id=product.id)

    category_id = payload.get("category_id", product.category_id)
    unit_id = payload.get("unit_id", product.unit_id)
    if "category_id" in payload or "unit_id" in payload:
        _validate_refs(db, category_id, unit_id)

    price_changed = (
        "purchase_price" in payload and payload["purchase_price"] != product.purchase_price
    ) or ("sale_price" in payload and payload["sale_price"] != product.sale_price)

    updated = product_crud.update(db, product, payload)

    action = AuditAction.PRICE_CHANGE if price_changed else AuditAction.UPDATE
    audit_service.log_action(
        db,
        action=action,
        user_id=user_id,
        entity_type="product",
        entity_id=updated.id,
        description=f"Mahsulot yangilandi: {updated.sku} - {updated.name}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return updated
