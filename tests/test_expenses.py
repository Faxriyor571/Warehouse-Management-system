"""Tests for the migrated Expenses module (Phase 12, API_SPECIFICATION.md §12).

Company/store scoped like Stock In/Sales: Seller auto-assigned to own store
(store_id never accepted from a Seller), CEO requires store_id in body and
may filter by store_id on read, legacy admin transitional. Immutable — no
PUT/DELETE.
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


# ---------------------------------------------------------------------------
# Create — scope resolution
# ---------------------------------------------------------------------------
def test_ceo_creates_expense_with_store_id(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "ex-a")
    store_id = _store(client, ceo)
    resp = client.post(
        "/api/v1/expenses",
        headers=ceo,
        json={"store_id": store_id, "expense_type": "fuel", "amount": "50000.00", "description": "Yoqilg'i"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["store_id"] == store_id
    assert body["expense_type"] == "fuel"
    assert float(body["amount"]) == 50000.0


def test_ceo_missing_store_id_rejected(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "ex-b")
    resp = client.post(
        "/api/v1/expenses", headers=ceo, json={"expense_type": "other", "amount": "1.00", "description": "x"}
    )
    assert resp.status_code == 422


def test_cashier_has_no_expense_access(client: TestClient, db_session: Session) -> None:
    """A plain Cashier — unlike the old undifferentiated Seller — has no
    Expenses access at all under the ERP role redesign; only CEO and
    Accountant manage company finances."""
    ceo = _onboard(client, db_session, "ex-c")
    own = _store(client, ceo, "Own")
    cashier = _seller(client, ceo, "ex-c", "cashier-ex-c", own)

    resp = client.post(
        "/api/v1/expenses",
        headers=cashier,
        json={"expense_type": "driver", "amount": "20000.00", "description": "Haydovchi"},
    )
    assert resp.status_code == 403, resp.text
    assert client.get("/api/v1/expenses", headers=cashier).status_code == 403


def test_foreign_store_rejected(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "ex-d1")
    ceo_b = _onboard(client, db_session, "ex-d2")
    store_b = _store(client, ceo_b)
    resp = client.post(
        "/api/v1/expenses",
        headers=ceo_a,
        json={"store_id": store_b, "expense_type": "loader", "amount": "1.00", "description": "x"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def test_amount_must_be_positive(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "ex-e")
    store_id = _store(client, ceo)
    resp = client.post(
        "/api/v1/expenses",
        headers=ceo,
        json={"store_id": store_id, "expense_type": "other", "amount": "0", "description": "x"},
    )
    assert resp.status_code == 422


def test_description_required(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "ex-f")
    store_id = _store(client, ceo)
    resp = client.post(
        "/api/v1/expenses",
        headers=ceo,
        json={"store_id": store_id, "expense_type": "other", "amount": "1.00", "description": ""},
    )
    assert resp.status_code == 422


def test_invalid_expense_type_rejected(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "ex-g")
    store_id = _store(client, ceo)
    resp = client.post(
        "/api/v1/expenses",
        headers=ceo,
        json={"store_id": store_id, "expense_type": "bribery", "amount": "1.00", "description": "x"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Read scoping / financial-visibility rules
# ---------------------------------------------------------------------------
def test_accountant_query_store_id_is_a_real_filter_not_confinement(client: TestClient, db_session: Session) -> None:
    """Accountant is company-wide (unlike the old Seller model) — store_id
    is a real, honored filter for them, same as for CEO, not an ignored
    override of a fixed home store."""
    ceo = _onboard(client, db_session, "ex-h")
    own = _store(client, ceo, "Own")
    other = _store(client, ceo, "Other")
    # _seller() defaults to employee_role=cashier; create an accountant directly.
    resp = client.post(
        "/api/v1/employees",
        headers=ceo,
        json={"username": "acct-ex-h", "full_name": "Accountant", "password": "Acc12345!", "employee_role": "accountant"},
    )
    assert resp.status_code == 201, resp.text
    accountant = _bearer(client, "acct-ex-h", "Acc12345!", company_slug="ex-h")

    client.post("/api/v1/expenses", headers=ceo, json={"store_id": other, "expense_type": "fuel", "amount": "10.00", "description": "x"})
    own_expense = client.post(
        "/api/v1/expenses", headers=accountant, json={"store_id": own, "expense_type": "fuel", "amount": "20.00", "description": "y"}
    ).json()

    listed = client.get(f"/api/v1/expenses?store_id={other}", headers=accountant).json()
    assert listed["meta"]["total"] == 1
    assert listed["items"][0]["description"] == "x"

    listed_own = client.get(f"/api/v1/expenses?store_id={own}", headers=accountant).json()
    assert listed_own["meta"]["total"] == 1
    assert listed_own["items"][0]["id"] == own_expense["id"]


def test_ceo_filters_by_store_id(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "ex-i")
    store_a = _store(client, ceo, "Store A")
    store_b = _store(client, ceo, "Store B")
    client.post("/api/v1/expenses", headers=ceo, json={"store_id": store_a, "expense_type": "fuel", "amount": "10.00", "description": "x"})
    client.post("/api/v1/expenses", headers=ceo, json={"store_id": store_b, "expense_type": "fuel", "amount": "20.00", "description": "y"})

    listed = client.get(f"/api/v1/expenses?store_id={store_a}", headers=ceo).json()
    assert listed["meta"]["total"] == 1
    assert listed["items"][0]["store_id"] == store_a


def test_cross_company_detail_404(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "ex-j1")
    ceo_b = _onboard(client, db_session, "ex-j2")
    store_b = _store(client, ceo_b)
    created = client.post(
        "/api/v1/expenses",
        headers=ceo_b,
        json={"store_id": store_b, "expense_type": "other", "amount": "1.00", "description": "x"},
    ).json()

    assert client.get(f"/api/v1/expenses/{created['id']}", headers=ceo_a).status_code == 404
    listed_a = client.get("/api/v1/expenses", headers=ceo_a).json()
    assert listed_a["meta"]["total"] == 0


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------
def test_super_admin_no_access(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-ex-k")
    sa = _bearer(client, "root-ex-k", "Root12345!")
    assert client.get("/api/v1/expenses", headers=sa).status_code == 403
    assert client.post("/api/v1/expenses", headers=sa, json={"store_id": 1, "expense_type": "other", "amount": "1.00", "description": "x"}).status_code == 403
