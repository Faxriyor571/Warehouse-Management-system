"""Tests for the multi-tenant Units module (Phase 6 — catalog migration).

Writes are CEO-only; reads are CEO/Seller; Super Admin has no access. The
legacy single-tenant admin operates in the NULL-company scope via the shared
catalogue compat shim (also covered by the legacy test_stock_flow suite).
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


def test_ceo_creates_unit_with_conversion(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "unit-a")
    resp = client.post(
        "/api/v1/units", headers=ceo, json={"name": "Qop", "short_name": "qop", "conversion_factor": "50"}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Qop"
    assert body["short_name"] == "qop"
    assert body["conversion_factor"] == "50.000"


def test_duplicate_unit_name_within_company_rejected(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "unit-b")
    client.post("/api/v1/units", headers=ceo, json={"name": "Dona", "short_name": "dona"})
    dup = client.post("/api/v1/units", headers=ceo, json={"name": "Dona", "short_name": "d"})
    assert dup.status_code == 409


def test_two_companies_share_unit_name(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "unit-c1")
    ceo_b = _onboard(client, db_session, "unit-c2")
    ra = client.post("/api/v1/units", headers=ceo_a, json={"name": "Litr", "short_name": "l"})
    rb = client.post("/api/v1/units", headers=ceo_b, json={"name": "Litr", "short_name": "l"})
    assert ra.status_code == 201
    assert rb.status_code == 201


def test_list_get_update(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "unit-d")
    created = client.post("/api/v1/units", headers=ceo, json={"name": "Metr", "short_name": "m"}).json()

    listed = client.get("/api/v1/units", headers=ceo).json()
    assert {u["name"] for u in listed["items"]} == {"Metr"}

    got = client.get(f"/api/v1/units/{created['id']}", headers=ceo)
    assert got.status_code == 200 and got.json()["name"] == "Metr"

    upd = client.put(f"/api/v1/units/{created['id']}", headers=ceo, json={"short_name": "mtr"})
    assert upd.status_code == 200 and upd.json()["short_name"] == "mtr"


def test_cross_company_access_404(client: TestClient, db_session: Session) -> None:
    ceo_a = _onboard(client, db_session, "unit-e1")
    ceo_b = _onboard(client, db_session, "unit-e2")
    unit_b = client.post("/api/v1/units", headers=ceo_b, json={"name": "Quti", "short_name": "q"}).json()

    assert client.get(f"/api/v1/units/{unit_b['id']}", headers=ceo_a).status_code == 404
    assert client.put(f"/api/v1/units/{unit_b['id']}", headers=ceo_a, json={"short_name": "x"}).status_code == 404
    assert client.delete(f"/api/v1/units/{unit_b['id']}", headers=ceo_a).status_code == 404


def test_seller_read_only(client: TestClient, db_session: Session) -> None:
    ceo = _onboard(client, db_session, "unit-f")
    client.post("/api/v1/units", headers=ceo, json={"name": "Karobka", "short_name": "kor"})
    seller = _make_seller(client, ceo, "unit-f", "seller-unit-f")

    assert client.get("/api/v1/units", headers=seller).status_code == 200
    assert client.post("/api/v1/units", headers=seller, json={"name": "Nope", "short_name": "n"}).status_code == 403


def test_super_admin_no_access(client: TestClient, db_session: Session) -> None:
    _make_super_admin(db_session, "root-unit-g")
    sa = _bearer(client, "root-unit-g", "Root12345!")
    assert client.get("/api/v1/units", headers=sa).status_code == 403
    assert client.post("/api/v1/units", headers=sa, json={"name": "X", "short_name": "x"}).status_code == 403


def test_legacy_admin_sees_seeded_units(client: TestClient, auth_headers: dict[str, str]) -> None:
    """The seeded NULL-company units remain visible to the legacy admin via the
    compat shim (this is what test_stock_flow relies on)."""
    listed = client.get("/api/v1/units", headers=auth_headers).json()
    assert listed["meta"]["total"] >= 1
