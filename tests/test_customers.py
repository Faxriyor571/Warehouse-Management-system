"""Tests for the migrated Customers module (Phase 10, API_SPECIFICATION.md §10).

Customers are company-wide (no store scope): any Seller in the company can
find/manage any company customer, but a Seller's debt/sales history view in
the detail response is filtered to their own store. CEO/Seller only (+
transitional legacy admin); Super Admin has no access.
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


def _cash_method_id(db: Session, company_id: int) -> int:
    method = pm_crud.get_by_type_for_company(db, PaymentMethodType.CASH, company_id)
    assert method is not None
    return method.id


def _company_id(db: Session, slug: str) -> int:
    company = company_crud.get_by_slug(db, slug)
    assert company is not None
    return company.id


# ---------------------------------------------------------------------------
# Create / validation
# ---------------------------------------------------------------------------
def test_ceo_creates_customer_requires_customer_type(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "cu-a")
    resp = client.post(
        "/api/v1/customers",
        headers=ceo,
        json={"full_name": "Ali Valiyev", "phone": "+998901234567"},
    )
    assert resp.status_code == 422, resp.text


def test_ceo_creates_customer_with_type(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "cu-b")
    resp = client.post(
        "/api/v1/customers",
        headers=ceo,
        json={"full_name": "Ali Valiyev", "customer_type": "individual", "phone": "+998901234567"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["customer_type"] == "individual"


def test_individual_customer_name_and_phone_are_optional(client: TestClient, db_session: Session) -> None:
    """Business rule (amended 2026-07-09): an Individual customer must not be
    forced to have a name or phone on file. The full_name column is still
    NOT NULL at the DB level — the service generates a placeholder."""
    ceo = _onboard(client, db_session, "cu-ind")
    resp = client.post("/api/v1/customers", headers=ceo, json={"customer_type": "individual"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["full_name"]  # never blank/null — a placeholder was generated
    assert body["phone"] is None


def test_individual_customer_placeholder_name_uses_phone_if_given(
    client: TestClient, db_session: Session
) -> None:
    ceo = _onboard(client, db_session, "cu-ind-ph")
    resp = client.post(
        "/api/v1/customers", headers=ceo, json={"customer_type": "individual", "phone": "+998901234567"}
    )
    assert resp.status_code == 201, resp.text
    assert "+998901234567" in resp.json()["full_name"]


def test_individual_customer_explicit_name_is_kept(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "cu-ind-name")
    resp = client.post(
        "/api/v1/customers", headers=ceo, json={"customer_type": "individual", "full_name": "Ali Valiyev"}
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["full_name"] == "Ali Valiyev"


def test_legal_entity_customer_still_requires_name(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "cu-legal")
    resp = client.post("/api/v1/customers", headers=ceo, json={"customer_type": "legal_entity"})
    assert resp.status_code == 422, resp.text


def test_sale_works_for_individual_customer_with_no_name(client: TestClient, db_session: Session) -> None:
    """'Sales must work without forcing those fields' — an Individual
    customer created with no name/phone must still be usable in a Sale."""
    ceo = _onboard(client, db_session, "cu-sale")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "CUSALE")
    client.post(
        "/api/v1/stock-in",
        headers=ceo,
        json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": "10", "price": "10.00"}]},
    )
    customer_id = client.post(
        "/api/v1/customers", headers=ceo, json={"customer_type": "individual"}
    ).json()["id"]

    resp = client.post(
        "/api/v1/sales",
        headers=ceo,
        json={
            "store_id": store_id,
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": "1", "price": "15.00"}],
        },
    )
    assert resp.status_code == 201, resp.text


def test_seller_can_create_and_list_company_wide(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "cu-c")
    store_id = _store(client, ceo)
    seller = _seller(client, ceo, "cu-c", "seller-cu-c", store_id)

    resp = client.post(
        "/api/v1/customers",
        headers=seller,
        json={"full_name": "Vali Aliyev", "customer_type": "legal_entity"},
    )
    assert resp.status_code == 201, resp.text
    customer_id = resp.json()["id"]

    # CEO sees the same company-wide list.
    listed = client.get("/api/v1/customers", headers=ceo).json()
    assert any(c["id"] == customer_id for c in listed["items"])


# ---------------------------------------------------------------------------
# Authorization / tenant isolation
# ---------------------------------------------------------------------------
def test_super_admin_no_access(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-cu-d")
    sa = _bearer(client, "root-cu-d", "Root12345!")
    assert client.get("/api/v1/customers", headers=sa).status_code == 403
    assert client.post("/api/v1/customers", headers=sa, json={"full_name": "X", "customer_type": "individual"}).status_code == 403


def test_cross_company_detail_404(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "cu-e1")
    ceo_b = _onboard(client, db_session, "cu-e2")
    created = client.post(
        "/api/v1/customers",
        headers=ceo_b,
        json={"full_name": "Boshqa mijoz", "customer_type": "individual"},
    ).json()

    assert client.get(f"/api/v1/customers/{created['id']}", headers=ceo_a).status_code == 404
    listed_a = client.get("/api/v1/customers", headers=ceo_a).json()
    assert listed_a["meta"]["total"] == 0


def test_sale_rejects_foreign_company_customer(client: TestClient, db_session: Session) -> None:
    """Tenant-isolation fix: Sales' customer_id lookup must be company-scoped,
    same as the payment_method_id fix — a foreign company's customer_id must
    not be usable in a sale."""
    ceo_a = _onboard(client, db_session, "cu-j1")
    ceo_b = _onboard(client, db_session, "cu-j2")
    store_a = _store(client, ceo_a)
    product_id = _product(client, ceo_a, "SKU-CUJ")
    client.post("/api/v1/stock-in", headers=ceo_a, json={"store_id": store_a, "items": [{"product_id": product_id, "quantity": "10", "price": "10.00"}]})

    customer_b = client.post(
        "/api/v1/customers", headers=ceo_b, json={"full_name": "Boshqa mijoz", "customer_type": "individual"}
    ).json()

    resp = client.post(
        "/api/v1/sales",
        headers=ceo_a,
        json={
            "store_id": store_a,
            "customer_id": customer_b["id"],
            "items": [{"product_id": product_id, "quantity": "1"}],
            "payments": [],
        },
    )
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Detail view: store-filtered debt/sales history for a Seller
# ---------------------------------------------------------------------------
def test_seller_detail_history_filtered_to_own_store(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "cu-f")
    store_a = _store(client, ceo, "Store A")
    store_b = _store(client, ceo, "Store B")
    product_id = _product(client, ceo, "SKU-CUF")
    seller_a = _seller(client, ceo, "cu-f", "seller-cu-f-a", store_a)
    company_id = _company_id(db_session, "cu-f")
    cash_id = _cash_method_id(db_session, company_id)

    customer_id = client.post(
        "/api/v1/customers", headers=ceo, json={"full_name": "Umumiy mijoz", "customer_type": "individual"}
    ).json()["id"]

    for store_id in (store_a, store_b):
        client.post("/api/v1/stock-in", headers=ceo, json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": "50", "price": "10.00"}]})

    # A sale in store A and a sale in store B, both for the same customer.
    client.post(
        "/api/v1/sales",
        headers=ceo,
        json={"store_id": store_a, "customer_id": customer_id, "items": [{"product_id": product_id, "quantity": "1"}], "payments": [{"payment_method_id": cash_id, "amount": "15.00"}]},
    )
    client.post(
        "/api/v1/sales",
        headers=ceo,
        json={"store_id": store_b, "customer_id": customer_id, "items": [{"product_id": product_id, "quantity": "1"}], "payments": [{"payment_method_id": cash_id, "amount": "15.00"}]},
    )

    # CEO sees both purchases company-wide.
    ceo_detail = client.get(f"/api/v1/customers/{customer_id}", headers=ceo).json()
    assert len(ceo_detail["purchases"]) == 2

    # Seller A only sees store A's purchase.
    seller_detail = client.get(f"/api/v1/customers/{customer_id}", headers=seller_a).json()
    assert len(seller_detail["purchases"]) == 1


# ---------------------------------------------------------------------------
# Deactivate
# ---------------------------------------------------------------------------
def test_deactivate_blocked_while_debt_outstanding(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "cu-g")
    store_id = _store(client, ceo)
    product_id = _product(client, ceo, "SKU-CUG")
    company_id = _company_id(db_session, "cu-g")
    cash_id = _cash_method_id(db_session, company_id)
    client.post("/api/v1/stock-in", headers=ceo, json={"store_id": store_id, "items": [{"product_id": product_id, "quantity": "50", "price": "10.00"}]})

    customer_id = client.post(
        "/api/v1/customers", headers=ceo, json={"full_name": "Qarzdor", "customer_type": "individual"}
    ).json()["id"]

    client.post(
        "/api/v1/sales",
        headers=ceo,
        json={
            "store_id": store_id,
            "customer_id": customer_id,
            "items": [{"product_id": product_id, "quantity": "10"}],
            "payments": [{"payment_method_id": cash_id, "amount": "100.00"}],  # 150 total -> 50 debt
        },
    )

    resp = client.post(f"/api/v1/customers/{customer_id}/deactivate", headers=ceo)
    assert resp.status_code == 409, resp.text


def test_deactivate_allowed_when_no_debt(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "cu-h")
    customer_id = client.post(
        "/api/v1/customers", headers=ceo, json={"full_name": "Toza mijoz", "customer_type": "individual"}
    ).json()["id"]

    resp = client.post(f"/api/v1/customers/{customer_id}/deactivate", headers=ceo)
    assert resp.status_code == 200, resp.text

    # Deactivated customers no longer appear in the default list.
    listed = client.get("/api/v1/customers", headers=ceo).json()
    assert all(c["id"] != customer_id for c in listed["items"])


def test_seller_cannot_deactivate(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "cu-i")
    store_id = _store(client, ceo)
    seller = _seller(client, ceo, "cu-i", "seller-cu-i", store_id)
    customer_id = client.post(
        "/api/v1/customers", headers=ceo, json={"full_name": "Mijoz", "customer_type": "individual"}
    ).json()["id"]

    resp = client.post(f"/api/v1/customers/{customer_id}/deactivate", headers=seller)
    assert resp.status_code == 403, resp.text
