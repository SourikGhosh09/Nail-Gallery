"""Authentication: login success/failure, logout, session, rate limiting."""
from __future__ import annotations

from app.security import RateLimiter
from conftest import ADMIN_EMAIL, ADMIN_PASSWORD


def test_login_success_sets_cookies_and_returns_csrf(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user"]["email"] == ADMIN_EMAIL
    assert body["user"]["role"] == "admin"
    assert body["csrf_token"]
    # Session cookie (httpOnly) and CSRF cookie are both set.
    assert "access_token" in resp.cookies
    assert "csrf_token" in resp.cookies


def test_login_wrong_password_is_rejected(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": "totally-wrong"},
    )
    assert resp.status_code == 401
    assert "access_token" not in resp.cookies


def test_login_unknown_email_is_rejected(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "nobody@test.local", "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 401


def test_login_malformed_email_is_validation_error(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "not-an-email", "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 422


def test_me_requires_authentication(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_user_when_authenticated(auth_client):
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == ADMIN_EMAIL


def test_logout_clears_session(auth_client):
    assert auth_client.post("/api/auth/logout").status_code == 200
    # After logout the session cookie is cleared, so /me is unauthorized again.
    assert auth_client.get("/api/auth/me").status_code == 401


def test_rate_limiter_blocks_after_max_attempts():
    """Unit test of the sliding-window limiter used to throttle logins."""
    limiter = RateLimiter(max_attempts=3, window_seconds=900)
    key = "1.2.3.4:admin@test.local"
    for _ in range(3):
        allowed, _ = limiter.check(key)
        assert allowed
        limiter.record_failure(key)
    allowed, retry_after = limiter.check(key)
    assert allowed is False
    assert retry_after >= 1
    # A successful login resets the counter.
    limiter.reset(key)
    allowed, _ = limiter.check(key)
    assert allowed
