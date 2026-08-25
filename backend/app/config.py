"""
Centralised application configuration.

All settings are loaded from environment variables (and the local ``.env``
file during development) using pydantic-settings.  Import the singleton
``settings`` object anywhere in the app:

    from app.config import settings
    print(settings.STUDIO_NAME)

Nothing secret is ever hard-coded in source — everything lives in ``.env``.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Key filesystem locations, all derived from THIS file's own location so the
# app works no matter which directory it is launched from:
#
#   <project root>/
#   ├─ backend/            the Python server
#   │  └─ app/config.py    (this file)
#   └─ frontend/           what the browser sees
#      ├─ templates/       Jinja2 HTML
#      └─ static/          CSS / JS / images
# ---------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent        # .../backend/app
BACKEND_DIR = APP_DIR.parent                      # .../backend
PROJECT_ROOT = BACKEND_DIR.parent                 # the project root
FRONTEND_DIR = PROJECT_ROOT / "frontend"
TEMPLATES_DIR = FRONTEND_DIR / "templates"
STATIC_DIR = FRONTEND_DIR / "static"

# Relative settings (the .env file, the uploads folder, a relative SQLite
# database path) are all resolved against the project root.
BASE_DIR = PROJECT_ROOT


class Settings(BaseSettings):
    """Strongly-typed application settings, validated at startup."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---- Environment --------------------------------------------------------
    ENV: str = "development"

    # ---- Security -----------------------------------------------------------
    SECRET_KEY: str = "change-me-to-a-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    # ---- First admin account ------------------------------------------------
    ADMIN_NAME: str = "Studio Admin"
    ADMIN_EMAIL: str = "admin@missuniverse.local"
    ADMIN_PASSWORD: str = "ChangeMe!123"

    # ---- Database -----------------------------------------------------------
    DATABASE_URL: str = "sqlite:///./nailstudio.db"

    # ---- Studio branding ----------------------------------------------------
    STUDIO_NAME: str = "Miss Universe"
    STUDIO_SUBTITLE: str = "Nail Art Studio"
    STUDIO_TAGLINE: str = "Elegance at Your Fingertips"
    STUDIO_DESCRIPTION: str = (
        "Premium bespoke nail art designs — bridal, chrome, French, 3D and "
        "more. Discover your perfect nail style."
    )

    # ---- Contact & WhatsApp -------------------------------------------------
    WHATSAPP_NUMBER: str = "919876543210"
    CONTACT_EMAIL: str = "hello@missuniverse.local"
    CONTACT_PHONE: str = "+91 98765 43210"
    CONTACT_ADDRESS: str = "123 Glamour Lane, Your City"
    INSTAGRAM_URL: str = "https://instagram.com/"
    FACEBOOK_URL: str = "https://facebook.com/"

    # ---- Currency -----------------------------------------------------------
    CURRENCY_CODE: str = "INR"
    CURRENCY_SYMBOL: str = "₹"

    # ---- Public base URL ----------------------------------------------------
    BASE_URL: str = "http://localhost:8000"

    # ---- Image uploads ------------------------------------------------------
    UPLOAD_DIR: str = "storage/uploads"
    MAX_UPLOAD_MB: int = 5
    ALLOWED_IMAGE_EXTENSIONS: str = ".jpg,.jpeg,.png,.webp"

    # ---- Login rate limiting ------------------------------------------------
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 900

    # ---- Derived / helpers --------------------------------------------------
    @field_validator("WHATSAPP_NUMBER")
    @classmethod
    def _clean_whatsapp(cls, v: str) -> str:
        """Keep digits only — WhatsApp deep links require a bare number."""
        return "".join(ch for ch in v if ch.isdigit())

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() in {"production", "prod"}

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024

    @property
    def allowed_extensions(self) -> set[str]:
        return {
            e.strip().lower() if e.strip().startswith(".") else f".{e.strip().lower()}"
            for e in self.ALLOWED_IMAGE_EXTENSIONS.split(",")
            if e.strip()
        }

    @property
    def upload_path(self) -> Path:
        """Absolute path to the upload directory (created if missing)."""
        p = Path(self.UPLOAD_DIR)
        if not p.is_absolute():
            p = BASE_DIR / p
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Import-friendly singleton.
settings = get_settings()
