"""Generic CRUD base class.

Provides reusable create/read/update/delete and list-with-search-and-pagination
operations for any SQLAlchemy model, reducing duplication across the data layer.
"""
from __future__ import annotations

from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.database import Base
from app.utils.exceptions import NotFoundError
from app.utils.pagination import PageParams

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    """Base data-access object for a single model type."""

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model
        self.has_soft_delete = hasattr(model, "deleted_at")

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def _base_select(self, include_deleted: bool = False) -> Select[tuple[ModelType]]:
        stmt = select(self.model)
        if self.has_soft_delete and not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return stmt

    def get(self, db: Session, obj_id: int, *, include_deleted: bool = False) -> ModelType | None:
        stmt = self._base_select(include_deleted).where(self.model.id == obj_id)  # type: ignore[attr-defined]
        return db.execute(stmt).scalar_one_or_none()

    def get_or_404(self, db: Session, obj_id: int) -> ModelType:
        obj = self.get(db, obj_id)
        if obj is None:
            raise NotFoundError(f"{self.model.__name__} (id={obj_id}) topilmadi")
        return obj

    def get_all(self, db: Session, *, include_deleted: bool = False) -> Sequence[ModelType]:
        return db.execute(self._base_select(include_deleted)).scalars().all()

    def list(
        self,
        db: Session,
        *,
        page_params: PageParams,
        search: str | None = None,
        search_fields: Sequence[InstrumentedAttribute[Any]] | None = None,
        filters: Sequence[Any] | None = None,
        order_by: Any | None = None,
    ) -> tuple[Sequence[ModelType], int]:
        """Return a page of rows plus the total count matching the filters."""
        stmt = self._base_select()

        if filters:
            for f in filters:
                stmt = stmt.where(f)

        if search and search_fields:
            like = f"%{search.strip()}%"
            stmt = stmt.where(or_(*[field.ilike(like) for field in search_fields]))

        # Total count (without pagination/order).
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = db.execute(count_stmt).scalar_one()

        if order_by is not None:
            stmt = stmt.order_by(order_by)
        else:
            stmt = stmt.order_by(self.model.id.desc())  # type: ignore[attr-defined]

        stmt = stmt.offset(page_params.offset).limit(page_params.limit)
        items = db.execute(stmt).scalars().all()
        return items, total

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def create(self, db: Session, data: dict[str, Any], *, commit: bool = True) -> ModelType:
        obj = self.model(**data)
        db.add(obj)
        if commit:
            db.commit()
            db.refresh(obj)
        else:
            db.flush()
        return obj

    def update(
        self, db: Session, db_obj: ModelType, data: dict[str, Any], *, commit: bool = True
    ) -> ModelType:
        for key, value in data.items():
            setattr(db_obj, key, value)
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        else:
            db.flush()
        return db_obj

    def remove(self, db: Session, db_obj: ModelType, *, commit: bool = True) -> None:
        """Soft-delete if supported, otherwise hard-delete."""
        if self.has_soft_delete:
            from datetime import datetime, timezone

            db_obj.deleted_at = datetime.now(timezone.utc)  # type: ignore[attr-defined]
            db.add(db_obj)
        else:
            db.delete(db_obj)
        if commit:
            db.commit()

    def hard_delete(self, db: Session, db_obj: ModelType, *, commit: bool = True) -> None:
        db.delete(db_obj)
        if commit:
            db.commit()

    def count(self, db: Session, *, filters: Sequence[Any] | None = None) -> int:
        stmt = self._base_select()
        if filters:
            for f in filters:
                stmt = stmt.where(f)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        return db.execute(count_stmt).scalar_one()
