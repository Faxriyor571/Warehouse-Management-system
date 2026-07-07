"""Payment method data-access operations. Every query is scoped to a company.

``company_id=None`` resolves the legacy single-tenant scope
(``company_id IS NULL``); a concrete ``company_id`` resolves within that
company. This mirrors the uniqueness constraint on the model.
"""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.enums import PaymentMethodType
from app.models.payment_method import PaymentMethod

# The 5 system defaults, seeded for every company (and, for the legacy
# single-tenant scope, once with company_id=None) at onboarding time.
DEFAULT_PAYMENT_METHODS: list[tuple[str, PaymentMethodType]] = [
    ("Naqd", PaymentMethodType.CASH),
    ("Click", PaymentMethodType.CLICK),
    ("Payme", PaymentMethodType.PAYME),
    ("Bank", PaymentMethodType.BANK),
    ("Qarz", PaymentMethodType.DEBT),
]


class CRUDPaymentMethod(CRUDBase[PaymentMethod]):
    """CRUD operations for :class:`PaymentMethod`, always company-scoped."""

    @staticmethod
    def _company_filter(company_id: int | None) -> ColumnElement[bool]:
        if company_id is None:
            return PaymentMethod.company_id.is_(None)
        return PaymentMethod.company_id == company_id

    def get_for_company(
        self, db: Session, method_id: int, company_id: int | None
    ) -> PaymentMethod | None:
        stmt = select(PaymentMethod).where(
            PaymentMethod.id == method_id, self._company_filter(company_id)
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_for_company(
        self, db: Session, company_id: int | None
    ) -> Sequence[PaymentMethod]:
        stmt = (
            select(PaymentMethod)
            .where(self._company_filter(company_id))
            .order_by(PaymentMethod.id.asc())
        )
        return db.execute(stmt).scalars().all()

    def get_by_name_for_company(
        self, db: Session, name: str, company_id: int | None
    ) -> PaymentMethod | None:
        stmt = select(PaymentMethod).where(
            PaymentMethod.name == name, self._company_filter(company_id)
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_type_for_company(
        self, db: Session, type_: PaymentMethodType, company_id: int | None
    ) -> PaymentMethod | None:
        stmt = select(PaymentMethod).where(
            PaymentMethod.type == type_, self._company_filter(company_id)
        )
        return db.execute(stmt).scalars().first()

    def seed_defaults_for_company(self, db: Session, company_id: int | None) -> None:
        """Idempotently seed the 5 system methods for a company (or, with
        ``company_id=None``, for the legacy single-tenant scope)."""
        existing = {pm.name for pm in self.list_for_company(db, company_id)}
        for name, type_ in DEFAULT_PAYMENT_METHODS:
            if name not in existing:
                db.add(
                    PaymentMethod(
                        company_id=company_id,
                        name=name,
                        type=type_,
                        is_active=True,
                        is_system=True,
                    )
                )


payment_method = CRUDPaymentMethod(PaymentMethod)
