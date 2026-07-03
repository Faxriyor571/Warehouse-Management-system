"""Payment method CRUD endpoints (admin-managed)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import DbSession
from app.crud.payment_method import payment_method as pm_crud
from app.models.payment_method import PaymentMethod
from app.permissions.dependencies import require_permission
from app.schemas.common import Message
from app.schemas.payment_method import (
    PaymentMethodCreate,
    PaymentMethodOut,
    PaymentMethodUpdate,
)
from app.utils.exceptions import ConflictError, ValidationError

router = APIRouter(prefix="/payment-methods", tags=["Payment Methods"])


@router.get(
    "",
    response_model=list[PaymentMethodOut],
    dependencies=[Depends(require_permission("payment_method.view"))],
    summary="To'lov turlari ro'yxati",
)
def list_payment_methods(db: DbSession) -> list[PaymentMethod]:
    return list(pm_crud.get_all(db))


@router.post(
    "",
    response_model=PaymentMethodOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("payment_method.manage"))],
    summary="To'lov turi qo'shish",
)
def create_payment_method(db: DbSession, data: PaymentMethodCreate) -> PaymentMethod:
    if pm_crud.get_by_name(db, data.name) is not None:
        raise ConflictError(f"'{data.name}' to'lov turi allaqachon mavjud")
    return pm_crud.create(db, {**data.model_dump(), "is_system": False})


@router.put(
    "/{method_id}",
    response_model=PaymentMethodOut,
    dependencies=[Depends(require_permission("payment_method.manage"))],
    summary="To'lov turini yangilash",
)
def update_payment_method(
    db: DbSession, method_id: int, data: PaymentMethodUpdate
) -> PaymentMethod:
    obj = pm_crud.get_or_404(db, method_id)
    return pm_crud.update(db, obj, data.model_dump(exclude_unset=True))


@router.delete(
    "/{method_id}",
    response_model=Message,
    dependencies=[Depends(require_permission("payment_method.manage"))],
    summary="To'lov turini o'chirish",
)
def delete_payment_method(db: DbSession, method_id: int) -> Message:
    obj = pm_crud.get_or_404(db, method_id)
    if obj.is_system:
        raise ValidationError("Tizim to'lov turini o'chirib bo'lmaydi (nofaol qiling)")
    pm_crud.hard_delete(db, obj)
    return Message(detail="To'lov turi o'chirildi")
