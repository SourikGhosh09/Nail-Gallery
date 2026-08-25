"""Admin API is locked down: auth required, CSRF required for mutations."""
from __future__ import annotations

import pytest

from conftest import ADMIN_EMAIL, ADMIN_PASSWORD


def _login_without_csrf_header(client):
    """Log in (cookies set) but deliberately do NOT prime the CSRF header."""
    resp = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    return resp.json()["csrf_token"]


def test_unauthenticated_dashboard_is_401(client):
    assert client.get("/api/admin/dashboard").status_code == 401


def test_unauthenticated_list_endpoints_are_401(client):
    assert client.get("/api/admin/nail-arts").status_code == 401
    assert client.get("/api/admin/categories").status_code == 401


@pytest.mark.parametrize(
    "method,url",
    [
        ("post", "/api/admin/categories"),
        ("put", "/api/admin/categories/1"),
        ("delete", "/api/admin/categories/1"),
        ("post", "/api/admin/nail-arts"),
        ("put", "/api/admin/nail-arts/1"),
        ("delete", "/api/admin/nail-arts/1"),
        ("patch", "/api/admin/nail-arts/1/status"),
    ],
)
def test_unauthenticated_mutations_are_rejected(client, method, url):
    # Mutations are rejected before any work happens: CSRF check yields 403,
    # missing session yields 401 — either way, never allowed through.
    resp = getattr(client, method)(url)
    assert resp.status_code in (401, 403)


def test_authenticated_without_csrf_header_is_forbidden(client):
    _login_without_csrf_header(client)
    # Cookies are present, but no X-CSRF-Token header -> double-submit fails.
    resp = client.post("/api/admin/categories", data={"name": "No CSRF"})
    assert resp.status_code == 403


def test_authenticated_with_mismatched_csrf_is_forbidden(client):
    _login_without_csrf_header(client)
    resp = client.post(
        "/api/admin/categories",
        data={"name": "Bad CSRF"},
        headers={"X-CSRF-Token": "not-the-real-token"},
    )
    assert resp.status_code == 403


def test_authenticated_with_valid_csrf_is_allowed(auth_client):
    # Sanity check that the primed CSRF header actually lets a mutation through.
    resp = auth_client.post("/api/admin/categories", data={"name": "Allowed"})
    assert resp.status_code == 201, resp.text
