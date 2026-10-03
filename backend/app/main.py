"""
Application entry point.

Creates the FastAPI application, wires up middleware (security headers, CORS),
mounts static files and uploaded media, includes all routers, registers
friendly error pages, and ensures the database + first admin exist on startup.

Run with:   uvicorn app.main:app --reload
"""
from __future__ import annotations

import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.config import settings, STATIC_DIR
from app.database import SessionLocal, init_db
from app.models import User
from app.routers import admin_api, admin_pages, auth, pages, public_api
from app.security import hash_password
from app.templating import csp_nonce_var, templates


def ensure_admin() -> None:
    """Create the first admin from environment variables if none exists."""
    from sqlalchemy import select

    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.role == "admin"))
        if existing is None:
            db.add(
                User(
                    name=settings.ADMIN_NAME,
                    email=settings.ADMIN_EMAIL.lower().strip(),
                    password_hash=hash_password(settings.ADMIN_PASSWORD),
                    role="admin",
                    is_active=True,
                )
            )
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.SKIP_DB_INIT:
        init_db()
        ensure_admin()
    yield


app = FastAPI(
    title=f"{settings.STUDIO_NAME} {settings.STUDIO_SUBTITLE} API",
    description="REST API powering the public nail-art catalogue and admin panel.",
    version=__version__,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ---- CORS (same-origin by default; adjust ALLOWED origins for a split host)-
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.BASE_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Security headers + per-request CSP nonce ------------------------------
@app.middleware("http")
async def security_headers(request: Request, call_next):
    nonce = secrets.token_urlsafe(16)
    token = csp_nonce_var.set(nonce)
    try:
        response = await call_next(request)
    finally:
        csp_nonce_var.reset(token)

    csp = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        f"script-src 'self' 'nonce-{nonce}'; "
        "connect-src 'self'; "
        "form-action 'self'"
    )
    response.headers.setdefault("Content-Security-Policy", csp)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    if settings.is_production:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


# ---- Static files & uploaded media -----------------------------------------
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
if settings.STORAGE_BACKEND == "local":
    app.mount("/media", StaticFiles(directory=str(settings.upload_path)), name="media")
else:
    from app.storage import read_image
    from fastapi import HTTPException
    from fastapi.responses import Response
    from pathlib import Path
    import mimetypes

    @app.get("/media/{filename}", include_in_schema=False)
    def blob_media(filename: str, request: Request):
        if Path(filename).name != filename or Path(filename).suffix.lower() not in settings.allowed_extensions:
            raise HTTPException(status_code=404, detail="Photo not found.")
        from sqlalchemy import select, or_
        from app.models import NailArt, NailArtPhoto, Category, Status
        from app.security import decode_access_token, COOKIE_NAME
        with SessionLocal() as db:
            published = db.scalar(select(NailArt.id).join(NailArt.category).where(
                NailArt.status == Status.ACTIVE, Category.status == Status.ACTIVE,
                or_(NailArt.image_path == filename, NailArt.photos.any(NailArtPhoto.image_path == filename)),
            ).limit(1))
            if published is None:
                payload = decode_access_token(request.cookies.get(COOKIE_NAME, ""))
                subject = str(payload.get("sub", "")) if payload else ""
                admin = db.get(User, int(subject)) if subject.isdigit() else None
                if admin is None or not admin.is_active or admin.role != "admin":
                    raise HTTPException(status_code=404, detail="Photo not found.")
        try:
            data = read_image(filename)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Photo not found.")
        return Response(data, media_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
                        headers={"Cache-Control": "private, no-store"})

# ---- Routers ---------------------------------------------------------------
app.include_router(auth.router)
app.include_router(public_api.router)
app.include_router(admin_api.router)
app.include_router(admin_pages.router)
app.include_router(pages.router)


# ---- Friendly error handling -----------------------------------------------
def _wants_json(request: Request) -> bool:
    path = request.url.path
    return path.startswith("/api") or "application/json" in request.headers.get("accept", "")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if _wants_json(request):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    if exc.status_code == 404:
        return templates.TemplateResponse(
            request, "public/404.html",
            {"active_page": "", "message": "The page you are looking for could not be found."},
            status_code=404,
        )
    return templates.TemplateResponse(
        request, "public/error.html",
        {"active_page": "", "status_code": exc.status_code, "message": str(exc.detail)},
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Build a clean, JSON-serialisable field->message map. (Raw ``exc.errors()``
    # can embed the original ValueError in ``ctx``, which is not serialisable and
    # would otherwise crash the response with a 500.)
    errors: dict[str, str] = {}
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path")]
        field = ".".join(loc) or "field"
        errors[field] = err.get("msg", "Invalid value.")
    return JSONResponse(
        status_code=422,
        content={"detail": {"message": "Validation failed.", "errors": errors}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak internals to the client.
    if _wants_json(request):
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})
    return templates.TemplateResponse(
        request, "public/error.html",
        {"active_page": "", "status_code": 500, "message": "Something went wrong. Please try again."},
        status_code=500,
    )
