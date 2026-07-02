"""ORM models package.

Importing every model here ensures they are all registered on ``Base.metadata``
before Alembic autogenerate or ``create_all`` runs.
"""
from __future__ import annotations

from app.database import Base
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.customer import Customer
from app.models.debt import Debt, DebtPayment
from app.models.enums import (
    AuditAction,
    DebtStatus,
    PaymentMethodType,
    PaymentStatus,
    RoleName,
)
from app.models.payment import Payment
from app.models.payment_method import PaymentMethod
from app.models.product import Product
from app.models.role import Permission, Role, role_permissions
from app.models.setting import Setting
from app.models.stock_in import StockIn, StockInItem
from app.models.stock_out import StockOut, StockOutItem
from app.models.supplier import Supplier
from app.models.unit import Unit
from app.models.user import User

__all__ = [
    "Base",
    "AuditLog",
    "Category",
    "Customer",
    "Debt",
    "DebtPayment",
    "Payment",
    "PaymentMethod",
    "Product",
    "Permission",
    "Role",
    "role_permissions",
    "Setting",
    "StockIn",
    "StockInItem",
    "StockOut",
    "StockOutItem",
    "Supplier",
    "Unit",
    "User",
    # Enums
    "AuditAction",
    "DebtStatus",
    "PaymentMethodType",
    "PaymentStatus",
    "RoleName",
]
