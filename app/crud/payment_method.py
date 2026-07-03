"""Payment method data-access operations."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.enums import PaymentMethodType
from app.models.payment_method import PaymentMethod


class CRUDPaymentMethod(CRUDBase[PaymentMethod]):
    """CRUD operations for :class:`PaymentMethod`."""

    def get_by_type(self, db: Session, type_: PaymentMethodType) -> PaymentMethod | None:
        stmt = select(PaymentMethod).where(PaymentMethod.type == type_)
        return db.execute(stmt).scalars().first()

    def get_by_name(self, db: Session, name: str) -> PaymentMethod | None:
        stmt = select(PaymentMethod).where(PaymentMethod.name == name)
        return db.execute(stmt).scalar_one_or_none()


payment_method = CRUDPaymentMethod(PaymentMethod)
