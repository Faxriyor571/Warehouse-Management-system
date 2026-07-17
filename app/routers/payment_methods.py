"""Payment method endpoints.

Company-scoped (DATABASE_DESIGN.md §3.18/§6). No dedicated
API_SPECIFICATION.md section exists for this module; reading is gated by
``Perm.PAYMENT_METHODS_VIEW`` (a Cashier must still be able to read the list
to pick a method at sale time), writing by ``Perm.PAYMENT_METHODS_MANAGE``
(CEO only, same as Settings). The legacy single-tenant admin bypasses via
``is_superuser`` inside ``require_perm`` and operates in the NULL-company
scope. Super Admin has no access. System methods (``is_system=True``) can be
neither deleted nor deactivated.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import DbSession
from app.auth.permissions import require_perm
from app.crud.payment_method import payment_method as pm_crud
from app.models.enums import UserRole
from app.models.payment_method import PaymentMethod
from app.models.user import User
from app.permissions.employee_matrix import Perm
from app.schemas.common import Message
from app.schemas.payment_method import (
    PaymentMethodCreate,
    PaymentMethodOut,
    PaymentMethodUpdate,
)
from app.utils.exceptions import ConflictError, NotFoundError, ValidationError

router = APIRouter(prefix="/payment-methods", tags=["Payment Methods"])

RequirePaymentMethodRead = Annotated[User, Depends(require_perm(Perm.PAYMENT_METHODS_VIEW))]
RequirePaymentMethodManage = Annotated[User, Depends(require_perm(Perm.PAYMENT_METHODS_MANAGE))]


def _resolve_company(current_user: User) -> int | None:
    if current_user.role in (UserRole.CEO, UserRole.SELLER):
        return current_user.company_id
    return None  # legacy single-tenant admin


def _get_or_404(db: DbSession, current_user: User, method_id: int) -> PaymentMethod:
    obj = pm_crud.get_for_company(db, method_id, _resolve_company(current_user))
    if obj is None:
        raise NotFoundError(f"To'lov turi (id={method_id}) topilmadi")
    return obj


@router.get("", response_model=list[PaymentMethodOut], summary="To'lov turlari ro'yxati")
def list_payment_methods(db: DbSession, current_user: RequirePaymentMethodRead) -> list[PaymentMethod]:
    return list(pm_crud.list_for_company(db, _resolve_company(current_user)))


@router.post(
    "",
    response_model=PaymentMethodOut,
    status_code=status.HTTP_201_CREATED,
    summary="To'lov turi qo'shish",
)
def create_payment_method(
    db: DbSession, current_user: RequirePaymentMethodManage, data: PaymentMethodCreate
) -> PaymentMethod:
    company_id = _resolve_company(current_user)
    if pm_crud.get_by_name_for_company(db, data.name, company_id) is not None:
        raise ConflictError(f"'{data.name}' to'lov turi allaqachon mavjud")
    return pm_crud.create(db, {**data.model_dump(), "company_id": company_id, "is_system": False})


@router.put(
    "/{method_id}",
    response_model=PaymentMethodOut,
    summary="To'lov turini yangilash",
)
def update_payment_method(
    db: DbSession, current_user: RequirePaymentMethodManage, method_id: int, data: PaymentMethodUpdate
) -> PaymentMethod:
    obj = _get_or_404(db, current_user, method_id)
    payload = data.model_dump(exclude_unset=True)
    if obj.is_system and payload.get("is_active") is False:
        raise ValidationError("Tizim to'lov turini faolsizlantirib bo'lmaydi")
    return pm_crud.update(db, obj, payload)


@router.delete(
    "/{method_id}",
    response_model=Message,
    summary="To'lov turini o'chirish",
)
def delete_payment_method(db: DbSession, current_user: RequirePaymentMethodManage, method_id: int) -> Message:
    obj = _get_or_404(db, current_user, method_id)
    if obj.is_system:
        raise ValidationError("Tizim to'lov turini o'chirib bo'lmaydi")
    pm_crud.hard_delete(db, obj)
    return Message(detail="To'lov turi o'chirildi")
