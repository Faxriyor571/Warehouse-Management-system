"""Tests for the Inventory module (Phase 7 — store_stock foundation).

The Inventory endpoints are read-only; store_stock/stock_movements are seeded
here by driving inventory_service.apply_movement directly (the same primitive
the migrated Stock In / Sales writers will call). product.quantity is
untouched by this module.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import security
from app.models.enums import MovementType, UserRole
from app.models.user import User
from app.services import inventory_service
from app.utils.exceptions import InsufficientStockError


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


def _onboard(client: TestClient, db: Session, slug: str) -> tuple[dict[str, str], int, int]:
    """Return (CEO headers, company_id, ceo_user_id)."""
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
    company_id = resp.json()["company"]["id"]
    ceo = _bearer(client, f"ceo-{slug}", "Ceo12345!", company_slug=slug)
    ceo_user = db.query(User).filter(User.username == f"ceo-{slug}", User.company_id == company_id).one()
    return ceo, company_id, ceo_user.id


def _make_store(client: TestClient, ceo: dict[str, str], name: str) -> int:
    return client.post("/api/v1/stores", headers=ceo, json={"name": name}).json()["id"]


def _make_product(client: TestClient, ceo: dict[str, str], sku: str = "SKU-1") -> int:
    cat = client.post("/api/v1/categories", headers=ceo, json={"name": f"Cat-{sku}"}).json()["id"]
    unit = client.post("/api/v1/units", headers=ceo, json={"name": f"Unit-{sku}", "short_name": "u"}).json()["id"]
    resp = client.post(
        "/api/v1/products",
        headers=ceo,
        json={"name": f"Prod-{sku}", "sku": sku, "category_id": cat, "unit_id": unit,
              "purchase_price": "10.00", "sale_price": "15.00"},
    )
    return resp.json()["id"]


def _make_seller(client: TestClient, ceo: dict[str, str], slug: str, username: str, store_id: int) -> dict[str, str]:
    resp = client.post(
        "/api/v1/employees",
        headers=ceo,
        json={"username": username, "full_name": "Seller", "password": "Sell12345!", "store_id": store_id},
    )
    assert resp.status_code == 201, resp.text
    return _bearer(client, username, "Sell12345!", company_slug=slug)


def _seed(db: Session, company_id: int, store_id: int, product_id: int, created_by_id: int,
          delta: str, mtype: MovementType = MovementType.STOCK_IN, ref_type: str = "stock_in") -> None:
    inventory_service.apply_movement(
        db,
        company_id=company_id,
        store_id=store_id,
        product_id=product_id,
        movement_type=mtype,
        quantity_delta=Decimal(delta),
        reference_type=ref_type,
        created_by_id=created_by_id,
        commit=True,
    )


# ---------------------------------------------------------------------------
# Store-stock (per store / company-wide)
# ---------------------------------------------------------------------------
def test_store_stock_reflects_movements(client: TestClient, db_session: Session) -> None:
    ceo, cid, uid = _onboard(client, db_session, "inv-a")
    store = _make_store(client, ceo, "Main")
    prod = _make_product(client, ceo)
    _seed(db_session, cid, store, prod, uid, "100")

    resp = client.get(f"/api/v1/inventory/store-stock?store_id={store}", headers=ceo)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["product_id"] == prod
    assert float(items[0]["quantity"]) == 100.0


def test_ceo_company_wide_totals(client: TestClient, db_session: Session) -> None:
    ceo, cid, uid = _onboard(client, db_session, "inv-b")
    store_a = _make_store(client, ceo, "Store A")
    store_b = _make_store(client, ceo, "Store B")
    prod = _make_product(client, ceo)
    _seed(db_session, cid, store_a, prod, uid, "50")
    _seed(db_session, cid, store_b, prod, uid, "30")

    # No store_id → company-wide total (50 + 30).
    resp = client.get("/api/v1/inventory/store-stock", headers=ceo)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert float(items[0]["quantity"]) == 80.0

    # Specific store → that store only.
    a = client.get(f"/api/v1/inventory/store-stock?store_id={store_a}", headers=ceo).json()["items"]
    assert float(a[0]["quantity"]) == 50.0


def test_ceo_foreign_store_404(client: TestClient, db_session: Session) -> None:
    ceo_a, _, _ = _onboard(client, db_session, "inv-c1")
    ceo_b, _, _ = _onboard(client, db_session, "inv-c2")
    store_b = _make_store(client, ceo_b, "Store B")

    resp = client.get(f"/api/v1/inventory/store-stock?store_id={store_b}", headers=ceo_a)
    assert resp.status_code == 404


def test_seller_confined_to_own_store(client: TestClient, db_session: Session) -> None:
    ceo, cid, uid = _onboard(client, db_session, "inv-d")
    store_a = _make_store(client, ceo, "Store A")
    store_b = _make_store(client, ceo, "Store B")
    prod = _make_product(client, ceo)
    _seed(db_session, cid, store_a, prod, uid, "50")
    _seed(db_session, cid, store_b, prod, uid, "30")
    seller = _make_seller(client, ceo, "inv-d", "seller-inv-d", store_a)

    # No store_id → forced to own store (A = 50).
    own = client.get("/api/v1/inventory/store-stock", headers=seller).json()["items"]
    assert float(own[0]["quantity"]) == 50.0

    # Passing store B is ignored — still own store A.
    forced = client.get(f"/api/v1/inventory/store-stock?store_id={store_b}", headers=seller).json()["items"]
    assert float(forced[0]["quantity"]) == 50.0


# ---------------------------------------------------------------------------
# Cross-store (quantity-only, the one permitted Seller cross-store view)
# ---------------------------------------------------------------------------
def test_cross_store_view(client: TestClient, db_session: Session) -> None:
    ceo, cid, uid = _onboard(client, db_session, "inv-e")
    store_a = _make_store(client, ceo, "Store A")
    store_b = _make_store(client, ceo, "Store B")
    prod = _make_product(client, ceo)
    _seed(db_session, cid, store_a, prod, uid, "50")
    _seed(db_session, cid, store_b, prod, uid, "30")
    seller = _make_seller(client, ceo, "inv-e", "seller-inv-e", store_a)

    # A Seller in store A may see every store's quantity for the product.
    rows = client.get(f"/api/v1/inventory/store-stock/cross-store?product_id={prod}", headers=seller).json()
    by_store = {r["store_id"]: float(r["quantity"]) for r in rows}
    assert by_store == {store_a: 50.0, store_b: 30.0}
    # Response is quantity-only.
    assert set(rows[0].keys()) == {"store_id", "store_name", "quantity"}


def test_cross_store_unknown_product_404(client: TestClient, db_session: Session) -> None:
    ceo_a, _, _ = _onboard(client, db_session, "inv-f1")
    ceo_b, _, _ = _onboard(client, db_session, "inv-f2")
    prod_b = _make_product(client, ceo_b, sku="B-SKU")

    resp = client.get(f"/api/v1/inventory/store-stock/cross-store?product_id={prod_b}", headers=ceo_a)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Movement ledger
# ---------------------------------------------------------------------------
def test_movements_ledger(client: TestClient, db_session: Session) -> None:
    ceo, cid, uid = _onboard(client, db_session, "inv-g")
    store = _make_store(client, ceo, "Main")
    prod = _make_product(client, ceo)
    _seed(db_session, cid, store, prod, uid, "100", MovementType.STOCK_IN, "stock_in")
    _seed(db_session, cid, store, prod, uid, "-10", MovementType.SALE, "sale")

    resp = client.get(f"/api/v1/inventory/movements?store_id={store}", headers=ceo)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    kinds = {i["movement_type"] for i in items}
    assert kinds == {"stock_in", "sale"}
    # Filter by movement_type.
    sales = client.get(f"/api/v1/inventory/movements?movement_type=sale", headers=ceo).json()["items"]
    assert len(sales) == 1 and float(sales[0]["quantity_delta"]) == -10.0


def test_movements_seller_own_store_only(client: TestClient, db_session: Session) -> None:
    ceo, cid, uid = _onboard(client, db_session, "inv-h")
    store_a = _make_store(client, ceo, "Store A")
    store_b = _make_store(client, ceo, "Store B")
    prod = _make_product(client, ceo)
    _seed(db_session, cid, store_a, prod, uid, "100")
    _seed(db_session, cid, store_b, prod, uid, "40")
    seller = _make_seller(client, ceo, "inv-h", "seller-inv-h", store_a)

    items = client.get("/api/v1/inventory/movements", headers=seller).json()["items"]
    assert all(i["store_id"] == store_a for i in items)
    assert len(items) == 1  # only store A's movement


# ---------------------------------------------------------------------------
# Service invariants: negative guard + reconciliation
# ---------------------------------------------------------------------------
def test_apply_movement_rejects_negative(client: TestClient, db_session: Session) -> None:
    ceo, cid, uid = _onboard(client, db_session, "inv-i")
    store = _make_store(client, ceo, "Main")
    prod = _make_product(client, ceo)
    _seed(db_session, cid, store, prod, uid, "5")

    with pytest.raises(InsufficientStockError):
        inventory_service.apply_movement(
            db_session, company_id=cid, store_id=store, product_id=prod,
            movement_type=MovementType.SALE, quantity_delta=Decimal("-10"),
            reference_type="sale", created_by_id=uid, commit=True,
        )
    db_session.rollback()


def test_reconciliation_holds(client: TestClient, db_session: Session) -> None:
    ceo, cid, uid = _onboard(client, db_session, "inv-j")
    store = _make_store(client, ceo, "Main")
    prod = _make_product(client, ceo)
    _seed(db_session, cid, store, prod, uid, "100")
    _seed(db_session, cid, store, prod, uid, "-30", MovementType.SALE, "sale")
    _seed(db_session, cid, store, prod, uid, "5", MovementType.SALES_RETURN, "sales_return")

    assert inventory_service.reconcile(db_session, store, prod) is True
    # Balance is 100 - 30 + 5 = 75.
    stock = client.get(f"/api/v1/inventory/store-stock?store_id={store}", headers=ceo).json()["items"]
    assert float(stock[0]["quantity"]) == 75.0


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
def test_super_admin_no_access(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-inv-k")
    sa = _bearer(client, "root-inv-k", "Root12345!")
    assert client.get("/api/v1/inventory/store-stock", headers=sa).status_code == 403
    assert client.get("/api/v1/inventory/movements", headers=sa).status_code == 403


def test_legacy_admin_no_access(client: TestClient, auth_headers: dict[str, str]) -> None:
    """The Inventory module is new multi-tenant only — the legacy admin (role
    None) is not CEO/Seller and has no access."""
    assert client.get("/api/v1/inventory/store-stock", headers=auth_headers).status_code == 403
