"""Tests for the migrated Suppliers module (Production Fix 3).

Company-wide (no store scope), same pattern as Customers: CEO and Seller
share one access tier, legacy admin transitional (NULL scope), Super Admin no
access. Stock In's supplier_id lookup is company-scoped — a foreign
company's supplier_id is a 404.
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


def _seller(client: TestClient, ceo: dict[str, str], slug: str, username: str, store_id: int) -> dict[str, str]:
    resp = client.post(
        "/api/v1/employees",
        headers=ceo,
        json={"username": username, "full_name": "Seller", "password": "Sell12345!", "store_id": store_id},
    )
    assert resp.status_code == 201, resp.text
    return _bearer(client, username, "Sell12345!", company_slug=slug)


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


def _supplier(client: TestClient, headers: dict[str, str], name: str) -> dict:
    resp = client.post("/api/v1/suppliers", headers=headers, json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# CEO CRUD
# ---------------------------------------------------------------------------
def test_ceo_creates_and_lists_supplier(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sup-a")
    created = _supplier(client, ceo, "Fert Co")
    assert created["company_id"] is not None

    listed = client.get("/api/v1/suppliers", headers=ceo).json()
    assert any(s["id"] == created["id"] for s in listed["items"])


def test_ceo_updates_and_deletes_supplier(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sup-b")
    created = _supplier(client, ceo, "Old Name")

    updated = client.put(f"/api/v1/suppliers/{created['id']}", headers=ceo, json={"name": "New Name"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "New Name"

    deleted = client.delete(f"/api/v1/suppliers/{created['id']}", headers=ceo)
    assert deleted.status_code == 200, deleted.text
    assert client.get(f"/api/v1/suppliers/{created['id']}", headers=ceo).status_code == 404


# ---------------------------------------------------------------------------
# Seller access (company-wide, same tier as CEO)
# ---------------------------------------------------------------------------
def test_seller_can_create_and_read_company_wide(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sup-c")
    store_id = _store(client, ceo)
    seller = _seller(client, ceo, "sup-c", "seller-sup-c", store_id)

    created = _supplier(client, seller, "Seller's Supplier")
    # CEO sees the same company-wide supplier.
    assert client.get(f"/api/v1/suppliers/{created['id']}", headers=ceo).status_code == 200


# ---------------------------------------------------------------------------
# Authorization / tenant isolation
# ---------------------------------------------------------------------------
def test_super_admin_no_access(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-sup-d")
    sa = _bearer(client, "root-sup-d", "Root12345!")
    assert client.get("/api/v1/suppliers", headers=sa).status_code == 403
    assert client.post("/api/v1/suppliers", headers=sa, json={"name": "X"}).status_code == 403


def test_cross_company_detail_404(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "sup-e1")
    ceo_b = _onboard(client, db_session, "sup-e2")
    created_b = _supplier(client, ceo_b, "Company B Supplier")

    assert client.get(f"/api/v1/suppliers/{created_b['id']}", headers=ceo_a).status_code == 404
    listed_a = client.get("/api/v1/suppliers", headers=ceo_a).json()
    assert listed_a["meta"]["total"] == 0


def test_cross_company_update_and_delete_404(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "sup-f1")
    ceo_b = _onboard(client, db_session, "sup-f2")
    created_b = _supplier(client, ceo_b, "Company B Supplier")

    assert client.put(f"/api/v1/suppliers/{created_b['id']}", headers=ceo_a, json={"name": "Hacked"}).status_code == 404
    assert client.delete(f"/api/v1/suppliers/{created_b['id']}", headers=ceo_a).status_code == 404


# ---------------------------------------------------------------------------
# Stock In integration: company-scoped supplier_id
# ---------------------------------------------------------------------------
def test_stock_in_rejects_foreign_company_supplier(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "sup-g1")
    ceo_b = _onboard(client, db_session, "sup-g2")
    store_a = _store(client, ceo_a)
    product_a = _product(client, ceo_a, "SKU-SUPG")
    supplier_b = _supplier(client, ceo_b, "Foreign Supplier")

    resp = client.post(
        "/api/v1/stock-in",
        headers=ceo_a,
        json={
            "store_id": store_a,
            "supplier_id": supplier_b["id"],
            "items": [{"product_id": product_a, "quantity": "1", "price": "1.00"}],
        },
    )
    assert resp.status_code == 404, resp.text


def test_stock_in_accepts_own_company_supplier(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sup-h")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-SUPH")
    own_supplier = _supplier(client, ceo, "Own Supplier")

    resp = client.post(
        "/api/v1/stock-in",
        headers=ceo,
        json={
            "store_id": store_id,
            "supplier_id": own_supplier["id"],
            "items": [{"product_id": product_id, "quantity": "1", "price": "1.00"}],
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["supplier_id"] == own_supplier["id"]


# ---------------------------------------------------------------------------
# Legacy admin transitional support
# ---------------------------------------------------------------------------
def test_legacy_admin_can_use_suppliers(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = _supplier(client, auth_headers, "Legacy Supplier")
    assert created["company_id"] is None
    assert client.get(f"/api/v1/suppliers/{created['id']}", headers=auth_headers).status_code == 200
