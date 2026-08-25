"""Authentication API: login, logout, and current-user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, UserOut
from app.security import (
    authenticate_user,
    clear_auth_cookies,
    create_access_token,
    get_current_user,
    issue_csrf_token,
    login_rate_limiter,
    set_auth_cookies,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _client_key(request: Request, email: str) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")
    return f"{ip}:{email.lower()}"


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    key = _client_key(request, payload.email)
    allowed, retry_after = login_rate_limiter.check(key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        login_rate_limiter.record_failure(key)
        # Deliberately vague message — do not reveal which field was wrong.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid e-mail or password.",
        )

    login_rate_limiter.reset(key)
    token = create_access_token(user.id)
    csrf = issue_csrf_token()
    set_auth_cookies(response, token, csrf)
    return {"user": UserOut.model_validate(user).model_dump(), "csrf_token": csrf}


@router.post("/logout")
def logout(response: Response):
    clear_auth_cookies(response)
    return {"detail": "Logged out."}


@router.get("/me")
def me(user: User | None = Depends(get_current_user)):
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated."
        )
    return {"user": UserOut.model_validate(user).model_dump()}
