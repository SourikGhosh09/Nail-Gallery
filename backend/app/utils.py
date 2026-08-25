"""Small, dependency-free helper functions used across the app."""
from __future__ import annotations

import re
import unicodedata
from urllib.parse import quote

from app.config import settings


def slugify(value: str) -> str:
    """Turn 'Royal Pink Chrome' into 'royal-pink-chrome' (URL-safe, ASCII)."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return value or "item"


def unique_slug(base: str, exists) -> str:
    """
    Return a slug based on ``base`` that is unique.

    ``exists`` is a callable ``(slug) -> bool`` telling us whether a slug is
    already taken.  Appends -2, -3, ... until a free slug is found.
    """
    slug = slugify(base)
    candidate = slug
    counter = 2
    while exists(candidate):
        candidate = f"{slug}-{counter}"
        counter += 1
    return candidate


def format_price(value) -> str:
    """Format a numeric price with the configured currency symbol."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        amount = 0.0
    # Show whole numbers without decimals, otherwise 2 dp.
    if amount == int(amount):
        body = f"{int(amount):,}"
    else:
        body = f"{amount:,.2f}"
    return f"{settings.CURRENCY_SYMBOL}{body}"


def whatsapp_link(design_name: str | None = None) -> str:
    """
    Build a WhatsApp deep link with a pre-filled enquiry message.

    Falls back to a generic message when no specific design is supplied.
    """
    if design_name:
        message = (
            f"Hello {settings.STUDIO_NAME} {settings.STUDIO_SUBTITLE}, "
            f"I am interested in {design_name}."
        )
    else:
        message = (
            f"Hello {settings.STUDIO_NAME} {settings.STUDIO_SUBTITLE}, "
            f"I would like to know more about your nail art."
        )
    return f"https://wa.me/{settings.WHATSAPP_NUMBER}?text={quote(message)}"
