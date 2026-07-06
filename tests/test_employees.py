"""Tests for the Employees (Sellers) module (Sprint 1, Phase 4).

CEO-only, company-scoped management of Seller accounts. Super Admin and
Seller have no access.
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


def _seller_payload(username: str, store_id: int, **over) -> dict:
    body = {
        "username": username,
        "full_name": "Seller Person",
        "password": "Sell12345!",
        "email": None,
        "phone": None,
        "store_id": store_id,
    }
    body.update(over)
    return body


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
def test_create_seller(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "emp-a")
    store_id = _create_store(client, ceo, "Main")
    resp = client.post("/api/v1/employees", headers=ceo, json=_seller_payload("sardor", store_id))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["role"] == "seller"
    assert body["store_id"] == store_id
    assert body["store_name"] == "Main"
    assert body["is_active"] is True
    assert "password" not in body and "hashed_password" not in body

    # The seller can log in via the company slug.
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "sardor", "password": "Sell12345!", "company_slug": "emp-a"},
    )
    assert login.status_code == 200


def test_create_seller_store_from_other_company_rejected(client: TestClient, db_session: Session) -> None:
    ceo_a, _ = _onboard(client, db_session, "emp-b1")
    ceo_b, _ = _onboard(client, db_session, "emp-b2")
    store_b = _create_store(client, ceo_b, "B-Store")

    # CEO A assigns a seller to company B's store → 404 (store not in A's company).
    resp = client.post("/api/v1/employees", headers=ceo_a, json=_seller_payload("xseller", store_b))
    assert resp.status_code == 404


def test_create_seller_missing_store_id_rejected(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "emp-c")
    body = {"username": "yseller", "full_name": "No Store", "password": "Sell12345!"}
    resp = client.post("/api/v1/employees", headers=ceo, json=body)
    assert resp.status_code == 422


def test_create_seller_duplicate_username_within_company_rejected(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "emp-d")
    store_id = _create_store(client, ceo)
    client.post("/api/v1/employees", headers=ceo, json=_seller_payload("dup", store_id))
    resp = client.post("/api/v1/employees", headers=ceo, json=_seller_payload("dup", store_id))
    assert resp.status_code == 409


def test_two_companies_share_seller_username(client: TestClient, db_session: Session) -> None:
    """Tenant isolation: each company may have a seller with the same username."""
    ceo_a, _ = _onboard(client, db_session, "emp-e1")
    ceo_b, _ = _onboard(client, db_session, "emp-e2")
    store_a = _create_store(client, ceo_a)
    store_b = _create_store(client, ceo_b)

    ra = client.post("/api/v1/employees", headers=ceo_a, json=_seller_payload("seller", store_a))
    rb = client.post("/api/v1/employees", headers=ceo_b, json=_seller_payload("seller", store_b))
    assert ra.status_code == 201
    assert rb.status_code == 201


# ---------------------------------------------------------------------------
# List / Get — tenant isolation
# ---------------------------------------------------------------------------
def test_list_only_own_company_sellers(client: TestClient, db_session: Session) -> None:
    ceo_a, _ = _onboard(client, db_session, "emp-f1")
    ceo_b, _ = _onboard(client, db_session, "emp-f2")
    store_a = _create_store(client, ceo_a)
    store_b = _create_store(client, ceo_b)
    client.post("/api/v1/employees", headers=ceo_a, json=_seller_payload("a-seller", store_a))
    client.post("/api/v1/employees", headers=ceo_b, json=_seller_payload("b-seller", store_b))

    listed = client.get("/api/v1/employees", headers=ceo_a).json()
    usernames = {item["username"] for item in listed["items"]}
    assert usernames == {"a-seller"}  # only company A's seller; not CEO, not B's seller
    assert all(item["role"] == "seller" for item in listed["items"])


def test_get_other_company_seller_404(client: TestClient, db_session: Session) -> None:
    ceo_a, _ = _onboard(client, db_session, "emp-g1")
    ceo_b, _ = _onboard(client, db_session, "emp-g2")
    store_b = _create_store(client, ceo_b)
    created_b = client.post("/api/v1/employees", headers=ceo_b, json=_seller_payload("bob", store_b)).json()

    assert client.get(f"/api/v1/employees/{created_b['id']}", headers=ceo_a).status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------
def test_update_reassign_store_within_company(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "emp-h")
    s1 = _create_store(client, ceo, "One")
    s2 = _create_store(client, ceo, "Two")
    seller = client.post("/api/v1/employees", headers=ceo, json=_seller_payload("mover", s1)).json()

    resp = client.put(f"/api/v1/employees/{seller['id']}", headers=ceo, json={"store_id": s2})
    assert resp.status_code == 200
    assert resp.json()["store_id"] == s2
    assert resp.json()["store_name"] == "Two"


def test_update_reassign_to_other_company_store_404(client: TestClient, db_session: Session) -> None:
    ceo_a, _ = _onboard(client, db_session, "emp-i1")
    ceo_b, _ = _onboard(client, db_session, "emp-i2")
    store_a = _create_store(client, ceo_a)
    store_b = _create_store(client, ceo_b)
    seller = client.post("/api/v1/employees", headers=ceo_a, json=_seller_payload("sseller", store_a)).json()

    resp = client.put(f"/api/v1/employees/{seller['id']}", headers=ceo_a, json={"store_id": store_b})
    assert resp.status_code == 404


def test_update_explicit_null_store_id_rejected(client: TestClient, db_session: Session) -> None:
    """CHANGE 2: explicit null store_id is a validation error, not a no-op."""
    ceo, _ = _onboard(client, db_session, "emp-j")
    store_id = _create_store(client, ceo)
    seller = client.post("/api/v1/employees", headers=ceo, json=_seller_payload("sseller", store_id)).json()

    resp = client.put(f"/api/v1/employees/{seller['id']}", headers=ceo, json={"store_id": None})
    assert resp.status_code == 422


def test_update_omitted_store_id_unchanged(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "emp-k")
    store_id = _create_store(client, ceo, "Keep")
    seller = client.post("/api/v1/employees", headers=ceo, json=_seller_payload("sseller", store_id)).json()

    resp = client.put(f"/api/v1/employees/{seller['id']}", headers=ceo, json={"full_name": "Renamed"})
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Renamed"
    assert resp.json()["store_id"] == store_id  # unchanged
    assert resp.json()["store_name"] == "Keep"


# ---------------------------------------------------------------------------
# Activate / Deactivate
# ---------------------------------------------------------------------------
def test_deactivate_blocks_login_and_activate_restores(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "emp-l")
    store_id = _create_store(client, ceo)
    seller = client.post("/api/v1/employees", headers=ceo, json=_seller_payload("worker", store_id)).json()

    deact = client.post(f"/api/v1/employees/{seller['id']}/deactivate", headers=ceo)
    assert deact.status_code == 200
    assert deact.json()["is_active"] is False

    blocked = client.post(
        "/api/v1/auth/login",
        data={"username": "worker", "password": "Sell12345!", "company_slug": "emp-l"},
    )
    assert blocked.status_code == 401

    act = client.post(f"/api/v1/employees/{seller['id']}/activate", headers=ceo)
    assert act.status_code == 200
    assert act.json()["is_active"] is True

    restored = client.post(
        "/api/v1/auth/login",
        data={"username": "worker", "password": "Sell12345!", "company_slug": "emp-l"},
    )
    assert restored.status_code == 200


# ---------------------------------------------------------------------------
# Reset password
# ---------------------------------------------------------------------------
def test_reset_password(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "emp-m")
    store_id = _create_store(client, ceo)
    seller = client.post("/api/v1/employees", headers=ceo, json=_seller_payload("pwseller", store_id)).json()

    # Seller logs in and gets a refresh token before the reset.
    first = client.post(
        "/api/v1/auth/login",
        data={"username": "pwseller", "password": "Sell12345!", "company_slug": "emp-m"},
    ).json()

    resp = client.post(
        f"/api/v1/employees/{seller['id']}/reset-password", headers=ceo, json={"new_password": "NewPass123!"}
    )
    assert resp.status_code == 204

    # Old password no longer works; new one does.
    assert client.post(
        "/api/v1/auth/login",
        data={"username": "pwseller", "password": "Sell12345!", "company_slug": "emp-m"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        data={"username": "pwseller", "password": "NewPass123!", "company_slug": "emp-m"},
    ).status_code == 200

    # Documented behavior: reset does NOT revoke existing sessions — the
    # pre-reset refresh token is still usable (spec only "recommends" revoking).
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert refreshed.status_code == 200


# ---------------------------------------------------------------------------
# Authorization matrix
# ---------------------------------------------------------------------------
def test_seller_cannot_access_employees(client: TestClient, db_session: Session) -> None:
    ceo, _ = _onboard(client, db_session, "emp-n")
    store_id = _create_store(client, ceo)
    client.post("/api/v1/employees", headers=ceo, json=_seller_payload("insider", store_id))
    seller = _bearer(client, "insider", "Sell12345!", company_slug="emp-n")

    assert client.get("/api/v1/employees", headers=seller).status_code == 403
    assert client.post("/api/v1/employees", headers=seller, json=_seller_payload("xseller", store_id)).status_code == 403


def test_super_admin_cannot_access_employees(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-emp-o")
    sa = _bearer(client, "root-emp-o", "Root12345!")
    assert client.get("/api/v1/employees", headers=sa).status_code == 403
    assert client.post("/api/v1/employees", headers=sa, json={"username": "zseller", "full_name": "Z", "password": "Zz12345!", "store_id": 1}).status_code == 403


def test_legacy_admin_cannot_access_employees(client: TestClient, auth_headers: dict[str, str]) -> None:
    """The legacy is_superuser bypass must not grant access to the new module."""
    assert client.get("/api/v1/employees", headers=auth_headers).status_code == 403
