"""Payment method schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentMethodType


class PaymentMethodBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: PaymentMethodType
    is_active: bool = True


class PaymentMethodCreate(PaymentMethodBase):
    pass


class PaymentMethodUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    type: PaymentMethodType | None = None
    is_active: bool | None = None


class PaymentMethodOut(PaymentMethodBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_system: bool
