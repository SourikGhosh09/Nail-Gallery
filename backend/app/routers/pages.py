"""Public, server-rendered pages + SEO endpoints (sitemap, robots)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Category, NailArt, Status
from app.services import (
    DEFAULT_SORT,
    active_categories_with_counts,
    get_nail_by_slug_or_id,
    list_nail_arts,
    related_designs,
)
from app.templating import templates

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    featured = list_nail_arts(db, sort="newest", page=1, page_size=8)
    categories = active_categories_with_counts(db)
    return templates.TemplateResponse(
        request,
        "public/home.html",
        {"active_page": "home", "featured": featured.items, "categories": categories},
    )


@router.get("/catalog", response_class=HTMLResponse)
def catalog(
    request: Request,
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=140),
    sort: str = Query(default=DEFAULT_SORT),
    page: int = Query(default=1, ge=1),
):
    result = list_nail_arts(db, search=search, category=category, sort=sort, page=page, page_size=12)
    categories = active_categories_with_counts(db)
    return templates.TemplateResponse(
        request,
        "public/catalog.html",
        {
            "active_page": "catalog",
            "result": result,
            "categories": categories,
            "current_search": search or "",
            "current_category": category or "",
            "current_sort": sort if sort in dict(templates.env.globals["sort_labels"]) else DEFAULT_SORT,
        },
    )


@router.get("/nail/{slug}", response_class=HTMLResponse)
def nail_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    nail = get_nail_by_slug_or_id(db, slug)
    if nail is None:
        return templates.TemplateResponse(
            request, "public/404.html", {"active_page": "", "message": "This nail art design could not be found."}, status_code=404
        )
    related = related_designs(db, nail)
    return templates.TemplateResponse(
        request, "public/detail.html", {"active_page": "catalog", "nail": nail, "related": related}
    )


@router.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return templates.TemplateResponse(request, "public/about.html", {"active_page": "about"})


@router.get("/contact", response_class=HTMLResponse)
def contact(request: Request):
    return templates.TemplateResponse(request, "public/contact.html", {"active_page": "contact"})


# ---- SEO ------------------------------------------------------------------
@router.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
def robots():
    body = f"User-agent: *\nAllow: /\nDisallow: /admin\nSitemap: {settings.BASE_URL}/sitemap.xml\n"
    return PlainTextResponse(body)


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap(db: Session = Depends(get_db)):
    base = settings.BASE_URL.rstrip("/")
    urls = [f"{base}/", f"{base}/catalog", f"{base}/about", f"{base}/contact"]
    nails = db.scalars(
        select(NailArt).join(NailArt.category).where(
            NailArt.status == Status.ACTIVE, Category.status == Status.ACTIVE
        )
    ).unique().all()
    for n in nails:
        urls.append(f"{base}/nail/{n.slug}")

    items = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{items}\n</urlset>\n'
    return Response(content=xml, media_type="application/xml")


@router.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}
