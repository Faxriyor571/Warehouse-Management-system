"""Infrastructure regression test for RequestValidationError serialization.

A schema field/model validator that raises ``ValueError`` produces an
``errors()`` entry whose ``ctx`` holds the raw exception object, which is not
JSON-serializable. The app's RequestValidationError handler must pass the
errors through ``jsonable_encoder`` so such a request returns HTTP 422 (with
the usual body shape) instead of crashing the handler into a 500.
"""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_validator_value_error_returns_422_not_500(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # The Customer schema's phone field_validator raises ValueError on a
    # malformed phone — a real, reachable path that exercises the handler.
    resp = client.post(
        "/api/v1/customers",
        headers=auth_headers,
        json={"full_name": "Bad Phone", "phone": "!!!not-a-phone!!!"},
    )

    assert resp.status_code == 422  # previously crashed to 500

    # Response body shape is unchanged: a top-level detail message plus a
    # list of structured validation errors.
    body = resp.json()
    assert body["detail"] == "Ma'lumotlar noto'g'ri"
    assert isinstance(body["errors"], list) and body["errors"]
    err = body["errors"][0]
    assert err["loc"][-1] == "phone"
    assert "Telefon raqami noto'g'ri formatda" in err["msg"]
