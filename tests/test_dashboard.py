"""Tests for the migrated Dashboard module (Phase 13, API_SPECIFICATION.md §13).

Role-based, same response shape for CEO/Seller (``scope`` differs): CEO gets
company-wide aggregation, Seller gets their own store only. Legacy admin
transitional; Super Admin has no access.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import security
from app.crud.company import company as company_crud
from app.crud.payment_method import payment_method as pm_crud
from app.models.enums import PaymentMethodType, UserRole
from app.models.user import User


def _make_super_admin(db: Session, username: str) -> None:
    db.add(
        User(
            username=username,
            full_name="Root",
            hashed_password=security.hash_password("Root12345!"),
            role_id=None,
            role=UserRole.SUPER_ADMIN,
            company_id=None,
            store_id=None,
            is_active=True,
        )
    )
    db.commit()


def _bearer(client: TestClient, username: str, password: str, company_slug: str | None = None) -> dict[str, str]:
    data = {"username": username, "password": password}
    if company_slug is not None:
        data["company_slug"] = company_slug
    resp = client.post("/api/v1/auth/login", data=data)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _onboard(client: TestClient, db: Session, slug: str) -> dict[str, str]:
    root = f"root-{slug}"
    _make_super_admin(db, root)
    sa = _bearer(client, root, "Root12345!")
    payload = {
        "name": f"Co {slug}",
        "slug": slug,
        "contact_email": None,
        "contact_phone": None,
        "ceo": {"username": f"ceo-{slug}", "full_name": "CEO", "password": "Ceo12345!", "email": None},
    }
    assert client.post("/api/v1/companies", headers=sa, json=payload).status_code == 201
    return _bearer(client, f"ceo-{slug}", "Ceo12345!", company_slug=slug)


def _store(client: TestClient, ceo: dict[str, str], name: str = "Store") -> int:
    return client.post("/api/v1/stores", headers=ceo, json={"name": name}).json()["id"]


def _seller(client: TestClient, ceo: dict[str, str], slug: str, username: str, store_id: int) -> dict[str, str]:
    resp = client.post(
        "/api/v1/employees",
        headers=ceo,
        json={"username": username, "full_name": "Seller", "password": "Sell12345!", "store_id": store_id},
    )
    assert resp.status_code == 201, resp.text
    return _bearer(client, username, "Sell12345!", company_slug=slug)


def _warehouse(client: TestClient, ceo: dict[str, str], slug: str, username: str) -> dict[str, str]:
    """A company-wide Warehouse Employee — the only job function that can
    record a Stock In under the ERP role redesign."""
    resp = client.post(
        "/api/v1/employees",
        headers=ceo,
        json={"username": username, "full_name": "Warehouse", "password": "Wh12345!", "employee_role": "warehouse"},
    )
    assert resp.status_code == 201, resp.text
    return _bearer(client, username, "Wh12345!", company_slug=slug)


def _stock_in(client: TestClient, warehouse: dict[str, str], store_id: int, product_id: int, qty: str = "50") -> None:
    resp = client.post(
        "/api/v1/stock-in",
        headers=warehouse,
        json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": qty, "price": "10.00"}]},
    )
    assert resp.status_code == 201, resp.text


def _product(client: TestClient, ceo: dict[str, str], sku: str) -> int:
    cat = client.post("/api/v1/categories", headers=ceo, json={"name": f"Cat-{sku}"}).json()["id"]
    unit = client.post("/api/v1/units", headers=ceo, json={"name": f"Unit-{sku}", "short_name": "u"}).json()["id"]
    resp = client.post(
        "/api/v1/products",
        headers=ceo,
        json={"name": f"P-{sku}", "sku": sku, "category_id": cat, "unit_id": unit, "purchase_price": "10.00", "sale_price": "15.00"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _company_id(db: Session, slug: str) -> int:
    company = company_crud.get_by_slug(db, slug)
    assert company is not None
    return company.id


def _cash_method_id(db: Session, company_id: int) -> int:
    method = pm_crud.get_by_type_for_company(db, PaymentMethodType.CASH, company_id)
    assert method is not None
    return method.id


def _sale(client: TestClient, actor: dict[str, str], db: Session, slug: str, store_id: int, product_id: int, qty: str) -> dict:
    """``actor`` must be a Cashier (or the legacy admin) — the only identity
    that can record a sale under the ERP role redesign."""
    company_id = _company_id(db, slug)
    cash_id = _cash_method_id(db, company_id)
    resp = client.post(
        "/api/v1/sales",
        headers=actor,
        json={
            "store_id": store_id,
            "items": [{"product_id": product_id, "quantity": qty}],
            "payments": [{"payment_method_id": cash_id, "amount": str(float(qty) * 15)}],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Shape / scope
# ---------------------------------------------------------------------------
def test_ceo_scope_is_company(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "dash-a")
    resp = client.get("/api/v1/dashboard", headers=ceo)
    assert resp.status_code == 200, resp.text
    assert resp.json()["scope"] == "company"


def test_seller_scope_is_store(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "dash-b")
    store_id = _store(client, ceo)
    seller = _seller(client, ceo, "dash-b", "seller-dash-b", store_id)
    resp = client.get("/api/v1/dashboard", headers=seller)
    assert resp.status_code == 200, resp.text
    assert resp.json()["scope"] == "store"


def test_super_admin_no_access(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-dash-c")
    sa = _bearer(client, "root-dash-c", "Root12345!")
    assert client.get("/api/v1/dashboard", headers=sa).status_code == 403


# ---------------------------------------------------------------------------
# Aggregation correctness + tenant isolation
# ---------------------------------------------------------------------------
def test_ceo_aggregates_company_wide_across_stores(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "dash-d")
    store_a = _store(client, ceo, "Store A")
    store_b = _store(client, ceo, "Store B")
    product_id = _product(client, ceo, "SKU-DASH-D")
    warehouse = _warehouse(client, ceo, "dash-d", "wh-dash-d")
    for store_id in (store_a, store_b):
        _stock_in(client, warehouse, store_id, product_id)
    cashier_a = _seller(client, ceo, "dash-d", "cashier-dash-d-a", store_a)
    cashier_b = _seller(client, ceo, "dash-d", "cashier-dash-d-b", store_b)
    _sale(client, cashier_a, db_session, "dash-d", store_a, product_id, "2")
    _sale(client, cashier_b, db_session, "dash-d", store_b, product_id, "3")

    stats = client.get("/api/v1/dashboard", headers=ceo).json()
    assert stats["today_sales_count"] == 2
    assert float(stats["today_sales_total"]) == 75.0  # (2+3)*15


def test_seller_sees_only_own_store(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "dash-e")
    own = _store(client, ceo, "Own Store")
    other = _store(client, ceo, "Other Store")
    product_id = _product(client, ceo, "SKU-DASH-E")
    warehouse = _warehouse(client, ceo, "dash-e", "wh-dash-e")
    for store_id in (own, other):
        _stock_in(client, warehouse, store_id, product_id)
    seller = _seller(client, ceo, "dash-e", "seller-dash-e", own)
    cashier_other = _seller(client, ceo, "dash-e", "cashier-dash-e-other", other)
    _sale(client, seller, db_session, "dash-e", own, product_id, "2")
    _sale(client, cashier_other, db_session, "dash-e", other, product_id, "5")

    stats = client.get("/api/v1/dashboard", headers=seller).json()
    assert stats["today_sales_count"] == 1
    assert float(stats["today_sales_total"]) == 30.0  # 2*15


def test_cross_company_isolation(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "dash-f1")
    ceo_b = _onboard(client, db_session, "dash-f2")
    store_b = _store(client, ceo_b)
    product_b = _product(client, ceo_b, "SKU-DASH-F")
    warehouse_b = _warehouse(client, ceo_b, "dash-f2", "wh-dash-f2")
    _stock_in(client, warehouse_b, store_b, product_b)
    cashier_b = _seller(client, ceo_b, "dash-f2", "cashier-dash-f2", store_b)
    _sale(client, cashier_b, db_session, "dash-f2", store_b, product_b, "1")

    stats_a = client.get("/api/v1/dashboard", headers=ceo_a).json()
    assert stats_a["today_sales_count"] == 0
    assert float(stats_a["today_sales_total"]) == 0.0


def test_month_expenses_uses_expense_module(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "dash-g")
    store_id = _store(client, ceo)
    client.post("/api/v1/expenses", headers=ceo, json={"store_id": store_id, "expense_type": "fuel", "amount": "12345.00", "description": "Yoqilg'i"})

    stats = client.get("/api/v1/dashboard", headers=ceo).json()
    assert float(stats["month_expenses"]) == 12345.0


def test_top_debtors_and_debtor_totals(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "dash-h")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-DASH-H")
    warehouse = _warehouse(client, ceo, "dash-h", "wh-dash-h")
    _stock_in(client, warehouse, store_id, product_id)
    customer_id = client.post("/api/v1/customers", headers=ceo, json={"full_name": "Qarzdor", "customer_type": "individual"}).json()["id"]
    company_id = _company_id(db_session, "dash-h")
    cash_id = _cash_method_id(db_session, company_id)
    cashier = _seller(client, ceo, "dash-h", "cashier-dash-h", store_id)
    client.post(
        "/api/v1/sales",
        headers=cashier,
        json={
            "store_id": store_id,
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": "10"}],
            "payments": [{"payment_method_id": cash_id, "amount": "100.00"}],  # 150 total -> 50 debt
        },
    )

    stats = client.get("/api/v1/dashboard", headers=ceo).json()
    assert stats["debtors_count"] == 1
    assert float(stats["debtors_total"]) == 50.0
    assert len(stats["top_debtors"]) == 1
    assert stats["top_debtors"][0]["customer_id"] == customer_id
    assert float(stats["top_debtors"][0]["remaining"]) == 50.0


def test_recent_operations_and_top_products_shape(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "dash-i")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-DASH-I")
    warehouse = _warehouse(client, ceo, "dash-i", "wh-dash-i")
    _stock_in(client, warehouse, store_id, product_id)
    cashier = _seller(client, ceo, "dash-i", "cashier-dash-i", store_id)
    _sale(client, cashier, db_session, "dash-i", store_id, product_id, "4")

    stats = client.get("/api/v1/dashboard", headers=ceo).json()
    types = {op["type"] for op in stats["recent_operations"]}
    assert types == {"stock_in", "sale"}
    assert len(stats["top_products"]) == 1
    assert stats["top_products"][0]["product_id"] == product_id
    assert float(stats["top_products"][0]["quantity_sold"]) == 4.0
    assert len(stats["sales_chart"]) == 7
