"""Tests for the multi-tenant Categories module (Phase 5).

Writes are CEO-only; reads are CEO/Seller; Super Admin (new role) has no
access. A transitional compatibility shim (app/auth/legacy_compat.py) also
admits the legacy single-tenant admin, operating in the NULL-company scope;
that path is covered here and by the legacy test_stock_flow suite.
"""
from __future__ import annotations

from unittest.mock import patch

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


def _make_seller(client: TestClient, db: Session, ceo: dict[str, str], slug: str, username: str) -> dict[str, str]:
    store = client.post("/api/v1/stores", headers=ceo, json={"name": "Store"}).json()["id"]
    resp = client.post(
        "/api/v1/employees",
        headers=ceo,
        json={"username": username, "full_name": "Seller", "password": "Sell12345!", "store_id": store},
    )
    assert resp.status_code == 201, resp.text
    return _bearer(client, username, "Sell12345!", company_slug=slug)


# ---------------------------------------------------------------------------
# CEO CRUD + uniqueness
# ---------------------------------------------------------------------------
def test_ceo_creates_category(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "cat-a")
    resp = client.post("/api/v1/categories", headers=ceo, json={"name": "O'g'itlar"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["name"] == "O'g'itlar"


def test_duplicate_name_within_company_rejected(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "cat-b")
    client.post("/api/v1/categories", headers=ceo, json={"name": "Urug'lar"})
    dup = client.post("/api/v1/categories", headers=ceo, json={"name": "Urug'lar"})
    assert dup.status_code == 409


def test_race_between_check_and_insert_returns_409_not_500(
    client: TestClient, db_session: Session
) -> None:
    """Two requests racing past create_category's check-then-insert window
    (e.g. a double form-submit) must both fail cleanly with 409 — not crash
    with a raw 500 from the database's own unique constraint. Simulated by
    patching the pre-check to always report "no existing row", so both
    calls fall through to the real INSERT and the second one collides.
    """
    ceo = _onboard(client, db_session, "cat-race")
    with patch("app.services.category_service.category_crud.get_by_name_for_company", return_value=None):
        first = client.post("/api/v1/categories", headers=ceo, json={"name": "Race Condition"})
        second = client.post("/api/v1/categories", headers=ceo, json={"name": "Race Condition"})
    assert first.status_code == 201, first.text
    assert second.status_code == 409, second.text
    assert "detail" in second.json()


def test_two_companies_share_category_name(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "cat-c1")
    ceo_b = _onboard(client, db_session, "cat-c2")
    ra = client.post("/api/v1/categories", headers=ceo_a, json={"name": "Shared"})
    rb = client.post("/api/v1/categories", headers=ceo_b, json={"name": "Shared"})
    assert ra.status_code == 201
    assert rb.status_code == 201


def test_list_and_get_and_update(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "cat-d")
    created = client.post("/api/v1/categories", headers=ceo, json={"name": "One"}).json()

    listed = client.get("/api/v1/categories", headers=ceo).json()
    assert {c["name"] for c in listed["items"]} == {"One"}

    got = client.get(f"/api/v1/categories/{created['id']}", headers=ceo)
    assert got.status_code == 200 and got.json()["name"] == "One"

    upd = client.put(f"/api/v1/categories/{created['id']}", headers=ceo, json={"name": "Renamed"})
    assert upd.status_code == 200 and upd.json()["name"] == "Renamed"


def test_delete_soft_excludes_from_list_and_get(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "cat-e")
    created = client.post("/api/v1/categories", headers=ceo, json={"name": "Gone"}).json()

    assert client.delete(f"/api/v1/categories/{created['id']}", headers=ceo).status_code == 200
    assert client.get(f"/api/v1/categories/{created['id']}", headers=ceo).status_code == 404
    listed = client.get("/api/v1/categories", headers=ceo).json()
    assert all(c["id"] != created["id"] for c in listed["items"])


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------
def test_cross_company_access_404(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "cat-f1")
    ceo_b = _onboard(client, db_session, "cat-f2")
    cat_b = client.post("/api/v1/categories", headers=ceo_b, json={"name": "B-Cat"}).json()

    assert client.get(f"/api/v1/categories/{cat_b['id']}", headers=ceo_a).status_code == 404
    assert client.put(f"/api/v1/categories/{cat_b['id']}", headers=ceo_a, json={"name": "Hack"}).status_code == 404
    assert client.delete(f"/api/v1/categories/{cat_b['id']}", headers=ceo_a).status_code == 404
    # A A-side list never shows B's category.
    listed = client.get("/api/v1/categories", headers=ceo_a).json()
    assert all(c["name"] != "B-Cat" for c in listed["items"])


# ---------------------------------------------------------------------------
# Authorization matrix
# ---------------------------------------------------------------------------
def test_seller_read_only(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "cat-g")
    client.post("/api/v1/categories", headers=ceo, json={"name": "Visible"})
    seller = _make_seller(client, db_session, ceo, "cat-g", "seller-cat-g")

    # Seller can read.
    assert client.get("/api/v1/categories", headers=seller).status_code == 200
    # Seller cannot write.
    assert client.post("/api/v1/categories", headers=seller, json={"name": "Nope"}).status_code == 403


def test_super_admin_no_access(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-cat-h")
    sa = _bearer(client, "root-cat-h", "Root12345!")
    assert client.get("/api/v1/categories", headers=sa).status_code == 403
    assert client.post("/api/v1/categories", headers=sa, json={"name": "X"}).status_code == 403


def test_seller_sees_only_own_company_categories(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "cat-i1")
    ceo_b = _onboard(client, db_session, "cat-i2")
    client.post("/api/v1/categories", headers=ceo_a, json={"name": "A-Only"})
    client.post("/api/v1/categories", headers=ceo_b, json={"name": "B-Only"})
    seller_a = _make_seller(client, db_session, ceo_a, "cat-i1", "seller-cat-i1")

    listed = client.get("/api/v1/categories", headers=seller_a).json()
    names = {c["name"] for c in listed["items"]}
    assert names == {"A-Only"}


# ---------------------------------------------------------------------------
# Transitional legacy-admin compatibility (NULL-company scope)
# ---------------------------------------------------------------------------
def test_legacy_admin_operates_in_null_scope(client: TestClient, auth_headers: dict[str, str]) -> None:
    """The seeded legacy admin (is_superuser) can still manage categories via
    the transitional compat shim; it operates in the NULL-company scope,
    isolated from any tenant company's categories."""
    created = client.post("/api/v1/categories", headers=auth_headers, json={"name": "Legacy Cat"})
    assert created.status_code == 201, created.text
    listed = client.get("/api/v1/categories", headers=auth_headers).json()
    assert any(c["name"] == "Legacy Cat" for c in listed["items"])
