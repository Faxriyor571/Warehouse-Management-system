"""ORM models package.

Importing every model here ensures they are all registered on ``Base.metadata``
before Alembic autogenerate or ``create_all`` runs.
"""
from __future__ import annotations

from app.database import Base
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.company import Company
from app.models.customer import Customer
from app.models.debt import Debt, DebtPayment
from app.models.document_sequence import DocumentSequence
from app.models.enums import (
    AuditAction,
    CompanyStatus,
    CustomerType,
    DebtStatus,
    ExpenseType,
    MovementType,
    PaymentMethodType,
    PaymentStatus,
    RoleName,
    UserRole,
)
from app.models.expense import Expense
from app.models.payment import Payment
from app.models.payment_method import PaymentMethod
from app.models.product import Product
from app.models.refresh_token import RefreshToken
from app.models.role import Permission, Role, role_permissions
from app.models.sales_return import SalesReturn, SalesReturnItem
from app.models.setting import Setting
from app.models.stock_in import StockIn, StockInItem
from app.models.stock_movement import StockMovement
from app.models.stock_out import StockOut, StockOutItem
from app.models.store import Store
from app.models.store_stock import StoreStock
from app.models.supplier import Supplier
from app.models.unit import Unit
from app.models.user import User

__all__ = [
    "Base",
    "AuditLog",
    "Category",
    "Company",
    "Customer",
    "Debt",
    "DebtPayment",
    "DocumentSequence",
    "Expense",
    "Payment",
    "PaymentMethod",
    "Product",
    "Permission",
    "RefreshToken",
    "Role",
    "role_permissions",
    "SalesReturn",
    "SalesReturnItem",
    "Setting",
    "StockIn",
    "StockInItem",
    "StockMovement",
    "StockOut",
    "StockOutItem",
    "Store",
    "StoreStock",
    "Supplier",
    "Unit",
    "User",
    # Enums
    "AuditAction",
    "CompanyStatus",
    "CustomerType",
    "DebtStatus",
    "ExpenseType",
    "MovementType",
    "PaymentMethodType",
    "PaymentStatus",
    "RoleName",
    "UserRole",
]
