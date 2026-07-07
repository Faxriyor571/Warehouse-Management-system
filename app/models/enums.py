"""Enumerations used across the domain models.

Using ``str, Enum`` makes the values human-readable in the database and JSON,
while still being type-safe in Python.
"""
from __future__ import annotations

import enum


class RoleName(str, enum.Enum):
    """Built-in system roles."""

    ADMIN = "admin"
    MANAGER = "manager"
    WAREHOUSE_WORKER = "warehouse_worker"
    CASHIER = "cashier"
    VIEWER = "viewer"


class PaymentMethodType(str, enum.Enum):
    """Types of payment methods supported by the system."""

    CASH = "cash"          # Naqd
    CLICK = "click"        # Click
    PAYME = "payme"        # Payme
    BANK = "bank"          # Bank
    DEBT = "debt"          # Qarz


class PaymentStatus(str, enum.Enum):
    """Payment status of a sale (chiqim)."""

    PAID = "paid"          # To'liq to'langan
    PARTIAL = "partial"    # Qisman to'langan
    UNPAID = "unpaid"      # To'lanmagan (qarz)


class DebtStatus(str, enum.Enum):
    """Lifecycle status of a debt (qarz)."""

    ACTIVE = "active"      # Faol (to'lanmoqda)
    PAID = "paid"          # To'liq yopilgan
    OVERDUE = "overdue"    # Muddati o'tgan


class AuditAction(str, enum.Enum):
    """Actions recorded in the audit log."""

    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    STOCK_IN = "stock_in"
    STOCK_OUT = "stock_out"
    SALES_RETURN = "sales_return"
    PAYMENT = "payment"
    PRICE_CHANGE = "price_change"
    LOGIN_FAILED = "login_failed"


class UserRole(str, enum.Enum):
    """Fixed multi-tenant role hierarchy (DATABASE_DESIGN.md §12).

    This is the permanent, final name/shape for the role concept going
    forward. It coexists with the legacy ``RoleName``/``Role`` RBAC system
    during the incremental migration; ``RoleName`` is removed once every
    module has moved over.
    """

    SUPER_ADMIN = "super_admin"
    CEO = "ceo"
    SELLER = "seller"


class CompanyStatus(str, enum.Enum):
    """Lifecycle status of a company (tenant)."""

    ACTIVE = "active"
    SUSPENDED = "suspended"


class CustomerType(str, enum.Enum):
    """Individual vs. Legal Entity (SRS rule #17), used to gate rule #18
    (legal-entity price override). Minimal addition for Sales — not a
    Customers migration."""

    INDIVIDUAL = "individual"
    LEGAL_ENTITY = "legal_entity"


class MovementType(str, enum.Enum):
    """Kinds of inventory movement recorded in ``stock_movements`` (§3.9/§11).

    ``sales_return`` and ``adjustment`` are defined now so the ledger is ready
    for the Sales-return and future stock-adjustment features; only
    ``stock_in`` and ``sale`` are produced by the writers migrated so far.
    """

    STOCK_IN = "stock_in"
    SALE = "sale"
    SALES_RETURN = "sales_return"
    ADJUSTMENT = "adjustment"
