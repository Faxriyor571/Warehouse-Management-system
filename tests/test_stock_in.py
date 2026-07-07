"""Tests for the migrated Stock In module (Phase 8).

Stock In now writes the per-store ``store_stock`` balance and the
``stock_movements`` ledger via ``inventory_service.apply_movement`` (verified
through the read-only §7 Inventory endpoints). CEO/Seller only (+ transitional
legacy admin, covered by test_stock_flow); Super Admin has no access.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import security
from app.models.enums import UserRole
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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


def _store_qty(client: TestClient, headers: dict[str, str], store_id: int | None, product_id: int) -> float | None:
    url = "/api/v1/inventory/store-stock"
    if store_id is not None:
        url += f"?store_id={store_id}"
    rows = client.get(url, headers=headers).json()["items"]
    for r in rows:
        if r["product_id"] == product_id:
            return float(r["quantity"])
    return None


# ---------------------------------------------------------------------------
# Create — inventory effect
# ---------------------------------------------------------------------------
def test_ceo_stock_in_increases_store_stock(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "si-a")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-A")

    resp = client.post(
        "/api/v1/stock-in",
        headers=ceo,
        json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": "100", "price": "12.00"}]},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["store_id"] == store_id
    assert float(body["total_amount"]) == 1200.0

    # store_stock now reflects the receipt.
    assert _store_qty(client, ceo, store_id, product_id) == 100.0

    # A stock_in movement is recorded in the ledger.
    movements = client.get(f"/api/v1/inventory/movements?product_id={product_id}", headers=ceo).json()["items"]
    assert len(movements) == 1
    assert movements[0]["movement_type"] == "stock_in"
    assert float(movements[0]["quantity_delta"]) == 100.0


def test_two_stock_ins_accumulate(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "si-b")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-B")

    for qty in ("40", "60"):
        client.post(
            "/api/v1/stock-in",
            headers=ceo,
            json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": qty, "price": "10.00"}]},
        )
    assert _store_qty(client, ceo, store_id, product_id) == 100.0


def test_seller_stock_in_uses_own_store(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "si-c")
    own = _store(client, ceo, "Own")
    other = _store(client, ceo, "Other")
    product_id = _product(client, ceo, "SKU-C")
    seller = _seller(client, ceo, "si-c", "seller-si-c", own)

    # Seller passes a foreign store_id in the body; it must be ignored — the
    # receipt lands in the seller's own store.
    resp = client.post(
        "/api/v1/stock-in",
        headers=seller,
        json={"store_id": other, "items": [{"product_id": product_id, "quantity": "25", "price": "10.00"}]},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["store_id"] == own
    assert _store_qty(client, ceo, own, product_id) == 25.0
    assert _store_qty(client, ceo, other, product_id) is None


# ---------------------------------------------------------------------------
# Validation / authorization
# ---------------------------------------------------------------------------
def test_ceo_missing_store_id_rejected(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "si-d")
    product_id = _product(client, ceo, "SKU-D")
    resp = client.post(
        "/api/v1/stock-in",
        headers=ceo,
        json={"items": [{"product_id": product_id, "quantity": "1", "price": "1.00"}]},
    )
    assert resp.status_code == 422


def test_foreign_store_rejected(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "si-e1")
    ceo_b = _onboard(client, db_session, "si-e2")
    store_b = _store(client, ceo_b)
    product_a = _product(client, ceo_a, "SKU-E")
    resp = client.post(
        "/api/v1/stock-in",
        headers=ceo_a,
        json={"store_id": store_b, "items": [{"product_id": product_a, "quantity": "1", "price": "1.00"}]},
    )
    assert resp.status_code == 404


def test_foreign_product_rejected(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "si-f1")
    ceo_b = _onboard(client, db_session, "si-f2")
    store_a = _store(client, ceo_a)
    product_b = _product(client, ceo_b, "SKU-F")
    resp = client.post(
        "/api/v1/stock-in",
        headers=ceo_a,
        json={"store_id": store_a, "items": [{"product_id": product_b, "quantity": "1", "price": "1.00"}]},
    )
    assert resp.status_code == 404


def test_empty_items_and_bad_quantity_rejected(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "si-g")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-G")

    assert client.post("/api/v1/stock-in", headers=ceo, json={"store_id": store_id, "items": []}).status_code == 422
    assert client.post(
        "/api/v1/stock-in",
        headers=ceo,
        json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": "0", "price": "1.00"}]},
    ).status_code == 422


def test_super_admin_no_access(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-si-h")
    sa = _bearer(client, "root-si-h", "Root12345!")
    assert client.get("/api/v1/stock-in", headers=sa).status_code == 403
    assert client.post("/api/v1/stock-in", headers=sa, json={"store_id": 1, "items": []}).status_code == 403


# ---------------------------------------------------------------------------
# Tenant isolation + reference numbering
# ---------------------------------------------------------------------------
def test_cross_company_detail_404(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "si-i1")
    ceo_b = _onboard(client, db_session, "si-i2")
    store_b = _store(client, ceo_b)
    product_b = _product(client, ceo_b, "SKU-I")
    doc_b = client.post(
        "/api/v1/stock-in",
        headers=ceo_b,
        json={"store_id": store_b, "items": [{"product_id": product_b, "quantity": "5", "price": "1.00"}]},
    ).json()

    assert client.get(f"/api/v1/stock-in/{doc_b['id']}", headers=ceo_a).status_code == 404
    listed_a = client.get("/api/v1/stock-in", headers=ceo_a).json()
    assert listed_a["meta"]["total"] == 0


def test_reference_numbering_per_company(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "si-j1")
    ceo_b = _onboard(client, db_session, "si-j2")
    sa = _store(client, ceo_a)
    sb = _store(client, ceo_b)
    pa = _product(client, ceo_a, "SKU-JA")
    pb = _product(client, ceo_b, "SKU-JB")

    ra = client.post("/api/v1/stock-in", headers=ceo_a, json={"store_id": sa, "items": [{"product_id": pa, "quantity": "1", "price": "1"}]}).json()
    rb = client.post("/api/v1/stock-in", headers=ceo_b, json={"store_id": sb, "items": [{"product_id": pb, "quantity": "1", "price": "1"}]}).json()
    # Each company's first document numbers independently.
    assert ra["reference"] == rb["reference"]


def test_reconciliation_holds(client: TestClient, db_session: Session) -> None:
    """store_stock balance == sum of ledger deltas after receipts."""
    ceo = _onboard(client, db_session, "si-k")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-K")
    for qty in ("10", "5", "20"):
        client.post("/api/v1/stock-in", headers=ceo, json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": qty, "price": "1"}]})

    balance = _store_qty(client, ceo, store_id, product_id)
    movements = client.get(f"/api/v1/inventory/movements?product_id={product_id}", headers=ceo).json()["items"]
    ledger = sum(float(m["quantity_delta"]) for m in movements)
    assert balance == ledger == 35.0
