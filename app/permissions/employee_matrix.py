"""Multi-tenant permission matrix — the single source of truth for who can do
what in the new fixed CEO/Seller(+job function) model.

Deliberately separate from ``app/permissions/constants.py``, which belongs to
the legacy, admin-configurable ``Role``/``Permission`` system (orphaned,
gating only ``users.py``/``roles.py``/``audit.py``/``reminders.py`` — not
touched by this module).

Adding a future job function (Manager, Auditor, ...) means adding one
``EmployeeRole`` value in ``app/models/enums.py`` plus one entry in
``EMPLOYEE_ROLE_PERMS`` below — nothing else in the codebase changes.
"""
from __future__ import annotations

import enum

from app.models.enums import EmployeeRole, UserRole


class Perm(str, enum.Enum):
    """A single, fine-grained capability code, ``<module>.<action>``."""

    DASHBOARD_VIEW = "dashboard.view"

    REPORTS_SALES = "reports.sales"
    REPORTS_INVENTORY = "reports.inventory"
    REPORTS_DEBTS = "reports.debts"
    REPORTS_EXPENSES = "reports.expenses"
    REPORTS_FINANCIAL = "reports.financial"  # net profit / owner withdrawals summary

    STORES_MANAGE = "stores.manage"
    EMPLOYEES_MANAGE = "employees.manage"

    PRODUCTS_VIEW = "products.view"
    PRODUCTS_MANAGE = "products.manage"
    CATEGORIES_VIEW = "categories.view"
    CATEGORIES_MANAGE = "categories.manage"

    SALES_VIEW = "sales.view"
    SALES_MANAGE = "sales.manage"  # create a sale / sales return

    DEBTS_MANAGE = "debts.manage"

    STOCK_IN_VIEW = "stock_in.view"
    STOCK_IN_MANAGE = "stock_in.manage"  # receive inventory

    INVENTORY_VIEW = "inventory.view"

    TRANSFER_VIEW = "transfer.view"
    TRANSFER_MANAGE = "transfer.manage"  # move stock between stores

    EXPENSES_MANAGE = "expenses.manage"
    PAYROLL_MANAGE = "payroll.manage"
    WITHDRAWALS_MANAGE = "withdrawals.manage"

    SETTINGS_MANAGE = "settings.manage"

    # Embedded dependencies of the modules above (no dedicated sidebar item,
    # but their own endpoints still need a gate): a customer/supplier is
    # looked up or created inline while recording a Sale/Stock In, and a
    # payment method is picked inline at sale time.
    CUSTOMERS_VIEW = "customers.view"  # list/create/get/update — matches legacy "actor" scope
    CUSTOMERS_MANAGE = "customers.manage"  # deactivate only — CEO-only, unchanged from legacy
    SUPPLIERS_MANAGE = "suppliers.manage"  # view+write combined — no lifecycle split today
    PAYMENT_METHODS_VIEW = "payment_methods.view"
    PAYMENT_METHODS_MANAGE = "payment_methods.manage"


# The Company Owner (CEO) manages the business but does not perform daily
# operational data entry: they can see every module's data (view + reports)
# but not execute a sale, receive inventory, or move stock between stores —
# those are employee responsibilities.
CEO_PERMS: frozenset[Perm] = frozenset(set(Perm) - {
    Perm.SALES_MANAGE,
    Perm.STOCK_IN_MANAGE,
    Perm.TRANSFER_MANAGE,
})

EMPLOYEE_ROLE_PERMS: dict[EmployeeRole, frozenset[Perm]] = {
    # Seller / Cashier: sell products, manage customer debts, look up products.
    EmployeeRole.CASHIER: frozenset({
        Perm.DASHBOARD_VIEW,
        Perm.PRODUCTS_VIEW,
        Perm.CATEGORIES_VIEW,
        Perm.SALES_VIEW,
        Perm.SALES_MANAGE,
        Perm.DEBTS_MANAGE,
        Perm.CUSTOMERS_VIEW,
        Perm.PAYMENT_METHODS_VIEW,
    }),
    # Warehouse Employee: receive inventory, transfer between stores, view products.
    EmployeeRole.WAREHOUSE: frozenset({
        Perm.DASHBOARD_VIEW,
        Perm.PRODUCTS_VIEW,
        Perm.CATEGORIES_VIEW,
        Perm.STOCK_IN_VIEW,
        Perm.STOCK_IN_MANAGE,
        Perm.INVENTORY_VIEW,
        Perm.TRANSFER_VIEW,
        Perm.TRANSFER_MANAGE,
        Perm.SUPPLIERS_MANAGE,
    }),
    # Accountant: company finances — expenses, payroll, withdrawals, debts,
    # financial reports. No catalogue/sales/purchasing/store management.
    EmployeeRole.ACCOUNTANT: frozenset({
        Perm.DASHBOARD_VIEW,
        Perm.EXPENSES_MANAGE,
        Perm.PAYROLL_MANAGE,
        Perm.WITHDRAWALS_MANAGE,
        Perm.DEBTS_MANAGE,
        Perm.REPORTS_DEBTS,
        Perm.REPORTS_EXPENSES,
        Perm.REPORTS_FINANCIAL,
    }),
}


def permissions_for(role: UserRole | None, employee_role: EmployeeRole | None) -> frozenset[Perm]:
    """Resolve the effective permission set for a multi-tenant identity.

    ``role``/``employee_role`` are ``User.role``/``User.employee_role`` as-is.
    Returns an empty set for anything else (Super Admin has no business-data
    permissions here; the legacy admin's ``is_superuser`` bypass is handled by
    the caller, not this function).
    """
    if role == UserRole.CEO:
        return CEO_PERMS
    if role == UserRole.SELLER:
        return EMPLOYEE_ROLE_PERMS.get(employee_role, frozenset())
    return frozenset()
