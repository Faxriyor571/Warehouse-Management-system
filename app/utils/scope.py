"""Shared ``(company_id, store_filter)`` resolution for tenant-scoped routers.

Every business-data router (Stock In, Sales, Expenses, Debts, Reports) had its
own near-identical ``_resolve_write_scope``/``_resolve_read_scope`` pair. This
is the single implementation, extended for the ERP role redesign: a Cashier
is confined to their own store (unchanged legacy behavior), but a Warehouse
Employee or Accountant — like a CEO — is company-wide, since their job
(moving stock between stores, seeing company-wide financials) inherently
isn't tied to one store.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.crud.store import store as store_crud
from app.models.enums import EmployeeRole, UserRole
from app.models.user import User
from app.utils.exceptions import NotFoundError, ValidationError


def resolve_scope(
    current_user: User,
    requested_store_id: int | None,
    db: Session,
    *,
    require_store_id: bool = False,
) -> tuple[int | None, int | None]:
    """Resolve ``(company_id, store_filter)`` for a tenant-scoped read/write.

    - A Cashier (``role=SELLER``, ``employee_role=CASHIER``) is always
      confined to their own store — ``requested_store_id`` is ignored.
    - CEO, Warehouse Employee, and Accountant are company-wide:
      ``requested_store_id`` is an optional (or, if ``require_store_id``,
      mandatory) filter/target, validated to belong to their company.
    - The legacy single-tenant admin (``role is None``) gets ``(None, None)``.
    """
    if current_user.role == UserRole.SELLER and current_user.employee_role == EmployeeRole.CASHIER:
        return current_user.company_id, current_user.store_id
    if current_user.role in (UserRole.CEO, UserRole.SELLER):
        if require_store_id and requested_store_id is None:
            raise ValidationError("store_id majburiy")
        if requested_store_id is not None:
            store = store_crud.get_for_company(db, requested_store_id, current_user.company_id)
            if store is None:
                raise NotFoundError(f"Do'kon (id={requested_store_id}) topilmadi")
        return current_user.company_id, requested_store_id
    return None, None  # legacy single-tenant admin
