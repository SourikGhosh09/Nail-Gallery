"""
Pydantic schemas for request validation and response serialisation.

These provide the automatic input validation (a security requirement) and
shape the JSON returned by the REST API.  Plain ``str`` + a light regex is
used for e-mail so we avoid pulling in an extra dependency.
"""
from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import settings
from app.models import Category, NailArt, Status

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Enter a valid e-mail address.")
        return v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------
class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    status: Status = Status.ACTIVE

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Category name is required.")
        return v


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    status: Status | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Category name cannot be empty.")
        return v


# ---------------------------------------------------------------------------
# Nail art
# ---------------------------------------------------------------------------
class NailArtCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=5000)
    price: float = Field(ge=0)
    category_id: int = Field(gt=0)
    status: Status = Status.ACTIVE
    image_alt: str | None = Field(default=None, max_length=255)

    @field_validator("name", "description")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field is required.")
        return v


class NailArtUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    price: float | None = Field(default=None, ge=0)
    category_id: int | None = Field(default=None, gt=0)
    status: Status | None = None
    image_alt: str | None = Field(default=None, max_length=255)


class StatusUpdate(BaseModel):
    status: Status


# ---------------------------------------------------------------------------
# Serialisation helpers (ORM object -> plain dict for JSON responses)
# ---------------------------------------------------------------------------
def image_url(image_path: str | None) -> str | None:
    if not image_path:
        return None
    return f"/media/{image_path.lstrip('/')}"


def serialize_category(c: Category, *, include_counts: bool = True) -> dict:
    data = {
        "id": c.id,
        "name": c.name,
        "slug": c.slug,
        "description": c.description,
        "status": c.status.value,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }
    if include_counts:
        data["design_count"] = c.design_count
        data["active_design_count"] = c.active_design_count
    return data


def serialize_nail(n: NailArt, *, with_category: bool = True) -> dict:
    data = {
        "id": n.id,
        "name": n.name,
        "slug": n.slug,
        "description": n.description,
        "price": float(n.price),
        "price_display": f"{settings.CURRENCY_SYMBOL}{float(n.price):,.0f}"
        if float(n.price) == int(float(n.price))
        else f"{settings.CURRENCY_SYMBOL}{float(n.price):,.2f}",
        "category_id": n.category_id,
        "image_path": n.image_path,
        "image_url": image_url(n.image_path),
        "image_alt": n.image_alt or n.name,
        "status": n.status.value,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }
    if with_category and n.category is not None:
        data["category"] = {
            "id": n.category.id,
            "name": n.category.name,
            "slug": n.category.slug,
        }
    return data
