"""
Pytest configuration and shared fixtures.

Critically, the test environment variables are set **before** the application
package is imported, because ``app.config``/``app.database`` read them at import
time (the engine and settings singletons are built on import).

The test database is an in-memory SQLite (``sqlite://``) using a StaticPool, so
the whole suite runs fast and leaves no files behind.
"""
from __future__ import annotations

import os
import tempfile

# --- Environment MUST be configured before importing the app ----------------
_TMP_UPLOADS = tempfile.mkdtemp(prefix="nailtest_uploads_")
os.environ.update(
    {
        "ENV": "development",          # non-prod so cookies aren't "secure" over http
        "SECRET_KEY": "test-secret-key-0123456789-abcdefghijklmnop",
        "DATABASE_URL": "sqlite://",   # in-memory + StaticPool
        "ADMIN_NAME": "Test Admin",
        "ADMIN_EMAIL": "admin@test.local",
        "ADMIN_PASSWORD": "TestPassw0rd!",
        "UPLOAD_DIR": _TMP_UPLOADS,
        "LOGIN_RATE_LIMIT_ATTEMPTS": "1000",  # avoid rate-limit flakiness in tests
    }
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


@pytest.fixture
def _clean_db():
    """Give every test a pristine schema (the in-memory DB persists per-process)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(_clean_db):
    """
    A TestClient whose context manager triggers the app lifespan, which runs
    ``init_db`` + ``ensure_admin`` — so the admin account exists for each test.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_client(client):
    """A logged-in admin client with the CSRF header primed for mutations."""
    resp = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, f"login failed: {resp.status_code} {resp.text}"
    client.headers.update({"X-CSRF-Token": resp.json()["csrf_token"]})
    return client
