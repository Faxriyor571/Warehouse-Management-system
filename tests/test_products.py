"""Tests for the multi-tenant Products catalogue (Phase 6 — catalog migration).

Writes are CEO-only; reads are CEO/Seller; Super Admin has no access.
Cross-company category/unit references are rejected (the FK-scoping fix). The
legacy admin operates in the NULL-company scope (also covered by
test_stock_flow).
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


def _make_seller(client: TestClient, ceo: dict[str, str], slug: str, username: str) -> dict[str, str]:
    store = client.post("/api/v1/stores", headers=ceo, json={"name": "Store"}).json()["id"]
    resp = client.post(
        "/api/v1/employees",
        headers=ceo,
        json={"username": username, "full_name": "Seller", "password": "Sell12345!", "store_id": store},
    )
    assert resp.status_code == 201, resp.text
    return _bearer(client, username, "Sell12345!", company_slug=slug)


def _catalogue(client: TestClient, ceo: dict[str, str], cat_name: str = "Cat", unit_name: str = "Unit") -> tuple[int, int]:
    cat = client.post("/api/v1/categories", headers=ceo, json={"name": cat_name}).json()["id"]
    unit = client.post("/api/v1/units", headers=ceo, json={"name": unit_name, "short_name": "u"}).json()["id"]
    return cat, unit


def _product_payload(sku: str, category_id: int, unit_id: int, **over) -> dict:
    body = {
        "name": "Test Product",
        "sku": sku,
        "category_id": category_id,
        "unit_id": unit_id,
        "purchase_price": "10.00",
        "sale_price": "15.00",
    }
    body.update(over)
    return body


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
def test_ceo_creates_product(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "prod-a")
    cat, unit = _catalogue(client, ceo)
    resp = client.post("/api/v1/products", headers=ceo, json=_product_payload("SKU-A1", cat, unit))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["sku"] == "SKU-A1"
    assert body["quantity"] == "0.000"  # starts at zero (inventory phase adds stock)


def test_duplicate_sku_within_company_rejected(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "prod-b")
    cat, unit = _catalogue(client, ceo)
    client.post("/api/v1/products", headers=ceo, json=_product_payload("DUP", cat, unit))
    dup = client.post("/api/v1/products", headers=ceo, json=_product_payload("DUP", cat, unit, name="Other"))
    assert dup.status_code == 409


def test_two_companies_share_sku(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "prod-c1")
    ceo_b = _onboard(client, db_session, "prod-c2")
    ca, ua = _catalogue(client, ceo_a)
    cb, ub = _catalogue(client, ceo_b)
    ra = client.post("/api/v1/products", headers=ceo_a, json=_product_payload("SHARED", ca, ua))
    rb = client.post("/api/v1/products", headers=ceo_b, json=_product_payload("SHARED", cb, ub))
    assert ra.status_code == 201
    assert rb.status_code == 201


# ---------------------------------------------------------------------------
# Cross-company FK scoping (the fix identified in the last review)
# ---------------------------------------------------------------------------
def test_category_from_other_company_rejected(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "prod-d1")
    ceo_b = _onboard(client, db_session, "prod-d2")
    _, unit_a = _catalogue(client, ceo_a)
    cat_b, _ = _catalogue(client, ceo_b)

    # CEO A tries to use company B's category → 404 (not in A's company).
    resp = client.post("/api/v1/products", headers=ceo_a, json=_product_payload("X1", cat_b, unit_a))
    assert resp.status_code == 404


def test_unit_from_other_company_rejected(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "prod-e1")
    ceo_b = _onboard(client, db_session, "prod-e2")
    cat_a, _ = _catalogue(client, ceo_a)
    _, unit_b = _catalogue(client, ceo_b)

    resp = client.post("/api/v1/products", headers=ceo_a, json=_product_payload("X2", cat_a, unit_b))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Read / update / delete + tenant isolation
# ---------------------------------------------------------------------------
def test_list_get_update_delete(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "prod-f")
    cat, unit = _catalogue(client, ceo)
    created = client.post("/api/v1/products", headers=ceo, json=_product_payload("SKU-F", cat, unit)).json()

    listed = client.get("/api/v1/products", headers=ceo).json()
    assert {p["sku"] for p in listed["items"]} == {"SKU-F"}

    got = client.get(f"/api/v1/products/{created['id']}", headers=ceo)
    assert got.status_code == 200

    upd = client.put(f"/api/v1/products/{created['id']}", headers=ceo, json={"name": "Renamed", "sale_price": "20.00"})
    assert upd.status_code == 200 and upd.json()["name"] == "Renamed"

    assert client.delete(f"/api/v1/products/{created['id']}", headers=ceo).status_code == 200
    assert client.get(f"/api/v1/products/{created['id']}", headers=ceo).status_code == 404


def test_cross_company_product_access_404(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "prod-g1")
    ceo_b = _onboard(client, db_session, "prod-g2")
    cb, ub = _catalogue(client, ceo_b)
    prod_b = client.post("/api/v1/products", headers=ceo_b, json=_product_payload("B-SKU", cb, ub)).json()

    assert client.get(f"/api/v1/products/{prod_b['id']}", headers=ceo_a).status_code == 404
    assert client.delete(f"/api/v1/products/{prod_b['id']}", headers=ceo_a).status_code == 404


def test_list_filter_by_category(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "prod-h")
    cat1 = client.post("/api/v1/categories", headers=ceo, json={"name": "C1"}).json()["id"]
    cat2 = client.post("/api/v1/categories", headers=ceo, json={"name": "C2"}).json()["id"]
    unit = client.post("/api/v1/units", headers=ceo, json={"name": "U", "short_name": "u"}).json()["id"]
    client.post("/api/v1/products", headers=ceo, json=_product_payload("P1", cat1, unit))
    client.post("/api/v1/products", headers=ceo, json=_product_payload("P2", cat2, unit, name="P2"))

    filtered = client.get(f"/api/v1/products?category_id={cat1}", headers=ceo).json()
    assert {p["sku"] for p in filtered["items"]} == {"P1"}


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
def test_seller_read_only(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "prod-i")
    cat, unit = _catalogue(client, ceo)
    client.post("/api/v1/products", headers=ceo, json=_product_payload("SKU-I", cat, unit))
    seller = _make_seller(client, ceo, "prod-i", "seller-prod-i")

    assert client.get("/api/v1/products", headers=seller).status_code == 200
    assert client.post("/api/v1/products", headers=seller, json=_product_payload("NO", cat, unit)).status_code == 403


def test_super_admin_no_access(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-prod-j")
    sa = _bearer(client, "root-prod-j", "Root12345!")
    assert client.get("/api/v1/products", headers=sa).status_code == 403
    assert client.post("/api/v1/products", headers=sa, json=_product_payload("Z", 1, 1)).status_code == 403
