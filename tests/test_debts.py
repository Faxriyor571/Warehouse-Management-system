"""Tests for the migrated Debts module (Phase 11, API_SPECIFICATION.md §11).

Company/store scoped like Sales/Stock In: Seller confined to own store, CEO
company-wide (may filter by store_id), legacy admin transitional. Debts are
only created automatically via Sales in the tenant path; standalone
POST /debts remains legacy-admin-only (not in the API spec).
"""
from __future__ import annotations

from datetime import date

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


def _stock_in(client: TestClient, warehouse: dict[str, str], store_id: int, product_id: int, qty: str = "100") -> None:
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


def _customer(client: TestClient, ceo: dict[str, str], full_name: str) -> int:
    resp = client.post("/api/v1/customers", headers=ceo, json={"full_name": full_name, "customer_type": "individual"})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _debt_sale(
    client: TestClient, actor: dict[str, str], db: Session, slug: str, store_id: int, product_id: int, customer_id: int
) -> dict:
    """A sale that leaves a 50 remaining debt (150 total, 100 paid). ``actor``
    must be a Cashier (or the legacy admin) — the only identity that can
    record a sale under the ERP role redesign."""
    company_id = _company_id(db, slug)
    cash_id = _cash_method_id(db, company_id)
    resp = client.post(
        "/api/v1/sales",
        headers=actor,
        json={
            "store_id": store_id,
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": "10"}],
            "payments": [{"payment_method_id": cash_id, "amount": "100.00"}],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _debt_for_sale(client: TestClient, ceo: dict[str, str], sale_id: int) -> dict:
    listed = client.get("/api/v1/debts", headers=ceo).json()["items"]
    return next(d for d in listed if d["stock_out_id"] == sale_id)


# ---------------------------------------------------------------------------
# Listing / detail / scoping
# ---------------------------------------------------------------------------
def test_debt_created_by_sale_is_scoped(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "db-a")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-DBA")
    warehouse = _warehouse(client, ceo, "db-a", "wh-db-a")
    _stock_in(client, warehouse, store_id, product_id)
    customer_id = _customer(client, ceo, "Ali")
    cashier = _seller(client, ceo, "db-a", "cashier-db-a", store_id)
    sale = _debt_sale(client, cashier, db_session, "db-a", store_id, product_id, customer_id)

    debt = _debt_for_sale(client, ceo, sale["id"])
    assert float(debt["remaining_amount"]) == 50.0
    assert debt["status"] == "active"
    assert debt["store_id"] == store_id


def test_detail_includes_payment_history(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "db-b")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-DBB")
    warehouse = _warehouse(client, ceo, "db-b", "wh-db-b")
    _stock_in(client, warehouse, store_id, product_id)
    customer_id = _customer(client, ceo, "Vali")
    cashier = _seller(client, ceo, "db-b", "cashier-db-b", store_id)
    sale = _debt_sale(client, cashier, db_session, "db-b", store_id, product_id, customer_id)
    debt = _debt_for_sale(client, ceo, sale["id"])

    detail = client.get(f"/api/v1/debts/{debt['id']}", headers=ceo).json()
    assert detail["payments"] == []


def test_seller_confined_to_own_store(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "db-c")
    own = _store(client, ceo, "Own Store")
    other = _store(client, ceo, "Other Store")
    product_id = _product(client, ceo, "SKU-DBC")
    warehouse = _warehouse(client, ceo, "db-c", "wh-db-c")
    _stock_in(client, warehouse, own, product_id)
    _stock_in(client, warehouse, other, product_id)
    customer_id = _customer(client, ceo, "Mijoz")
    seller = _seller(client, ceo, "db-c", "seller-db-c", own)
    cashier_other = _seller(client, ceo, "db-c", "cashier-db-c-other", other)
    sale_own = _debt_sale(client, seller, db_session, "db-c", own, product_id, customer_id)
    sale_other = _debt_sale(client, cashier_other, db_session, "db-c", other, product_id, customer_id)

    listed = client.get("/api/v1/debts", headers=seller).json()
    stock_out_ids = {d["stock_out_id"] for d in listed["items"]}
    assert sale_own["id"] in stock_out_ids
    assert sale_other["id"] not in stock_out_ids

    debt_other = _debt_for_sale(client, ceo, sale_other["id"])
    assert client.get(f"/api/v1/debts/{debt_other['id']}", headers=seller).status_code == 404


def test_ceo_filters_by_store_id(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "db-d")
    store_a = _store(client, ceo, "Store A")
    store_b = _store(client, ceo, "Store B")
    product_id = _product(client, ceo, "SKU-DBD")
    warehouse = _warehouse(client, ceo, "db-d", "wh-db-d")
    _stock_in(client, warehouse, store_a, product_id)
    _stock_in(client, warehouse, store_b, product_id)
    customer_id = _customer(client, ceo, "Mijoz")
    cashier_a = _seller(client, ceo, "db-d", "cashier-db-d-a", store_a)
    cashier_b = _seller(client, ceo, "db-d", "cashier-db-d-b", store_b)
    sale_a = _debt_sale(client, cashier_a, db_session, "db-d", store_a, product_id, customer_id)
    _debt_sale(client, cashier_b, db_session, "db-d", store_b, product_id, customer_id)

    listed = client.get(f"/api/v1/debts?store_id={store_a}", headers=ceo).json()
    assert all(d["store_id"] == store_a for d in listed["items"])
    assert any(d["stock_out_id"] == sale_a["id"] for d in listed["items"])


def test_cross_company_detail_404(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "db-e1")
    ceo_b = _onboard(client, db_session, "db-e2")
    store_b = _store(client, ceo_b)
    product_b = _product(client, ceo_b, "SKU-DBE")
    warehouse_b = _warehouse(client, ceo_b, "db-e2", "wh-db-e2")
    _stock_in(client, warehouse_b, store_b, product_b)
    customer_b = _customer(client, ceo_b, "Boshqa mijoz")
    cashier_b = _seller(client, ceo_b, "db-e2", "cashier-db-e2", store_b)
    sale_b = _debt_sale(client, cashier_b, db_session, "db-e2", store_b, product_b, customer_b)
    debt_b = _debt_for_sale(client, ceo_b, sale_b["id"])

    assert client.get(f"/api/v1/debts/{debt_b['id']}", headers=ceo_a).status_code == 404


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
def test_super_admin_no_access(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-db-f")
    sa = _bearer(client, "root-db-f", "Root12345!")
    assert client.get("/api/v1/debts", headers=sa).status_code == 403


def test_tenant_cannot_use_standalone_create(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "db-g")
    customer_id = _customer(client, ceo, "Mijoz")
    resp = client.post(
        "/api/v1/debts", headers=ceo, json={"customer_id": customer_id, "amount": "10.00"}
    )
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# Payments: remaining balance, status transitions, tenant-scoped payment method
# ---------------------------------------------------------------------------
def test_payment_reduces_balance_and_marks_paid(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "db-h")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-DBH")
    warehouse = _warehouse(client, ceo, "db-h", "wh-db-h")
    _stock_in(client, warehouse, store_id, product_id)
    customer_id = _customer(client, ceo, "Mijoz")
    cashier = _seller(client, ceo, "db-h", "cashier-db-h", store_id)
    sale = _debt_sale(client, cashier, db_session, "db-h", store_id, product_id, customer_id)
    debt = _debt_for_sale(client, ceo, sale["id"])
    company_id = _company_id(db_session, "db-h")
    cash_id = _cash_method_id(db_session, company_id)

    resp = client.post(
        f"/api/v1/debts/{debt['id']}/payments", headers=ceo, json={"payment_method_id": cash_id, "amount": "50.00"}
    )
    assert resp.status_code == 201, resp.text

    updated = client.get(f"/api/v1/debts/{debt['id']}", headers=ceo).json()
    assert float(updated["remaining_amount"]) == 0.0
    assert updated["status"] == "paid"
    assert len(updated["payments"]) == 1

    sale_after = client.get(f"/api/v1/sales/{sale['id']}", headers=ceo).json()
    assert sale_after["payment_status"] == "paid"


def test_payment_exceeding_remaining_rejected(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "db-i")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-DBI")
    warehouse = _warehouse(client, ceo, "db-i", "wh-db-i")
    _stock_in(client, warehouse, store_id, product_id)
    customer_id = _customer(client, ceo, "Mijoz")
    cashier = _seller(client, ceo, "db-i", "cashier-db-i", store_id)
    sale = _debt_sale(client, cashier, db_session, "db-i", store_id, product_id, customer_id)
    debt = _debt_for_sale(client, ceo, sale["id"])
    company_id = _company_id(db_session, "db-i")
    cash_id = _cash_method_id(db_session, company_id)

    resp = client.post(
        f"/api/v1/debts/{debt['id']}/payments", headers=ceo, json={"payment_method_id": cash_id, "amount": "999.00"}
    )
    assert resp.status_code == 422, resp.text


def test_payment_rejects_foreign_company_payment_method(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "db-j1")
    ceo_b = _onboard(client, db_session, "db-j2")
    store_a = _store(client, ceo_a)
    product_a = _product(client, ceo_a, "SKU-DBJ")
    warehouse_a = _warehouse(client, ceo_a, "db-j1", "wh-db-j1")
    _stock_in(client, warehouse_a, store_a, product_a)
    customer_a = _customer(client, ceo_a, "Mijoz")
    cashier_a = _seller(client, ceo_a, "db-j1", "cashier-db-j1", store_a)
    sale_a = _debt_sale(client, cashier_a, db_session, "db-j1", store_a, product_a, customer_a)
    debt_a = _debt_for_sale(client, ceo_a, sale_a["id"])

    company_b = _company_id(db_session, "db-j2")
    cash_b = _cash_method_id(db_session, company_b)

    resp = client.post(
        f"/api/v1/debts/{debt_a['id']}/payments", headers=ceo_a, json={"payment_method_id": cash_b, "amount": "10.00"}
    )
    assert resp.status_code == 404, resp.text


def test_seller_cannot_pay_debt_of_other_store(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "db-k")
    own = _store(client, ceo, "Own Store")
    other = _store(client, ceo, "Other Store")
    product_id = _product(client, ceo, "SKU-DBK")
    warehouse = _warehouse(client, ceo, "db-k", "wh-db-k")
    _stock_in(client, warehouse, other, product_id)
    customer_id = _customer(client, ceo, "Mijoz")
    cashier_other = _seller(client, ceo, "db-k", "cashier-db-k-other", other)
    sale_other = _debt_sale(client, cashier_other, db_session, "db-k", other, product_id, customer_id)
    debt_other = _debt_for_sale(client, ceo, sale_other["id"])
    seller = _seller(client, ceo, "db-k", "seller-db-k", own)
    company_id = _company_id(db_session, "db-k")
    cash_id = _cash_method_id(db_session, company_id)

    resp = client.post(
        f"/api/v1/debts/{debt_other['id']}/payments", headers=seller, json={"payment_method_id": cash_id, "amount": "10.00"}
    )
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Due date
# ---------------------------------------------------------------------------
def test_update_due_date_recomputes_overdue_status(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "db-l")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-DBL")
    warehouse = _warehouse(client, ceo, "db-l", "wh-db-l")
    _stock_in(client, warehouse, store_id, product_id)
    customer_id = _customer(client, ceo, "Mijoz")
    cashier = _seller(client, ceo, "db-l", "cashier-db-l", store_id)
    sale = _debt_sale(client, cashier, db_session, "db-l", store_id, product_id, customer_id)
    debt = _debt_for_sale(client, ceo, sale["id"])

    resp = client.put(f"/api/v1/debts/{debt['id']}/due-date", headers=ceo, json={"due_date": "2020-01-01"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "overdue"
    assert resp.json()["due_date"] == "2020-01-01"


def test_stale_status_is_self_healed_on_read(client: TestClient, db_session: Session) -> None:
    """A debt whose due date silently passes (no payment, no due-date edit)
    must still surface as overdue the next time it's read — not stay
    "active" forever because nothing happened to touch it. Simulated by
    writing a past due_date directly to the DB (bypassing the status
    recompute that a real API call would trigger), then confirming both
    GET /debts and GET /reports/debts self-heal the stale status."""
    ceo = _onboard(client, db_session, "db-m")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-DBM")
    warehouse = _warehouse(client, ceo, "db-m", "wh-db-m")
    _stock_in(client, warehouse, store_id, product_id)
    customer_id = _customer(client, ceo, "Mijoz")
    cashier = _seller(client, ceo, "db-m", "cashier-db-m", store_id)
    sale = _debt_sale(client, cashier, db_session, "db-m", store_id, product_id, customer_id)
    debt = _debt_for_sale(client, ceo, sale["id"])

    from app.crud.debt import debt as debt_crud

    row = debt_crud.get(db_session, debt["id"])
    assert row is not None
    row.due_date = date(2020, 1, 1)
    db_session.add(row)
    db_session.commit()
    assert row.status.value == "active"  # still stale in the DB at this point

    listed = client.get("/api/v1/debts", headers=ceo).json()["items"]
    healed = next(d for d in listed if d["id"] == debt["id"])
    assert healed["status"] == "overdue"

    report = client.get("/api/v1/reports/debts", headers=ceo).json()
    overdue_bucket = next((b for b in report["by_status"] if b["status"] == "overdue"), None)
    assert overdue_bucket is not None and overdue_bucket["count"] >= 1


def test_refresh_overdue_respects_company_scope(client: TestClient, db_session: Session) -> None:
    """Reading company A's debts must not leak into flipping company B's
    stale debts, and vice versa — the bulk UPDATE has to stay tenant-scoped."""
    ceo_a = _onboard(client, db_session, "db-n1")
    store_a = _store(client, ceo_a)
    product_a = _product(client, ceo_a, "SKU-DBN1")
    warehouse_a = _warehouse(client, ceo_a, "db-n1", "wh-db-n1")
    _stock_in(client, warehouse_a, store_a, product_a)
    customer_a = _customer(client, ceo_a, "Mijoz A")
    cashier_a = _seller(client, ceo_a, "db-n1", "cashier-db-n1", store_a)
    sale_a = _debt_sale(client, cashier_a, db_session, "db-n1", store_a, product_a, customer_a)
    debt_a = _debt_for_sale(client, ceo_a, sale_a["id"])

    ceo_b = _onboard(client, db_session, "db-n2")
    store_b = _store(client, ceo_b)
    product_b = _product(client, ceo_b, "SKU-DBN2")
    warehouse_b = _warehouse(client, ceo_b, "db-n2", "wh-db-n2")
    _stock_in(client, warehouse_b, store_b, product_b)
    customer_b = _customer(client, ceo_b, "Mijoz B")
    cashier_b = _seller(client, ceo_b, "db-n2", "cashier-db-n2", store_b)
    sale_b = _debt_sale(client, cashier_b, db_session, "db-n2", store_b, product_b, customer_b)
    debt_b = _debt_for_sale(client, ceo_b, sale_b["id"])

    from app.crud.debt import debt as debt_crud

    for debt in (debt_a, debt_b):
        row = debt_crud.get(db_session, debt["id"])
        assert row is not None
        row.due_date = date(2020, 1, 1)
        db_session.add(row)
    db_session.commit()

    # Reading company A's debts flips only A's stale debt. Each client.get()
    # runs against its own DB session (see conftest's per-request override),
    # so db_session's identity-map cache must be expired to see those writes.
    client.get("/api/v1/debts", headers=ceo_a)
    db_session.expire_all()
    assert debt_crud.get(db_session, debt_a["id"]).status.value == "overdue"
    assert debt_crud.get(db_session, debt_b["id"]).status.value == "active"

    # Reading company B's debts now flips B's too.
    client.get("/api/v1/debts", headers=ceo_b)
    db_session.expire_all()
    assert debt_crud.get(db_session, debt_b["id"]).status.value == "overdue"
