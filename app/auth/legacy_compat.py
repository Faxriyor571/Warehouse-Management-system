"""TRANSITIONAL migration-compatibility authorization.

This module is the *single, isolated* place that holds the temporary
authorization allowances letting the legacy single-tenant admin
(``is_superuser=True``, no tenant ``role``) keep using catalogue endpoints
that have already been migrated to the multi-tenant model — while the modules
that still depend on them through the legacy admin (Products and the
stock-flow) have not yet been migrated.

Scoping is uniform and lives in the routers/services, not here: a legacy admin
has ``company_id IS NULL`` and therefore operates on the legacy (NULL-scoped)
catalogue rows, while a CEO/Seller operates on their own company. Only the
authorization gate differs between the two, and that difference is confined to
this file.

REMOVAL PLAN — when Products and the stock-flow are migrated off the legacy
admin, delete this module (or just its ``is_superuser`` branches) and point the
affected routers at ``RequireCEO`` / ``RequireCEOOrSeller``. No router, service,
or CRUD business logic needs to change.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import CurrentUser
from app.models.enums import UserRole
from app.models.user import User
from app.utils.exceptions import PermissionDeniedError


def require_catalogue_read(current_user: CurrentUser) -> User:
    """Allow a catalogue read: CEO/Seller (spec) or the legacy admin (transitional).

    Used by every catalogue module (categories, units, products).
    """
    if current_user.role in (UserRole.CEO, UserRole.SELLER):
        return current_user
    if current_user.is_superuser:  # TRANSITIONAL: legacy single-tenant admin
        return current_user
    raise PermissionDeniedError("Faqat CEO yoki sotuvchi uchun")


def require_catalogue_manage(current_user: CurrentUser) -> User:
    """Allow a catalogue write: CEO (spec) or the legacy admin (transitional).

    Used by every catalogue module (categories, units, products).
    """
    if current_user.role == UserRole.CEO:
        return current_user
    if current_user.is_superuser:  # TRANSITIONAL: legacy single-tenant admin
        return current_user
    raise PermissionDeniedError("Faqat kompaniya rahbari (CEO) uchun")


def require_stock_in_actor(current_user: CurrentUser) -> User:
    """Allow recording / reading Stock In: CEO or Seller (spec, §8) or the legacy
    admin (transitional).

    Same role set as ``require_catalogue_read`` today, but named for its own
    domain: Stock In both reads and writes are CEO+Seller, and the legacy admin
    is admitted transitionally so its ``product.quantity`` flow keeps working
    until Sales is migrated. Remove the ``is_superuser`` branch when the legacy
    world retires.
    """
    if current_user.role in (UserRole.CEO, UserRole.SELLER):
        return current_user
    if current_user.is_superuser:  # TRANSITIONAL: legacy single-tenant admin
        return current_user
    raise PermissionDeniedError("Faqat CEO yoki sotuvchi uchun")


def require_sales_actor(current_user: CurrentUser) -> User:
    """Allow recording / reading Sales (and sale returns): CEO or Seller (spec,
    §9) or the legacy admin (transitional).

    Same shape as ``require_stock_in_actor``. Remove the ``is_superuser``
    branch when the legacy world (Dashboard/Reports on product.quantity)
    retires.
    """
    if current_user.role in (UserRole.CEO, UserRole.SELLER):
        return current_user
    if current_user.is_superuser:  # TRANSITIONAL: legacy single-tenant admin
        return current_user
    raise PermissionDeniedError("Faqat CEO yoki sotuvchi uchun")


def require_customer_actor(current_user: CurrentUser) -> User:
    """Allow recording / reading Customers: CEO or Seller (spec, §10) or the
    legacy admin (transitional). Company-wide for both — Customers has no
    store scope. Remove the ``is_superuser`` branch when the legacy world
    retires.
    """
    if current_user.role in (UserRole.CEO, UserRole.SELLER):
        return current_user
    if current_user.is_superuser:  # TRANSITIONAL: legacy single-tenant admin
        return current_user
    raise PermissionDeniedError("Faqat CEO yoki sotuvchi uchun")


def require_customer_manage(current_user: CurrentUser) -> User:
    """Allow deactivating a Customer: CEO (spec, §10) or the legacy admin
    (transitional). Remove the ``is_superuser`` branch when the legacy world
    retires.
    """
    if current_user.role == UserRole.CEO:
        return current_user
    if current_user.is_superuser:  # TRANSITIONAL: legacy single-tenant admin
        return current_user
    raise PermissionDeniedError("Faqat kompaniya rahbari (CEO) uchun")


def require_payment_method_read(current_user: CurrentUser) -> User:
    """Allow reading Payment Methods: CEO or Seller (a Seller must be able to
    pick one at sale time) or the legacy admin (transitional). No dedicated
    API_SPECIFICATION.md section exists for this module; this mirrors the
    Settings access split (CEO manages, company-scoped) as the most
    conservative reading consistent with DATABASE_DESIGN.md §3.18/§6. Remove
    the ``is_superuser`` branch when the legacy world retires.
    """
    if current_user.role in (UserRole.CEO, UserRole.SELLER):
        return current_user
    if current_user.is_superuser:  # TRANSITIONAL: legacy single-tenant admin
        return current_user
    raise PermissionDeniedError("Faqat CEO yoki sotuvchi uchun")


def require_payment_method_manage(current_user: CurrentUser) -> User:
    """Allow managing Payment Methods: CEO only (or the legacy admin,
    transitional). See ``require_payment_method_read`` for the access-model
    rationale. Remove the ``is_superuser`` branch when the legacy world
    retires.
    """
    if current_user.role == UserRole.CEO:
        return current_user
    if current_user.is_superuser:  # TRANSITIONAL: legacy single-tenant admin
        return current_user
    raise PermissionDeniedError("Faqat kompaniya rahbari (CEO) uchun")


def require_debt_actor(current_user: CurrentUser) -> User:
    """Allow reading Debts / recording repayments / editing due-date: CEO or
    Seller (spec, §11) or the legacy admin (transitional). Remove the
    ``is_superuser`` branch when the legacy world retires.
    """
    if current_user.role in (UserRole.CEO, UserRole.SELLER):
        return current_user
    if current_user.is_superuser:  # TRANSITIONAL: legacy single-tenant admin
        return current_user
    raise PermissionDeniedError("Faqat CEO yoki sotuvchi uchun")


def require_legacy_debt_manage(current_user: CurrentUser) -> User:
    """Allow creating a standalone debt (not tied to a sale): legacy admin
    only. Not a spec'd endpoint (API_SPECIFICATION.md §11 only creates debts
    automatically via Sales) — kept working for the legacy flow, not
    extended to CEO/Seller. Remove when the legacy world retires.
    """
    if current_user.is_superuser:  # TRANSITIONAL: legacy single-tenant admin
        return current_user
    raise PermissionDeniedError("Faqat administrator uchun")


RequireCatalogueRead = Annotated[User, Depends(require_catalogue_read)]
RequireCatalogueManage = Annotated[User, Depends(require_catalogue_manage)]
RequireStockInActor = Annotated[User, Depends(require_stock_in_actor)]
RequireSalesActor = Annotated[User, Depends(require_sales_actor)]
RequireCustomerActor = Annotated[User, Depends(require_customer_actor)]
RequireCustomerManage = Annotated[User, Depends(require_customer_manage)]
RequirePaymentMethodRead = Annotated[User, Depends(require_payment_method_read)]
RequirePaymentMethodManage = Annotated[User, Depends(require_payment_method_manage)]
RequireDebtActor = Annotated[User, Depends(require_debt_actor)]
RequireLegacyDebtManage = Annotated[User, Depends(require_legacy_debt_manage)]
