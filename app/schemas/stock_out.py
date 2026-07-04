"""Stock-out (Chiqim / Sale) schemas."""
from __future__ import annotations

# NOTE: the date type is imported under an alias (date_type) because this
# module has a model field literally named "date" (StockOutCreate.date). Under
# "from __future__ import annotations" Pydantic v2 resolves annotations using
# the class namespace as locals, so a field named "date" would shadow the date
# type and break the optional-due-date annotation with a TypeError.
from datetime import date as date_type, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentStatus
from app.schemas.payment import PaymentCreate, PaymentOut
from app.schemas.product import ProductBrief
from app.schemas.stock_in import UserBrief


class StockOutItemCreate(BaseModel):
    """One outbound line to sell."""

    product_id: int
    quantity: Decimal = Field(gt=0)
    # If omitted, the product's current sale price is used.
    price: Decimal | None = Field(default=None, ge=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0)


class StockOutCreate(BaseModel):
    """Payload to create a sale document."""

    customer_id: int | None = None
    date: datetime | None = None
    discount: Decimal = Field(default=Decimal("0"), ge=0, description="Hujjat darajasidagi chegirma")
    note: str | None = None
    items: list[StockOutItemCreate] = Field(min_length=1)
    # Payments made at sale time (optional). Any unpaid remainder becomes a debt.
    payments: list[PaymentCreate] = Field(default_factory=list)
    # If a debt is created, this optional due date is applied.
    due_date: date_type | None = None


class StockOutItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: Decimal
    price: Decimal
    discount: Decimal
    subtotal: Decimal
    product: ProductBrief | None = None


class CustomerBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class StockOutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    customer_id: int | None = None
    created_by_id: int
    date: datetime
    subtotal: Decimal
    discount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    payment_status: PaymentStatus
    note: str | None = None
    created_at: datetime
    customer: CustomerBrief | None = None
    created_by: UserBrief | None = None
    items: list[StockOutItemOut] = Field(default_factory=list)
    payments: list[PaymentOut] = Field(default_factory=list)
