"""Tests for the migrated Payment Methods module (Phase 10).

Company-scoped (DATABASE_DESIGN.md §3.18/§6): every company gets its own 5
system methods seeded at onboarding. CEO manages (create/update/delete);
Seller has read-only access (needed to pick a method at sale time). System
methods (``is_system=True``) can be neither deleted nor deactivated. Super
Admin has no access (mirrors Settings — company business data).
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


def _warehouse(client: TestClient, ceo: dict[str, str], slug: str, username: str) -> dict[str, str]:
    resp = client.post(
        "/api/v1/employees",
        headers=ceo,
        json={"username": username, "full_name": "Warehouse", "password": "Wh12345!", "employee_role": "warehouse"},
    )
    assert resp.status_code == 201, resp.text
    return _bearer(client, username, "Wh12345!", company_slug=slug)


def _cashier(client: TestClient, ceo: dict[str, str], slug: str, username: str, store_id: int) -> dict[str, str]:
    resp = client.post(
        "/api/v1/employees",
        headers=ceo,
        json={"username": username, "full_name": "Cashier", "password": "Cash12345!", "store_id": store_id},
    )
    assert resp.status_code == 201, resp.text
    return _bearer(client, username, "Cash12345!", company_slug=slug)


def _seller(client: TestClient, ceo: dict[str, str], slug: str, username: str, store_id: int) -> dict[str, str]:
    resp = client.post(
        "/api/v1/employees",
        headers=ceo,
        json={"username": username, "full_name": "Seller", "password": "Sell12345!", "store_id": store_id},
    )
    assert resp.status_code == 201, resp.text
    return _bearer(client, username, "Sell12345!", company_slug=slug)


# ---------------------------------------------------------------------------
# Onboarding seeds a fresh, isolated set per company
# ---------------------------------------------------------------------------
def test_onboarding_seeds_five_system_methods(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "pm-a")
    methods = client.get("/api/v1/payment-methods", headers=ceo).json()
    assert len(methods) == 5
    assert all(m["is_system"] for m in methods)
    names = {m["name"] for m in methods}
    assert names == {"Naqd", "Click", "Payme", "Bank", "Qarz"}


def test_two_companies_have_independent_method_sets(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "pm-b1")
    ceo_b = _onboard(client, db_session, "pm-b2")

    created = client.post(
        "/api/v1/payment-methods", headers=ceo_a, json={"name": "Naqd", "type": "cash"}
    )
    # "Naqd" already exists as a-company's own system default -> conflict...
    assert created.status_code == 409, created.text

    # ...but the same name is free for company B's own custom addition attempt
    # only insofar as it collides with company B's own seeded default too.
    other = client.post(
        "/api/v1/payment-methods", headers=ceo_b, json={"name": "Naqd Ikkinchi", "type": "cash"}
    )
    assert other.status_code == 201, other.text

    ids_a = {m["id"] for m in client.get("/api/v1/payment-methods", headers=ceo_a).json()}
    ids_b = {m["id"] for m in client.get("/api/v1/payment-methods", headers=ceo_b).json()}
    assert ids_a.isdisjoint(ids_b)


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
def test_seller_read_only(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "pm-c")
    store_id = _store(client, ceo)
    seller = _seller(client, ceo, "pm-c", "seller-pm-c", store_id)

    assert client.get("/api/v1/payment-methods", headers=seller).status_code == 200
    resp = client.post("/api/v1/payment-methods", headers=seller, json={"name": "Custom", "type": "cash"})
    assert resp.status_code == 403, resp.text


def test_super_admin_no_access(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-pm-d")
    sa = _bearer(client, "root-pm-d", "Root12345!")
    assert client.get("/api/v1/payment-methods", headers=sa).status_code == 403


def test_cross_company_update_404(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "pm-e1")
    ceo_b = _onboard(client, db_session, "pm-e2")
    method_b = client.get("/api/v1/payment-methods", headers=ceo_b).json()[0]

    resp = client.put(
        f"/api/v1/payment-methods/{method_b['id']}", headers=ceo_a, json={"name": "Hacked"}
    )
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# System methods cannot be deleted or deactivated
# ---------------------------------------------------------------------------
def test_system_method_cannot_be_deleted(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "pm-f")
    cash = next(m for m in client.get("/api/v1/payment-methods", headers=ceo).json() if m["name"] == "Naqd")
    resp = client.delete(f"/api/v1/payment-methods/{cash['id']}", headers=ceo)
    assert resp.status_code == 422, resp.text


def test_system_method_cannot_be_deactivated(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "pm-g")
    cash = next(m for m in client.get("/api/v1/payment-methods", headers=ceo).json() if m["name"] == "Naqd")
    resp = client.put(f"/api/v1/payment-methods/{cash['id']}", headers=ceo, json={"is_active": False})
    assert resp.status_code == 422, resp.text


def test_custom_method_can_be_deactivated_and_deleted(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "pm-h")
    custom = client.post(
        "/api/v1/payment-methods", headers=ceo, json={"name": "Terminal", "type": "bank"}
    ).json()

    deactivated = client.put(
        f"/api/v1/payment-methods/{custom['id']}", headers=ceo, json={"is_active": False}
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["is_active"] is False

    deleted = client.delete(f"/api/v1/payment-methods/{custom['id']}", headers=ceo)
    assert deleted.status_code == 200, deleted.text


# ---------------------------------------------------------------------------
# Sales/Debts tenant-isolation fix: cross-company payment_method_id rejected
# ---------------------------------------------------------------------------
def test_sale_rejects_foreign_company_payment_method(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "pm-i1")
    ceo_b = _onboard(client, db_session, "pm-i2")
    store_a = _store(client, ceo_a)

    cat = client.post("/api/v1/categories", headers=ceo_a, json={"name": "Cat"}).json()["id"]
    unit = client.post("/api/v1/units", headers=ceo_a, json={"name": "Unit", "short_name": "u"}).json()["id"]
    product = client.post(
        "/api/v1/products",
        headers=ceo_a,
        json={"name": "P", "sku": "SKU-PMI", "category_id": cat, "unit_id": unit, "purchase_price": "10.00", "sale_price": "15.00"},
    ).json()
    warehouse_a = _warehouse(client, ceo_a, "pm-i1", "wh-pm-i1")
    client.post("/api/v1/stock-in", headers=warehouse_a, json={"store_id": store_a, "items": [{"product_id": product["id"], "quantity": "10", "price": "10.00"}]})
    cashier_a = _cashier(client, ceo_a, "pm-i1", "cashier-pm-i1", store_a)

    cash_b = next(m for m in client.get("/api/v1/payment-methods", headers=ceo_b).json() if m["name"] == "Naqd")

    resp = client.post(
        "/api/v1/sales",
        headers=cashier_a,
        json={
            "store_id": store_a,
            "items": [{"product_id": product["id"], "quantity": "1"}],
            "payments": [{"payment_method_id": cash_b["id"], "amount": "15.00"}],
        },
    )
    assert resp.status_code == 404, resp.text
