"""
Security primitives: password hashing, JWT sessions, CSRF tokens, a simple
login rate-limiter, and the FastAPI auth dependencies.

Password hashing uses PBKDF2-HMAC-SHA256 from the Python standard library.
It is an OWASP-recommended, NIST-approved algorithm and requires **no compiled
dependencies**, which keeps installation bullet-proof on a fresh machine.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

# ---------------------------------------------------------------------------
# Password hashing (PBKDF2-HMAC-SHA256)
# ---------------------------------------------------------------------------
_PBKDF2_ALGO = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    """Hash a plaintext password into a self-describing string."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return (
        f"{_PBKDF2_ALGO}${_PBKDF2_ITERATIONS}$"
        f"{base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"
    )


def verify_password(password: str, stored: str) -> bool:
    """Constant-time verification of a password against a stored hash."""
    try:
        algo, iterations, salt_b64, hash_b64 = stored.split("$")
        if algo != _PBKDF2_ALGO:
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# JWT access tokens (stored in an httpOnly cookie)
# ---------------------------------------------------------------------------
JWT_ALGORITHM = "HS256"
COOKIE_NAME = "access_token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(subject), "iat": now, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


# ---------------------------------------------------------------------------
# CSRF tokens (double-submit cookie pattern)
# ---------------------------------------------------------------------------
_csrf_serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="csrf")
_CSRF_MAX_AGE = 60 * 60 * 24  # 24h


def issue_csrf_token() -> str:
    return _csrf_serializer.dumps(secrets.token_urlsafe(16))


def _csrf_token_valid(token: str) -> bool:
    try:
        _csrf_serializer.loads(token, max_age=_CSRF_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def verify_csrf(request: Request) -> None:
    """
    Dependency for state-changing admin API calls.

    Requires that the ``X-CSRF-Token`` header is present, valid, and equal to
    the ``csrf_token`` cookie (double-submit).  Safe methods are never checked.
    """
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    header_token = request.headers.get(CSRF_HEADER_NAME)
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if (
        not header_token
        or not cookie_token
        or not hmac.compare_digest(header_token, cookie_token)
        or not _csrf_token_valid(header_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing CSRF token."
        )


# ---------------------------------------------------------------------------
# Very small in-memory login rate limiter (per key, sliding window)
# ---------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            hits = [t for t in self._hits.get(key, []) if now - t < self.window]
            self._hits[key] = hits
            if len(hits) >= self.max_attempts:
                retry_after = int(self.window - (now - hits[0])) + 1
                return False, max(retry_after, 1)
            return True, 0

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._hits.setdefault(key, []).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)


login_rate_limiter = RateLimiter(
    settings.LOGIN_RATE_LIMIT_ATTEMPTS, settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
)


# ---------------------------------------------------------------------------
# Authentication helpers & dependencies
# ---------------------------------------------------------------------------
def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.lower().strip()))
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(
    access_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User | None:
    """Return the logged-in user from the session cookie, or None."""
    if not access_token:
        return None
    payload = decode_access_token(access_token)
    if not payload or payload.get("type") != "access":
        return None
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return None
    user = db.get(User, user_id)
    if user and user.is_active:
        return user
    return None


def require_admin_api(
    user: User | None = Depends(get_current_user),
    _: None = Depends(verify_csrf),
) -> User:
    """Dependency for admin JSON APIs: 401 if not authenticated as admin."""
    if user is None or user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return user


def set_auth_cookies(response, token: str, csrf_token: str) -> None:
    """Attach the session + CSRF cookies to a response."""
    secure = settings.is_production
    max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        max_age=max_age,
        httponly=False,  # must be readable by JS to echo back in the header
        secure=secure,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")
