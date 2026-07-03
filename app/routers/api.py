"""Aggregate API router that mounts every feature router under a version prefix."""
from __future__ import annotations

from fastapi import APIRouter

from app.routers import (
    audit,
    auth,
    categories,
    customers,
    dashboard,
    debts,
    payment_methods,
    products,
    reminders,
    reports,
    roles,
    settings,
    stock_in,
    stock_out,
    suppliers,
    units,
    users,
)

api_router = APIRouter()

# Authentication & identity
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)

# Catalogue
api_router.include_router(categories.router)
api_router.include_router(units.router)
api_router.include_router(products.router)

# Partners
api_router.include_router(suppliers.router)
api_router.include_router(customers.router)

# Operations
api_router.include_router(stock_in.router)
api_router.include_router(stock_out.router)

# Payments & debts
api_router.include_router(payment_methods.router)
api_router.include_router(debts.router)
api_router.include_router(reminders.router)

# Insights
api_router.include_router(dashboard.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
api_router.include_router(settings.router)
