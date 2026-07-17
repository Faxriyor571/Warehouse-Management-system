"""Aggregate API router that mounts every feature router under a version prefix."""
from __future__ import annotations

from fastapi import APIRouter

from app.routers import (
    audit,
    auth,
    categories,
    companies,
    customers,
    dashboard,
    debts,
    employees,
    expenses,
    inventory,
    payment_methods,
    products,
    reminders,
    reports,
    roles,
    settings,
    stock_in,
    stock_out,
    stores,
    suppliers,
    units,
    users,
)

api_router = APIRouter()

# Authentication & identity
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)

# Platform administration (multi-tenant, Super Admin only)
api_router.include_router(companies.router)

# Company operations (multi-tenant, CEO / Seller)
api_router.include_router(stores.router)
api_router.include_router(employees.router)
api_router.include_router(inventory.router)

# Catalogue
api_router.include_router(categories.router)
api_router.include_router(units.router)
api_router.include_router(products.router)

# Partners
api_router.include_router(suppliers.router)
api_router.include_router(customers.router)

# Operations
api_router.include_router(stock_in.router)
# Sales: mounted at both /stock-out (legacy) and /sales (API_SPECIFICATION.md
# §9) — same router, same implementation, no code duplication.
api_router.include_router(stock_out.router, prefix="/stock-out")
api_router.include_router(stock_out.router, prefix="/sales")

# Payments & debts
api_router.include_router(payment_methods.router)
api_router.include_router(debts.router)
api_router.include_router(reminders.router)
api_router.include_router(expenses.router)

# Insights
api_router.include_router(dashboard.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
api_router.include_router(settings.router)
