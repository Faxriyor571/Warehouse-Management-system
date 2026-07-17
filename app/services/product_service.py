"""Product business logic (API_SPECIFICATION.md §6). Company-scoped catalogue.

``company_id`` is always supplied by the caller from the resolved user, never
by the client. ``None`` operates within the legacy single-tenant scope.

No logic here reads or writes ``product.quantity``: on-hand stock is an
inventory concern (deferred to the Inventory phase), not a catalogue concern.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.crud.category import category as category_crud
from app.crud.product import product as product_crud
from app.crud.unit import unit as unit_crud
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.utils.exceptions import ConflictError, NotFoundError


def _validate_refs(
    db: Session, company_id: int | None, category_id: int, unit_id: int
) -> None:
    """Category and unit must exist within the same company (closes the
    cross-company FK gap: a product may only reference its own company's
    catalogue rows)."""
    if category_crud.get_for_company(db, category_id, company_id) is None:
        raise NotFoundError(f"Kategoriya (id={category_id}) ushbu kompaniyada topilmadi")
    if unit_crud.get_for_company(db, unit_id, company_id) is None:
        raise NotFoundError(f"Birlik (id={unit_id}) ushbu kompaniyada topilmadi")


def _check_unique(
    db: Session,
    company_id: int | None,
    sku: str,
    barcode: str | None,
    *,
    exclude_id: int | None = None,
) -> None:
    existing = product_crud.get_by_sku_for_company(db, sku, company_id)
    if existing is not None and existing.id != exclude_id:
        raise ConflictError(f"SKU '{sku}' allaqachon mavjud")
    if barcode:
        existing_bc = product_crud.get_by_barcode_for_company(db, barcode, company_id)
        if existing_bc is not None and existing_bc.id != exclude_id:
            raise ConflictError(f"Shtrix kod '{barcode}' allaqachon mavjud")


def create_product(db: Session, company_id: int | None, data: ProductCreate) -> Product:
    _check_unique(db, company_id, data.sku, data.barcode)
    _validate_refs(db, company_id, data.category_id, data.unit_id)
    payload = data.model_dump()
    payload["company_id"] = company_id
    return product_crud.create(db, payload)


def update_product(
    db: Session, product: Product, company_id: int | None, data: ProductUpdate
) -> Product:
    payload = data.model_dump(exclude_unset=True)

    new_sku = payload.get("sku", product.sku)
    new_barcode = payload.get("barcode", product.barcode)
    if "sku" in payload or "barcode" in payload:
        _check_unique(db, company_id, new_sku, new_barcode, exclude_id=product.id)

    category_id = payload.get("category_id", product.category_id)
    unit_id = payload.get("unit_id", product.unit_id)
    if "category_id" in payload or "unit_id" in payload:
        _validate_refs(db, company_id, category_id, unit_id)

    for key, value in payload.items():
        setattr(product, key, value)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product: Product) -> None:
    """Soft-delete the product (sets ``deleted_at``)."""
    product_crud.remove(db, product)
