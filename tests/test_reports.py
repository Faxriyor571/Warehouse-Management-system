"""Tests for the migrated Reports module (Phase 14, API_SPECIFICATION.md §14).

JSON only, 4 report types (sales, inventory, debts, expenses). Company/store
scoped: Seller own store, CEO company-wide or one store via store_id, legacy
admin transitional, Super Admin no access.
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
        json={
            "username": username,
            "full_name": "Warehouse",
            "password": "Wh12345!",
            "employee_role": "warehouse",
        },
    )
    assert resp.status_code == 201, resp.text
    return _bearer(client, username, "Wh12345!", company_slug=slug)


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


def _stock_in(client: TestClient, ceo: dict[str, str], store_id: int, product_id: int, qty: str) -> None:
    assert client.post("/api/v1/stock-in", headers=ceo, json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": qty, "price": "10.00"}]}).status_code == 201


def _sale(client, ceo, db, slug, store_id, product_id, qty, customer_id=None, paid=None):
    company_id = _company_id(db, slug)
    cash_id = _cash_method_id(db, company_id)
    amount = paid if paid is not None else str(float(qty) * 15)
    body = {
        "store_id": store_id,
        "items": [{"product_id": product_id, "quantity": qty}],
        "payments": [{"payment_method_id": cash_id, "amount": amount}],
    }
    if customer_id is not None:
        body["customer_id"] = customer_id
    resp = client.post("/api/v1/sales", headers=ceo, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Sales report
# ---------------------------------------------------------------------------
def test_sales_report_totals_and_status_breakdown(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "rp-a")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-RPA")
    warehouse = _warehouse(client, ceo, "rp-a", "wh-rp-a")
    _stock_in(client, warehouse, store_id, product_id, "100")
    customer_id = client.post("/api/v1/customers", headers=ceo, json={"full_name": "Mijoz", "customer_type": "individual"}).json()["id"]
    cashier = _seller(client, ceo, "rp-a", "cashier-rp-a", store_id)
    _sale(client, cashier, db_session, "rp-a", store_id, product_id, "2")  # paid 30
    _sale(client, cashier, db_session, "rp-a", store_id, product_id, "10", customer_id=customer_id, paid="100.00")  # partial (150/100)

    rep = client.get("/api/v1/reports/sales", headers=ceo).json()
    assert rep["total_count"] == 2
    assert float(rep["total_revenue"]) == 180.0
    statuses = {b["status"]: b for b in rep["by_payment_status"]}
    assert statuses["paid"]["count"] == 1
    assert statuses["partial"]["count"] == 1
    assert len(rep["by_day"]) >= 1


def test_cashier_has_no_sales_report_access(client: TestClient, db_session: Session) -> None:
    """Reports is CEO-only under the ERP role redesign — a Cashier records
    sales but does not see the Sales report (not in Perm.REPORTS_SALES'
    grantees)."""
    ceo = _onboard(client, db_session, "rp-b")
    own = _store(client, ceo, "Own Store")
    cashier = _seller(client, ceo, "rp-b", "cashier-rp-b", own)

    assert client.get("/api/v1/reports/sales", headers=cashier).status_code == 403


def test_sales_report_ceo_store_filter_and_date_range(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "rp-c")
    store_a = _store(client, ceo, "Store A")
    store_b = _store(client, ceo, "Store B")
    product_id = _product(client, ceo, "SKU-RPC")
    warehouse = _warehouse(client, ceo, "rp-c", "wh-rp-c")
    _stock_in(client, warehouse, store_a, product_id, "100")
    _stock_in(client, warehouse, store_b, product_id, "100")
    cashier_a = _seller(client, ceo, "rp-c", "cashier-rp-c-a", store_a)
    cashier_b = _seller(client, ceo, "rp-c", "cashier-rp-c-b", store_b)
    _sale(client, cashier_a, db_session, "rp-c", store_a, product_id, "2")
    _sale(client, cashier_b, db_session, "rp-c", store_b, product_id, "3")

    rep = client.get(f"/api/v1/reports/sales?store_id={store_a}", headers=ceo).json()
    assert rep["total_count"] == 1

    # A date window in the far past excludes today's sales.
    rep2 = client.get("/api/v1/reports/sales?date_from=2000-01-01&date_to=2000-01-02", headers=ceo).json()
    assert rep2["total_count"] == 0


# ---------------------------------------------------------------------------
# Inventory report
# ---------------------------------------------------------------------------
def test_inventory_report_reflects_store_stock(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "rp-d")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-RPD")
    warehouse = _warehouse(client, ceo, "rp-d", "wh-rp-d")
    _stock_in(client, warehouse, store_id, product_id, "40")

    rep = client.get("/api/v1/reports/inventory", headers=ceo).json()
    assert rep["count"] == 1
    row = rep["rows"][0]
    assert row["product_id"] == product_id
    assert float(row["quantity"]) == 40.0


def test_warehouse_has_no_inventory_report_access(client: TestClient, db_session: Session) -> None:
    """Reports is CEO-only under the ERP role redesign — a Warehouse
    Employee moves stock but does not see the Inventory report (not in
    Perm.REPORTS_INVENTORY's grantees; they see stock levels via the
    Inventory module itself, a separate permission)."""
    ceo = _onboard(client, db_session, "rp-e")
    warehouse = _warehouse(client, ceo, "rp-e", "wh-rp-e")

    assert client.get("/api/v1/reports/inventory", headers=warehouse).status_code == 403


# ---------------------------------------------------------------------------
# Debts report
# ---------------------------------------------------------------------------
def test_debt_report_groups_by_customer_and_status(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "rp-f")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-RPF")
    warehouse = _warehouse(client, ceo, "rp-f", "wh-rp-f")
    _stock_in(client, warehouse, store_id, product_id, "100")
    customer_id = client.post("/api/v1/customers", headers=ceo, json={"full_name": "Qarzdor", "customer_type": "individual"}).json()["id"]
    cashier = _seller(client, ceo, "rp-f", "cashier-rp-f", store_id)
    _sale(client, cashier, db_session, "rp-f", store_id, product_id, "10", customer_id=customer_id, paid="100.00")  # 50 debt

    rep = client.get("/api/v1/reports/debts", headers=ceo).json()
    assert float(rep["total_remaining"]) == 50.0
    assert len(rep["by_customer"]) == 1
    assert rep["by_customer"][0]["customer_id"] == customer_id
    statuses = {b["status"] for b in rep["by_status"]}
    assert "active" in statuses


# ---------------------------------------------------------------------------
# Expenses report
# ---------------------------------------------------------------------------
def test_expense_report_groups_by_type_and_date(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "rp-g")
    store_id = _store(client, ceo)
    client.post("/api/v1/expenses", headers=ceo, json={"store_id": store_id, "expense_type": "fuel", "amount": "100.00", "description": "a"})
    client.post("/api/v1/expenses", headers=ceo, json={"store_id": store_id, "expense_type": "fuel", "amount": "50.00", "description": "b"})
    client.post("/api/v1/expenses", headers=ceo, json={"store_id": store_id, "expense_type": "driver", "amount": "25.00", "description": "c"})

    rep = client.get("/api/v1/reports/expenses", headers=ceo).json()
    assert float(rep["total"]) == 175.0
    by_type = {b["expense_type"]: b for b in rep["by_type"]}
    assert float(by_type["fuel"]["total"]) == 150.0
    assert by_type["fuel"]["count"] == 2
    assert float(by_type["driver"]["total"]) == 25.0
    assert len(rep["by_date"]) >= 1


# ---------------------------------------------------------------------------
# Authorization / isolation
# ---------------------------------------------------------------------------
def test_super_admin_no_access(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-rp-h")
    sa = _bearer(client, "root-rp-h", "Root12345!")
    for path in ("sales", "inventory", "debts", "expenses"):
        assert client.get(f"/api/v1/reports/{path}", headers=sa).status_code == 403


def test_cross_company_isolation(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "rp-i1")
    ceo_b = _onboard(client, db_session, "rp-i2")
    store_b = _store(client, ceo_b)
    product_b = _product(client, ceo_b, "SKU-RPI")
    warehouse_b = _warehouse(client, ceo_b, "rp-i2", "wh-rp-i2")
    _stock_in(client, warehouse_b, store_b, product_b, "50")
    cashier_b = _seller(client, ceo_b, "rp-i2", "cashier-rp-i2", store_b)
    _sale(client, cashier_b, db_session, "rp-i2", store_b, product_b, "1")

    rep_a = client.get("/api/v1/reports/sales", headers=ceo_a).json()
    assert rep_a["total_count"] == 0
    inv_a = client.get("/api/v1/reports/inventory", headers=ceo_a).json()
    assert inv_a["count"] == 0


def test_ceo_foreign_store_id_rejected(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "rp-j1")
    ceo_b = _onboard(client, db_session, "rp-j2")
    store_b = _store(client, ceo_b)
    assert client.get(f"/api/v1/reports/sales?store_id={store_b}", headers=ceo_a).status_code == 404
