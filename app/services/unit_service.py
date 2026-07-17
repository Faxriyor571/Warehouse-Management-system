"""Unit business logic. Company-scoped.

``company_id`` is always supplied by the caller from the resolved user, never
by the client. ``None`` operates within the legacy single-tenant scope.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.crud.unit import unit as unit_crud
from app.models.unit import Unit
from app.schemas.unit import UnitCreate, UnitUpdate
from app.utils.exceptions import ConflictError


def create_unit(db: Session, company_id: int | None, data: UnitCreate) -> Unit:
    if unit_crud.get_by_name_for_company(db, data.name, company_id) is not None:
        raise ConflictError(f"'{data.name}' nomli birlik allaqachon mavjud")
    payload = data.model_dump()
    payload["company_id"] = company_id
    return unit_crud.create(db, payload)


def update_unit(db: Session, unit: Unit, company_id: int | None, data: UnitUpdate) -> Unit:
    payload = data.model_dump(exclude_unset=True)
    new_name = payload.get("name")
    if new_name and new_name != unit.name:
        if unit_crud.get_by_name_for_company(db, new_name, company_id) is not None:
            raise ConflictError(f"'{new_name}' nomli birlik allaqachon mavjud")
    for key, value in payload.items():
        setattr(unit, key, value)
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


def delete_unit(db: Session, unit: Unit) -> None:
    """Delete a unit.

    Units have no soft-delete column; deletion is physical. A unit referenced
    by any product is protected by the ``RESTRICT`` foreign key
    (DATABASE_DESIGN.md §9) and cannot be removed — matching the legacy
    behaviour this migrates.
    """
    unit_crud.remove(db, unit)
