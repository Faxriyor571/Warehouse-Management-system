"""Permission catalogue and default role -> permission mapping.

Permission codes follow the ``<resource>.<action>`` convention. The catalogue
below is the single source of truth used when seeding the database.
"""
from __future__ import annotations

from app.models.enums import RoleName


# ---------------------------------------------------------------------------
# Permission definitions: code -> (human name, group)
# ---------------------------------------------------------------------------
PERMISSIONS: dict[str, tuple[str, str]] = {
    # Users & access control
    "user.view": ("Foydalanuvchilarni ko'rish", "user"),
    "user.manage": ("Foydalanuvchilarni boshqarish", "user"),
    "role.view": ("Rollarni ko'rish", "role"),
    "role.manage": ("Rollarni boshqarish", "role"),
    "permission.view": ("Ruxsatlarni ko'rish", "permission"),
    # Catalogue
    "category.view": ("Kategoriyalarni ko'rish", "category"),
    "category.manage": ("Kategoriyalarni boshqarish", "category"),
    "unit.view": ("Birliklarni ko'rish", "unit"),
    "unit.manage": ("Birliklarni boshqarish", "unit"),
    "product.view": ("Mahsulotlarni ko'rish", "product"),
    "product.manage": ("Mahsulotlarni boshqarish", "product"),
    # Partners
    "supplier.view": ("Yetkazib beruvchilarni ko'rish", "supplier"),
    "supplier.manage": ("Yetkazib beruvchilarni boshqarish", "supplier"),
    "customer.view": ("Mijozlarni ko'rish", "customer"),
    "customer.manage": ("Mijozlarni boshqarish", "customer"),
    # Operations
    "stock_in.view": ("Kirimlarni ko'rish", "stock_in"),
    "stock_in.manage": ("Kirim qilish", "stock_in"),
    "stock_out.view": ("Chiqimlarni ko'rish", "stock_out"),
    "stock_out.manage": ("Chiqim qilish", "stock_out"),
    # Payments & debts
    "payment_method.view": ("To'lov turlarini ko'rish", "payment"),
    "payment_method.manage": ("To'lov turlarini boshqarish", "payment"),
    "debt.view": ("Qarzlarni ko'rish", "debt"),
    "debt.manage": ("Qarzlarni boshqarish", "debt"),
    # Insights
    "dashboard.view": ("Dashboardni ko'rish", "dashboard"),
    "report.view": ("Hisobotlarni ko'rish", "report"),
    "audit.view": ("Audit jurnalini ko'rish", "audit"),
    "setting.manage": ("Sozlamalarni boshqarish", "setting"),
}

ALL_PERMISSION_CODES: list[str] = list(PERMISSIONS.keys())


# ---------------------------------------------------------------------------
# Role descriptions
# ---------------------------------------------------------------------------
ROLE_DESCRIPTIONS: dict[RoleName, str] = {
    RoleName.ADMIN: "To'liq huquqli administrator",
    RoleName.MANAGER: "Menejer — operatsiyalar va hisobotlar",
    RoleName.WAREHOUSE_WORKER: "Ombor xodimi — kirim/chiqim",
    RoleName.CASHIER: "Kassir — chiqim va to'lovlar",
    RoleName.VIEWER: "Kuzatuvchi — faqat ko'rish",
}


# ---------------------------------------------------------------------------
# Default role -> permission assignments
# ---------------------------------------------------------------------------
_VIEW_ONLY = [c for c in ALL_PERMISSION_CODES if c.endswith(".view")]

DEFAULT_ROLE_PERMISSIONS: dict[RoleName, list[str]] = {
    # Admin gets everything (also has is_superuser bypass, but keep explicit).
    RoleName.ADMIN: list(ALL_PERMISSION_CODES),
    # Manager: manage catalogue/partners/operations + view everything.
    RoleName.MANAGER: sorted(
        set(
            _VIEW_ONLY
            + [
                "category.manage",
                "unit.manage",
                "product.manage",
                "supplier.manage",
                "customer.manage",
                "stock_in.manage",
                "stock_out.manage",
                "debt.manage",
                "report.view",
                "dashboard.view",
            ]
        )
    ),
    # Warehouse worker: stock in/out + view catalogue.
    RoleName.WAREHOUSE_WORKER: sorted(
        set(
            [
                "product.view",
                "category.view",
                "unit.view",
                "supplier.view",
                "customer.view",
                "stock_in.view",
                "stock_in.manage",
                "stock_out.view",
                "stock_out.manage",
                "dashboard.view",
            ]
        )
    ),
    # Cashier: sales + payments + debts.
    RoleName.CASHIER: sorted(
        set(
            [
                "product.view",
                "customer.view",
                "customer.manage",
                "stock_out.view",
                "stock_out.manage",
                "payment_method.view",
                "debt.view",
                "debt.manage",
                "dashboard.view",
            ]
        )
    ),
    # Viewer: read-only.
    RoleName.VIEWER: sorted(set(_VIEW_ONLY + ["dashboard.view"])),
}
