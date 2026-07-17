"""Category business logic (API_SPECIFICATION.md §5). Company-scoped.

``company_id`` is always supplied by the caller from the resolved user, never
by the client. A value of ``None`` operates within the legacy single-tenant
scope; a concrete value within that company.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.crud.category import category as category_crud
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.utils.exceptions import ConflictError


def create_category(db: Session, company_id: int | None, data: CategoryCreate) -> Category:
    if category_crud.get_by_name_for_company(db, data.name, company_id) is not None:
        raise ConflictError(f"'{data.name}' nomli kategoriya allaqachon mavjud")
    payload = data.model_dump()
    payload["company_id"] = company_id
    return category_crud.create(db, payload)


def update_category(
    db: Session, category: Category, company_id: int | None, data: CategoryUpdate
) -> Category:
    payload = data.model_dump(exclude_unset=True)
    new_name = payload.get("name")
    if new_name and new_name != category.name:
        if category_crud.get_by_name_for_company(db, new_name, company_id) is not None:
            raise ConflictError(f"'{new_name}' nomli kategoriya allaqachon mavjud")
    for key, value in payload.items():
        setattr(category, key, value)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: Category) -> None:
    """Soft-delete the category (sets ``deleted_at``).

    Products keep their ``category_id`` reference; the row is never physically
    removed (API_SPECIFICATION.md §5, DATABASE_DESIGN.md §9).
    """
    category_crud.remove(db, category)
