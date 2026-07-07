"""Tests for the migrated Sales module (Phase 9): sales + sale returns.

Sales writes the per-store ``store_stock`` balance and the ``stock_movements``
ledger via ``inventory_service.apply_movement`` (same as Stock In), and mixes
in cross-cutting validations (legal-entity pricing, mixed payments, debt
creation) preserved from the legacy stock-out flow. CEO/Seller only (+
transitional legacy admin, covered by test_stock_flow); Super Admin has no
access. Reference numbering is scoped **per store** (not per company, unlike
Stock In) per DATABASE_DESIGN.md §6.

Payment Methods and Customers are both company-scoped (Phase 10): each
onboarded company gets its own seeded payment methods, and both
``payment_method_id`` and ``customer_id`` are now company-scoped lookups in
Sales (a tenant-isolation fix, not a new feature) — so both helpers below
(``_cash_method_id``, ``_customer``) resolve/create within the CEO's own
company rather than the legacy NULL scope.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import security
from app.crud.company import company as company_crud
from app.crud.payment_method import payment_method as pm_crud
from app.models.enums import PaymentMethodType, UserRole
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


def _product(client: TestClient, ceo: dict[str, str], sku: str, sale_price: str = "15.00") -> int:
    cat = client.post("/api/v1/categories", headers=ceo, json={"name": f"Cat-{sku}"}).json()["id"]
    unit = client.post("/api/v1/units", headers=ceo, json={"name": f"Unit-{sku}", "short_name": "u"}).json()["id"]
    resp = client.post(
        "/api/v1/products",
        headers=ceo,
        json={"name": f"P-{sku}", "sku": sku, "category_id": cat, "unit_id": unit, "purchase_price": "10.00", "sale_price": sale_price},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _stock_in(client: TestClient, ceo: dict[str, str], store_id: int, product_id: int, quantity: str) -> None:
    resp = client.post(
        "/api/v1/stock-in",
        headers=ceo,
        json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": quantity, "price": "10.00"}]},
    )
    assert resp.status_code == 201, resp.text


def _store_qty(client: TestClient, headers: dict[str, str], store_id: int | None, product_id: int) -> float | None:
    url = "/api/v1/inventory/store-stock"
    if store_id is not None:
        url += f"?store_id={store_id}"
    rows = client.get(url, headers=headers).json()["items"]
    for r in rows:
        if r["product_id"] == product_id:
            return float(r["quantity"])
    return None


def _customer(client: TestClient, ceo: dict[str, str], full_name: str, customer_type: str = "individual") -> int:
    """Customers is company-scoped (Phase 10); create through the real
    endpoint so the customer lands in the CEO's own company — a raw
    ``db_session`` insert would default to the legacy NULL-company scope and
    fail the (correct) company-scoped customer_id check in Sales."""
    resp = client.post(
        "/api/v1/customers", headers=ceo, json={"full_name": full_name, "customer_type": customer_type}
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


# ---------------------------------------------------------------------------
# Create — inventory + payments/debt
# ---------------------------------------------------------------------------
def test_ceo_cash_sale_decreases_store_stock(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sa-a")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-SA")
    _stock_in(client, ceo, store_id, product_id, "100")
    cash_id = _cash_method_id(db_session, _company_id(db_session, "sa-a"))

    resp = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={
            "store_id": store_id,
            "items": [{"product_id": product_id, "quantity": "10"}],
            "payments": [{"payment_method_id": cash_id, "amount": "150.00"}],
        },
    )
    assert resp.status_code == 201, resp.text
    sale = resp.json()
    assert sale["payment_status"] == "paid"
    assert float(sale["total_amount"]) == 150.0
    assert _store_qty(client, ceo, store_id, product_id) == 90.0

    movements = client.get(f"/api/v1/inventory/movements?product_id={product_id}", headers=ceo).json()["items"]
    sale_moves = [m for m in movements if m["movement_type"] == "sale"]
    assert len(sale_moves) == 1
    assert float(sale_moves[0]["quantity_delta"]) == -10.0


def test_partial_payment_creates_scoped_debt(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sa-b")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-SB")
    _stock_in(client, ceo, store_id, product_id, "100")
    cash_id = _cash_method_id(db_session, _company_id(db_session, "sa-b"))
    customer_id = _customer(client, ceo, "Ali")

    resp = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={
            "store_id": store_id,
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": "10"}],
            "payments": [{"payment_method_id": cash_id, "amount": "100.00"}],
        },
    )
    assert resp.status_code == 201, resp.text
    sale = resp.json()
    assert sale["payment_status"] == "partial"

    from app.crud.debt import debt as debt_crud

    debts = list(debt_crud.get_all(db_session))
    matching = [d for d in debts if d.stock_out_id == sale["id"]]
    assert len(matching) == 1
    debt = matching[0]
    assert float(debt.remaining_amount) == 50.0
    assert debt.company_id is not None
    assert debt.store_id == store_id


def test_no_payment_requires_customer_for_debt(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sa-c")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-SC")
    _stock_in(client, ceo, store_id, product_id, "100")

    resp = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": "5"}], "payments": []},
    )
    assert resp.status_code == 422, resp.text


def test_insufficient_stock_rejected(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sa-d")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-SD")

    resp = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": "5"}], "payments": []},
    )
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# Legal-entity pricing (SRS rule #18)
# ---------------------------------------------------------------------------
def test_price_override_allowed_for_legal_entity(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sa-e")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-SE", sale_price="15.00")
    _stock_in(client, ceo, store_id, product_id, "100")
    cash_id = _cash_method_id(db_session, _company_id(db_session, "sa-e"))
    customer_id = _customer(client, ceo, "Yuridik", customer_type="legal_entity")

    resp = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={
            "store_id": store_id,
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": "10", "price": "12.00"}],
            "payments": [{"payment_method_id": cash_id, "amount": "120.00"}],
        },
    )
    assert resp.status_code == 201, resp.text
    assert float(resp.json()["total_amount"]) == 120.0


def test_price_override_rejected_for_individual(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sa-f")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-SF", sale_price="15.00")
    _stock_in(client, ceo, store_id, product_id, "100")
    cash_id = _cash_method_id(db_session, _company_id(db_session, "sa-f"))
    customer_id = _customer(client, ceo, "Jismoniy", customer_type="individual")

    resp = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={
            "store_id": store_id,
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": "10", "price": "12.00"}],
            "payments": [{"payment_method_id": cash_id, "amount": "120.00"}],
        },
    )
    assert resp.status_code == 422, resp.text


def test_price_override_rejected_without_customer(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sa-g")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-SG", sale_price="15.00")
    _stock_in(client, ceo, store_id, product_id, "100")
    cash_id = _cash_method_id(db_session, _company_id(db_session, "sa-g"))

    resp = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={
            "store_id": store_id,
            "items": [{"product_id": product_id, "quantity": "10", "price": "12.00"}],
            "payments": [{"payment_method_id": cash_id, "amount": "120.00"}],
        },
    )
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# Authorization / tenant isolation
# ---------------------------------------------------------------------------
def test_seller_sale_uses_own_store(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sa-h")
    own = _store(client, ceo, "Own")
    other = _store(client, ceo, "Other")
    product_id = _product(client, ceo, "SKU-SH")
    _stock_in(client, ceo, own, product_id, "50")
    _stock_in(client, ceo, other, product_id, "50")
    seller = _seller(client, ceo, "sa-h", "seller-sa-h", own)
    cash_id = _cash_method_id(db_session, _company_id(db_session, "sa-h"))

    resp = client.post(
        "/api/v1/sales",
        headers=seller,
        json={
            "store_id": other,
            "items": [{"product_id": product_id, "quantity": "5"}],
            "payments": [{"payment_method_id": cash_id, "amount": "75.00"}],
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["store_id"] == own
    assert _store_qty(client, ceo, own, product_id) == 45.0
    assert _store_qty(client, ceo, other, product_id) == 50.0


def test_super_admin_no_access(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-sa-i")
    sa = _bearer(client, "root-sa-i", "Root12345!")
    assert client.get("/api/v1/sales", headers=sa).status_code == 403
    assert client.post("/api/v1/sales", headers=sa, json={"store_id": 1, "items": [], "payments": []}).status_code == 403


def test_cross_company_detail_404(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "sa-j1")
    ceo_b = _onboard(client, db_session, "sa-j2")
    store_b = _store(client, ceo_b)
    product_b = _product(client, ceo_b, "SKU-SJ")
    _stock_in(client, ceo_b, store_b, product_b, "10")
    cash_id = _cash_method_id(db_session, _company_id(db_session, "sa-j2"))
    sale_b = client.post(
        "/api/v1/sales",
        headers=ceo_b,
        json={
            "store_id": store_b,
            "items": [{"product_id": product_b, "quantity": "1"}],
            "payments": [{"payment_method_id": cash_id, "amount": "15.00"}],
        },
    ).json()

    assert client.get(f"/api/v1/sales/{sale_b['id']}", headers=ceo_a).status_code == 404
    listed_a = client.get("/api/v1/sales", headers=ceo_a).json()
    assert listed_a["meta"]["total"] == 0


# ---------------------------------------------------------------------------
# Reference numbering — per STORE (not per company, unlike Stock In)
# ---------------------------------------------------------------------------
def test_reference_numbering_per_store_within_same_company(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sa-k")
    store_1 = _store(client, ceo, "S1")
    store_2 = _store(client, ceo, "S2")
    product_id = _product(client, ceo, "SKU-SK")
    _stock_in(client, ceo, store_1, product_id, "10")
    _stock_in(client, ceo, store_2, product_id, "10")
    cash_id = _cash_method_id(db_session, _company_id(db_session, "sa-k"))

    r1 = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={"store_id": store_1, "items": [{"product_id": product_id, "quantity": "1"}], "payments": [{"payment_method_id": cash_id, "amount": "15.00"}]},
    ).json()
    r2 = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={"store_id": store_2, "items": [{"product_id": product_id, "quantity": "1"}], "payments": [{"payment_method_id": cash_id, "amount": "15.00"}]},
    ).json()
    # Each store's first sale numbers independently, even within one company.
    assert r1["reference"] == r2["reference"]


def test_dual_mount_stock_out_and_sales_are_the_same_endpoint(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sa-l")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-SL")
    _stock_in(client, ceo, store_id, product_id, "10")
    cash_id = _cash_method_id(db_session, _company_id(db_session, "sa-l"))

    resp = client.post(
        "/api/v1/stock-out",
        headers=ceo,
        json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": "1"}], "payments": [{"payment_method_id": cash_id, "amount": "15.00"}]},
    )
    assert resp.status_code == 201, resp.text
    sale_id = resp.json()["id"]
    # Same document, reachable under both mounted prefixes.
    assert client.get(f"/api/v1/sales/{sale_id}", headers=ceo).status_code == 200
    assert client.get(f"/api/v1/stock-out/{sale_id}", headers=ceo).status_code == 200


# ---------------------------------------------------------------------------
# Sale returns
# ---------------------------------------------------------------------------
def test_sales_return_restores_inventory_and_reduces_debt(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sa-m")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-SM")
    _stock_in(client, ceo, store_id, product_id, "100")
    cash_id = _cash_method_id(db_session, _company_id(db_session, "sa-m"))
    customer_id = _customer(client, ceo, "Vali")

    sale = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={
            "store_id": store_id,
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": "10"}],
            "payments": [{"payment_method_id": cash_id, "amount": "100.00"}],  # 150 total, 50 debt
        },
    ).json()
    assert _store_qty(client, ceo, store_id, product_id) == 90.0

    line_id = sale["items"][0]["id"]
    resp = client.post(
        f"/api/v1/sales/{sale['id']}/returns",
        headers=ceo,
        json={"reason": "Nuqsonli", "items": [{"stock_out_item_id": line_id, "quantity": "4"}]},
    )
    assert resp.status_code == 201, resp.text
    ret = resp.json()
    assert float(ret["total_amount"]) == 60.0  # 4 * 15.00

    # Inventory restored: 90 + 4 = 94.
    assert _store_qty(client, ceo, store_id, product_id) == 94.0

    from app.crud.debt import debt as debt_crud

    debt = next(d for d in debt_crud.get_all(db_session) if d.stock_out_id == sale["id"])
    db_session.refresh(debt)
    # Debt reduced by the returned value, floored (50 - 60 -> 0, not negative).
    assert float(debt.remaining_amount) == 0.0

    listed = client.get(f"/api/v1/sales/{sale['id']}/returns", headers=ceo).json()
    assert len(listed) == 1
    assert listed[0]["id"] == ret["id"]


def test_sales_return_over_return_rejected(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sa-n")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-SN")
    _stock_in(client, ceo, store_id, product_id, "100")
    cash_id = _cash_method_id(db_session, _company_id(db_session, "sa-n"))

    sale = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={
            "store_id": store_id,
            "items": [{"product_id": product_id, "quantity": "10"}],
            "payments": [{"payment_method_id": cash_id, "amount": "150.00"}],
        },
    ).json()
    line_id = sale["items"][0]["id"]

    resp = client.post(
        f"/api/v1/sales/{sale['id']}/returns",
        headers=ceo,
        json={"items": [{"stock_out_item_id": line_id, "quantity": "11"}]},
    )
    assert resp.status_code == 422, resp.text


def test_sales_return_cross_sale_line_rejected(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "sa-o")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-SO")
    _stock_in(client, ceo, store_id, product_id, "100")
    cash_id = _cash_method_id(db_session, _company_id(db_session, "sa-o"))

    sale_1 = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": "5"}], "payments": [{"payment_method_id": cash_id, "amount": "75.00"}]},
    ).json()
    sale_2 = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": "5"}], "payments": [{"payment_method_id": cash_id, "amount": "75.00"}]},
    ).json()
    sale_1_line_id = sale_1["items"][0]["id"]

    # Returning sale_1's line against sale_2's document must fail.
    resp = client.post(
        f"/api/v1/sales/{sale_2['id']}/returns",
        headers=ceo,
        json={"items": [{"stock_out_item_id": sale_1_line_id, "quantity": "1"}]},
    )
    assert resp.status_code == 404, resp.text
