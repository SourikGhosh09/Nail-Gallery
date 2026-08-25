"""Shared test helpers (plain functions used across test modules)."""
from __future__ import annotations

import io

from PIL import Image


def make_png(color: tuple[int, int, int] = (200, 120, 130), size: tuple[int, int] = (64, 64)) -> bytes:
    """Return the bytes of a small, valid PNG image."""
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def create_category(client, name, description="", status="active"):
    """Create a category through the admin API. Returns the httpx Response."""
    return client.post(
        "/api/admin/categories",
        data={"name": name, "description": description, "status": status},
    )


def create_nail(
    client,
    name,
    category_id,
    price=500,
    status="active",
    description="A lovely, elegant nail design.",
    image: bytes | None = None,
    image_alt: str | None = None,
):
    """Create a nail art through the admin API. Returns the httpx Response."""
    data = {
        "name": name,
        "description": description,
        "price": str(price),
        "category_id": str(category_id),
        "status": status,
    }
    if image_alt is not None:
        data["image_alt"] = image_alt
    files = {"image": ("design.png", image, "image/png")} if image is not None else None
    return client.post("/api/admin/nail-arts", data=data, files=files)
