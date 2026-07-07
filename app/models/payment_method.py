"""Payment method model (To'lov turlari).

Payment methods are configured per company (DATABASE_DESIGN.md §3.18/§6): CEO
manages them, a Seller only reads them (to pick one at sale time). Each is
linked to a ``PaymentMethodType`` enum so business logic (e.g. "is this a
debt?") does not depend on free-text names.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import PaymentMethodType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.debt import DebtPayment
    from app.models.payment import Payment


class PaymentMethod(Base, TimestampMixin):
    """A payment method usable at checkout (Naqd, Click, Payme, Bank, Qarz).

    ``company_id`` is nullable for the legacy single-tenant scope; ``name`` is
    unique **within its company** (not globally — §6), enforced by the
    constraint below plus a NULL-scoped partial index for legacy rows.
    """

    __tablename__ = "payment_methods"

    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_payment_methods_company_name"),
        Index(
            "uq_payment_methods_null_company_name",
            "name",
            unique=True,
            sqlite_where=text("company_id IS NULL"),
            postgresql_where=text("company_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    type: Mapped[PaymentMethodType] = mapped_column(
        SAEnum(PaymentMethodType, name="payment_method_type"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # System methods (the 5 defaults, seeded per company) cannot be deleted
    # or deactivated.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    payments: Mapped[list["Payment"]] = relationship(back_populates="payment_method")
    debt_payments: Mapped[list["DebtPayment"]] = relationship(back_populates="payment_method")

    @property
    def is_debt(self) -> bool:
        return self.type == PaymentMethodType.DEBT

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PaymentMethod {self.name}>"
