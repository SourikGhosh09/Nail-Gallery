"""
Shared Jinja2 templating configuration.

Common values (studio branding, currency helpers, the WhatsApp link builder,
the current year, sort options) are registered as template globals so every
template can use them without the routers having to pass them each time.
"""
from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone

from fastapi.templating import Jinja2Templates

from app.config import settings, TEMPLATES_DIR
from app.schemas import image_url
from app.services import SORT_LABELS
from app.utils import format_price, whatsapp_link

# Per-request CSP nonce, set by the security-headers middleware and read by
# templates for the few inline <script> tags we emit (structured data).
csp_nonce_var: ContextVar[str] = ContextVar("csp_nonce", default="")


def csp_nonce() -> str:
    return csp_nonce_var.get()


templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

templates.env.globals.update(
    cfg=settings,
    whatsapp_link=whatsapp_link,
    format_price=format_price,
    media_url=image_url,
    sort_labels=SORT_LABELS,
    csp_nonce=csp_nonce,
    current_year=datetime.now(timezone.utc).year,
)
