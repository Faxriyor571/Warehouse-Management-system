"""Payment method model (To'lov turlari).

Payment methods are configurable by the admin. Each is linked to a
``PaymentMethodType`` enum so business logic (e.g. "is this a debt?") does not
depend on free-text names.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import PaymentMethodType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.debt import DebtPayment
    from app.models.payment import Payment


class PaymentMethod(Base, TimestampMixin):
    """A payment method usable at checkout (Naqd, Click, Payme, Bank, Qarz)."""

    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    type: Mapped[PaymentMethodType] = mapped_column(
        SAEnum(PaymentMethodType, name="payment_method_type"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # System methods (the 5 defaults) cannot be deleted, only deactivated.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    payments: Mapped[list["Payment"]] = relationship(back_populates="payment_method")
    debt_payments: Mapped[list["DebtPayment"]] = relationship(back_populates="payment_method")

    @property
    def is_debt(self) -> bool:
        return self.type == PaymentMethodType.DEBT

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PaymentMethod {self.name}>"
