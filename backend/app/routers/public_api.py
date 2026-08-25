"""Public REST API (no authentication) — categories and nail-art catalogue."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import serialize_category, serialize_nail
from app.services import (
    DEFAULT_SORT,
    active_categories_with_counts,
    get_nail_by_slug_or_id,
    list_nail_arts,
    related_designs,
)

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    cats = active_categories_with_counts(db)
    return {"items": [serialize_category(c) for c in cats]}


@router.get("/nail-arts")
def get_nail_arts(
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=140),
    sort: str = Query(default=DEFAULT_SORT),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=60),
):
    result = list_nail_arts(
        db, search=search, category=category, sort=sort, page=page, page_size=page_size
    )
    return {
        "items": [serialize_nail(n) for n in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "pages": result.pages,
        "has_next": result.has_next,
        "has_prev": result.has_prev,
    }


@router.get("/nail-arts/{identifier}")
def get_nail_art(identifier: str, db: Session = Depends(get_db)):
    nail = get_nail_by_slug_or_id(db, identifier)
    if nail is None:
        raise HTTPException(status_code=404, detail="Nail art not found.")
    return {
        "item": serialize_nail(nail),
        "related": [serialize_nail(n) for n in related_designs(db, nail)],
    }
