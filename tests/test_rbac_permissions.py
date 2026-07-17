"""Tests for the ERP role redesign's permission engine (Phase 1).

Covers: CEO view-not-manage on Sales/Stock-In, each EmployeeRole's exact
allowed/denied permission set, the Employee-creation store_id relaxation for
company-wide job functions, and that the legacy admin is unaffected.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import security
from app.models.enums import UserRole
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


def _onboard(client: TestClient, db: Session, slug: str) -> tuple[dict[str, str], int]:
    """Create a company (+CEO) and return (CEO headers, company_id)."""
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
    resp = client.post("/api/v1/companies", headers=sa, json=payload)
    assert resp.status_code == 201, resp.text
    ceo = _bearer(client, f"ceo-{slug}", "Ceo12345!", company_slug=slug)
    return ceo, resp.json()["company"]["id"]


def _create_store(client: TestClient, ceo: dict[str, str], name: str = "Store") -> int:
    resp = client.post("/api/v1/stores", headers=ceo, json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_employee(
    client: TestClient,
    ceo: dict[str, str],
    username: str,
    employee_role: str,
    company_slug: str,
    store_id: int | None = None,
) -> dict[str, str]:
    body = {
        "username": username,
        "full_name": "Employee Person",
        "password": "Emp12345!",
        "email": None,
        "phone": None,
        "employee_role": employee_role,
    }
    if store_id is not None:
        body["store_id"] = store_id
    resp = client.post("/api/v1/employees", headers=ceo, json=body)
    assert resp.status_code == 201, resp.text
    return _bearer(client, username, "Emp12345!", company_slug=company_slug)


def _create_product(client: TestClient, ceo: dict[str, str]) -> int:
    cat = client.post("/api/v1/categories", headers=ceo, json={"name": "Cat"})
    assert cat.status_code == 201, cat.text
    unit = client.post("/api/v1/units", headers=ceo, json={"name": "Kilogramm", "short_name": "kg"})
    assert unit.status_code == 201, unit.text
    prod = client.post(
        "/api/v1/products",
        headers=ceo,
        json={
            "name": "Prod",
            "sku": "SKU1",
            "category_id": cat.json()["id"],
            "unit_id": unit.json()["id"],
            "purchase_price": "10.00",
            "sale_price": "15.00",
        },
    )
    assert prod.status_code == 201, prod.text
    return prod.json()["id"]


# ---------------------------------------------------------------------------
# Employee creation: store_id relaxation
# ---------------------------------------------------------------------------


def test_cashier_requires_store_id(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "rbac-cashier-req")
    resp = client.post(
        "/api/v1/employees",
        headers=ceo,
        json={
            "username": "cashier-nostore",
            "full_name": "Cashier",
            "password": "Emp12345!",
            "email": None,
            "phone": None,
            "employee_role": "cashier",
        },
    )
    assert resp.status_code == 422, resp.text


def test_warehouse_and_accountant_do_not_require_store_id(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "rbac-companywide")
    for role, username in [("warehouse", "wh-nostore"), ("accountant", "acc-nostore")]:
        resp = client.post(
            "/api/v1/employees",
            headers=ceo,
            json={
                "username": username,
                "full_name": "Employee",
                "password": "Emp12345!",
                "email": None,
                "phone": None,
                "employee_role": role,
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["store_id"] is None
        assert resp.json()["store_name"] is None
        assert resp.json()["employee_role"] == role


def test_cashier_with_store_id_succeeds(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "rbac-cashier-ok")
    store_id = _create_store(client, ceo)
    resp = client.post(
        "/api/v1/employees",
        headers=ceo,
        json={
            "username": "cashier-ok",
            "full_name": "Cashier",
            "password": "Emp12345!",
            "email": None,
            "phone": None,
            "employee_role": "cashier",
            "store_id": store_id,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["store_id"] == store_id
    assert resp.json()["employee_role"] == "cashier"


def test_employee_role_defaults_to_cashier(client: TestClient, db_session: Session) -> None:
    """Backward compatibility: omitting employee_role behaves like the old Seller model."""
    ceo, _ = _onboard(client, db_session, "rbac-default-role")
    store_id = _create_store(client, ceo)
    resp = client.post(
        "/api/v1/employees",
        headers=ceo,
        json={
            "username": "default-role",
            "full_name": "Seller",
            "password": "Emp12345!",
            "email": None,
            "phone": None,
            "store_id": store_id,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["employee_role"] == "cashier"


# ---------------------------------------------------------------------------
# CEO: view but not execute Sales / Stock In / Transfer-adjacent actions
# ---------------------------------------------------------------------------


def test_ceo_can_list_sales_but_not_create(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "rbac-ceo-sales")
    store_id = _create_store(client, ceo)
    product_id = _create_product(client, ceo)

    list_resp = client.get("/api/v1/sales", headers=ceo)
    assert list_resp.status_code == 200, list_resp.text

    create_resp = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": "1"}]},
    )
    assert create_resp.status_code == 403, create_resp.text


def test_ceo_can_list_stock_in_but_not_create(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "rbac-ceo-stockin")
    store_id = _create_store(client, ceo)
    product_id = _create_product(client, ceo)

    list_resp = client.get("/api/v1/stock-in", headers=ceo)
    assert list_resp.status_code == 200, list_resp.text

    create_resp = client.post(
        "/api/v1/stock-in",
        headers=ceo,
        json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": "10", "price": "5.00"}]},
    )
    assert create_resp.status_code == 403, create_resp.text


def test_ceo_can_view_reports_across_all_tabs(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "rbac-ceo-reports")
    for path in ("/api/v1/reports/sales", "/api/v1/reports/inventory", "/api/v1/reports/debts", "/api/v1/reports/expenses"):
        resp = client.get(path, headers=ceo)
        assert resp.status_code == 200, f"{path}: {resp.text}"


# ---------------------------------------------------------------------------
# Cashier: sell, manage debts, view products — nothing else
# ---------------------------------------------------------------------------


def test_cashier_can_sell_but_not_receive_inventory(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "rbac-cashier-perms")
    store_id = _create_store(client, ceo)
    product_id = _create_product(client, ceo)
    cashier = _create_employee(client, ceo, "cashier-perms", "cashier", "rbac-cashier-perms", store_id=store_id)

    sale_resp = client.post(
        "/api/v1/sales",
        headers=cashier,
        json={"items": [{"product_id": product_id, "quantity": "1"}], "payments": []},
    )
    assert sale_resp.status_code in (201, 422), sale_resp.text  # 422 only if a debt requires a customer

    stock_in_resp = client.post(
        "/api/v1/stock-in",
        headers=cashier,
        json={"items": [{"product_id": product_id, "quantity": "10", "price": "5.00"}]},
    )
    assert stock_in_resp.status_code == 403, stock_in_resp.text


def test_cashier_has_no_reports_or_expenses_access(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "rbac-cashier-denied")
    store_id = _create_store(client, ceo)
    cashier = _create_employee(client, ceo, "cashier-denied", "cashier", "rbac-cashier-denied", store_id=store_id)

    assert client.get("/api/v1/reports/sales", headers=cashier).status_code == 403
    assert client.get("/api/v1/expenses", headers=cashier).status_code == 403
    assert client.get("/api/v1/employees", headers=cashier).status_code == 403
    # A Cashier CAN read categories (embedded dependency of browsing/selling
    # products), but cannot manage the Categories module itself (CEO-only).
    assert client.get("/api/v1/categories", headers=cashier).status_code == 200
    assert client.post("/api/v1/categories", headers=cashier, json={"name": "New Cat"}).status_code == 403


# ---------------------------------------------------------------------------
# Warehouse Employee: receive/transfer inventory, view products — nothing else
# ---------------------------------------------------------------------------


def test_warehouse_can_receive_but_not_sell(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "rbac-warehouse-perms")
    store_id = _create_store(client, ceo)
    product_id = _create_product(client, ceo)
    warehouse = _create_employee(client, ceo, "warehouse-perms", "warehouse", "rbac-warehouse-perms")

    stock_in_resp = client.post(
        "/api/v1/stock-in",
        headers=warehouse,
        json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": "10", "price": "5.00"}]},
    )
    assert stock_in_resp.status_code == 201, stock_in_resp.text

    sale_resp = client.post(
        "/api/v1/sales",
        headers=warehouse,
        json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": "1"}]},
    )
    assert sale_resp.status_code == 403, sale_resp.text


def test_warehouse_has_no_expenses_or_settings_access(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "rbac-warehouse-denied")
    warehouse = _create_employee(client, ceo, "warehouse-denied", "warehouse", "rbac-warehouse-denied")

    assert client.get("/api/v1/expenses", headers=warehouse).status_code == 403
    assert client.get("/api/v1/settings", headers=warehouse).status_code == 403
    assert client.get("/api/v1/sales", headers=warehouse).status_code == 403


# ---------------------------------------------------------------------------
# Accountant: finances only — nothing operational
# ---------------------------------------------------------------------------


def test_accountant_can_manage_expenses_but_not_sales_or_products(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "rbac-accountant-perms")
    store_id = _create_store(client, ceo)
    accountant = _create_employee(client, ceo, "accountant-perms", "accountant", "rbac-accountant-perms")

    # Accountant is company-wide (like CEO), so — same as CEO — a store_id
    # must be supplied when recording an expense (existing pre-redesign rule,
    # unchanged; not a store-confinement of the Accountant's own scope).
    expense_resp = client.post(
        "/api/v1/expenses",
        headers=accountant,
        json={"expense_type": "fuel", "amount": "20.00", "description": "Fuel", "store_id": store_id},
    )
    assert expense_resp.status_code == 201, expense_resp.text

    assert client.get("/api/v1/reports/expenses", headers=accountant).status_code == 200
    assert client.get("/api/v1/reports/debts", headers=accountant).status_code == 200
    assert client.get("/api/v1/sales", headers=accountant).status_code == 403
    assert client.get("/api/v1/products", headers=accountant).status_code == 403
    assert client.get("/api/v1/categories", headers=accountant).status_code == 403
    assert client.post("/api/v1/stores", headers=accountant, json={"name": "X"}).status_code == 403


def test_accountant_has_no_reports_sales_or_inventory_tab(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "rbac-accountant-tabs")
    accountant = _create_employee(client, ceo, "accountant-tabs", "accountant", "rbac-accountant-tabs")

    assert client.get("/api/v1/reports/sales", headers=accountant).status_code == 403
    assert client.get("/api/v1/reports/inventory", headers=accountant).status_code == 403


# ---------------------------------------------------------------------------
# Legacy admin: unaffected (is_superuser bypass preserved)
# ---------------------------------------------------------------------------


def test_legacy_admin_still_has_full_access(client: TestClient, auth_headers: dict[str, str]) -> None:
    """``auth_headers`` (conftest.py) is the legacy single-tenant admin."""
    for path in ("/api/v1/sales", "/api/v1/stock-in", "/api/v1/expenses", "/api/v1/reports/sales"):
        resp = client.get(path, headers=auth_headers)
        assert resp.status_code == 200, f"{path}: {resp.text}"
