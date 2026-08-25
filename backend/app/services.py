"""
Catalogue query service.

A single, well-tested function builds the nail-art listing query used by both
the public REST API and the server-rendered catalogue page (DRY).  It handles
case-insensitive partial search, category filtering, sorting and pagination.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, contains_eager

from app.models import Category, NailArt, Status

# Allowed sort keys mapped to ORDER BY expressions.
SORT_OPTIONS = {
    "newest": (NailArt.created_at.desc(), NailArt.id.desc()),
    "oldest": (NailArt.created_at.asc(), NailArt.id.asc()),
    "price_asc": (NailArt.price.asc(), NailArt.id.asc()),
    "price_desc": (NailArt.price.desc(), NailArt.id.asc()),
    "name_asc": (NailArt.name.asc(),),
    "name_desc": (NailArt.name.desc(),),
}
DEFAULT_SORT = "newest"

SORT_LABELS = [
    ("newest", "Newest"),
    ("oldest", "Oldest"),
    ("price_asc", "Price: Low to High"),
    ("price_desc", "Price: High to Low"),
    ("name_asc", "Name: A to Z"),
    ("name_desc", "Name: Z to A"),
]


@dataclass
class NailArtPage:
    items: list[NailArt]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        if self.page_size <= 0:
            return 1
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages


def _resolve_category(db: Session, category: str | int | None) -> Category | None:
    if category is None or category == "" or str(category).lower() == "all":
        return None
    if isinstance(category, int) or str(category).isdigit():
        return db.get(Category, int(category))
    return db.scalar(select(Category).where(Category.slug == str(category).lower()))


def list_nail_arts(
    db: Session,
    *,
    search: str | None = None,
    category: str | int | None = None,
    sort: str = DEFAULT_SORT,
    page: int = 1,
    page_size: int = 12,
    admin: bool = False,
    status: Status | None = None,
) -> NailArtPage:
    """
    Return a paginated list of nail-art designs.

    * Public (``admin=False``): only ACTIVE designs whose category is also
      ACTIVE are returned.
    * Admin (``admin=True``): all designs; optionally filtered by ``status``.
    """
    page = max(1, int(page or 1))
    page_size = min(60, max(1, int(page_size or 12)))
    sort = sort if sort in SORT_OPTIONS else DEFAULT_SORT

    conditions = []
    if admin:
        if status is not None:
            conditions.append(NailArt.status == status)
    else:
        conditions.append(NailArt.status == Status.ACTIVE)
        conditions.append(Category.status == Status.ACTIVE)

    cat = _resolve_category(db, category)
    if cat is not None:
        conditions.append(NailArt.category_id == cat.id)
    elif category not in (None, "", "all", "All"):
        # A category was requested but does not exist -> no results.
        return NailArtPage(items=[], total=0, page=page, page_size=page_size)

    if search and search.strip():
        for word in search.strip().split():
            like = f"%{word.lower()}%"
            conditions.append(
                or_(
                    func.lower(NailArt.name).like(like),
                    func.lower(NailArt.description).like(like),
                )
            )

    base = select(NailArt).join(NailArt.category).where(*conditions)

    total = db.scalar(
        select(func.count()).select_from(NailArt).join(NailArt.category).where(*conditions)
    ) or 0

    stmt = (
        base.options(contains_eager(NailArt.category))
        .order_by(*SORT_OPTIONS[sort])
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(db.scalars(stmt).unique().all())
    return NailArtPage(items=items, total=total, page=page, page_size=page_size)


def get_nail_by_slug_or_id(db: Session, identifier: str, *, admin: bool = False) -> NailArt | None:
    stmt = select(NailArt).join(NailArt.category).options(contains_eager(NailArt.category))
    if str(identifier).isdigit():
        stmt = stmt.where(NailArt.id == int(identifier))
    else:
        stmt = stmt.where(NailArt.slug == str(identifier).lower())
    if not admin:
        stmt = stmt.where(NailArt.status == Status.ACTIVE, Category.status == Status.ACTIVE)
    return db.scalar(stmt)


def related_designs(db: Session, nail: NailArt, limit: int = 4) -> list[NailArt]:
    """Active designs from the same category, excluding the current design."""
    stmt = (
        select(NailArt)
        .join(NailArt.category)
        .options(contains_eager(NailArt.category))
        .where(
            NailArt.category_id == nail.category_id,
            NailArt.id != nail.id,
            NailArt.status == Status.ACTIVE,
            Category.status == Status.ACTIVE,
        )
        .order_by(NailArt.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).unique().all())


def active_categories_with_counts(db: Session) -> list[Category]:
    """All ACTIVE categories, ordered by name, for public filters."""
    return list(
        db.scalars(
            select(Category).where(Category.status == Status.ACTIVE).order_by(Category.name)
        ).all()
    )
