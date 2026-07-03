"""Debt data-access operations."""
from __future__ import annotations

from app.crud.base import CRUDBase
from app.models.debt import Debt, DebtPayment


class CRUDDebt(CRUDBase[Debt]):
    """CRUD operations for :class:`Debt`."""


class CRUDDebtPayment(CRUDBase[DebtPayment]):
    """CRUD operations for :class:`DebtPayment`."""


debt = CRUDDebt(Debt)
debt_payment = CRUDDebtPayment(DebtPayment)
