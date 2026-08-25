"""Admin server-rendered pages (protected).  Data mutations happen via the
admin REST API called from ``static/js/admin.js``; these routes render the
views and load the current data."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, NailArt, Status, User
from app.security import get_current_user
from app.services import list_nail_arts
from app.templating import templates

router = APIRouter(prefix="/admin", tags=["admin-pages"], include_in_schema=False)


def _redirect_login() -> RedirectResponse:
    return RedirectResponse(url="/admin", status_code=303)


@router.get("", response_class=HTMLResponse)
def admin_root(request: Request, user: User | None = Depends(get_current_user)):
    if user is not None:
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    return templates.TemplateResponse(request, "admin/login.html", {"admin_page": "login"})


@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    if user is None:
        return _redirect_login()
    total = db.scalar(select(func.count()).select_from(NailArt)) or 0
    active = db.scalar(select(func.count()).select_from(NailArt).where(NailArt.status == Status.ACTIVE)) or 0
    total_categories = db.scalar(select(func.count()).select_from(Category)) or 0
    recent = list(db.scalars(select(NailArt).join(NailArt.category).order_by(NailArt.created_at.desc()).limit(6)).unique().all())
    stats = {
        "total": total,
        "active": active,
        "inactive": total - active,
        "categories": total_categories,
    }
    return templates.TemplateResponse(
        request, "admin/dashboard.html",
        {"admin_page": "dashboard", "user": user, "stats": stats, "recent": recent},
    )


@router.get("/nail-arts", response_class=HTMLResponse)
def admin_nail_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sort: str = Query(default="newest"),
    page: int = Query(default=1, ge=1),
):
    if user is None:
        return _redirect_login()
    status_enum = None
    if status in ("active", "inactive"):
        status_enum = Status(status)
    result = list_nail_arts(db, search=search, category=category, sort=sort, page=page, page_size=12, admin=True, status=status_enum)
    categories = list(db.scalars(select(Category).order_by(Category.name)).all())
    return templates.TemplateResponse(
        request, "admin/nail_list.html",
        {
            "admin_page": "nail-arts", "user": user, "result": result, "categories": categories,
            "current_search": search or "", "current_category": category or "",
            "current_status": status or "", "current_sort": sort,
        },
    )


@router.get("/nail-arts/new", response_class=HTMLResponse)
def admin_nail_new(request: Request, db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    if user is None:
        return _redirect_login()
    categories = list(db.scalars(select(Category).where(Category.status == Status.ACTIVE).order_by(Category.name)).all())
    return templates.TemplateResponse(
        request, "admin/nail_form.html",
        {"admin_page": "nail-arts", "user": user, "nail": None, "categories": categories},
    )


@router.get("/nail-arts/{nail_id}/edit", response_class=HTMLResponse)
def admin_nail_edit(nail_id: int, request: Request, db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    if user is None:
        return _redirect_login()
    nail = db.get(NailArt, nail_id)
    if nail is None:
        return RedirectResponse(url="/admin/nail-arts", status_code=303)
    categories = list(db.scalars(select(Category).order_by(Category.name)).all())
    return templates.TemplateResponse(
        request, "admin/nail_form.html",
        {"admin_page": "nail-arts", "user": user, "nail": nail, "categories": categories},
    )


@router.get("/categories", response_class=HTMLResponse)
def admin_category_list(request: Request, db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    if user is None:
        return _redirect_login()
    categories = list(db.scalars(select(Category).order_by(Category.name)).all())
    return templates.TemplateResponse(
        request, "admin/category_list.html",
        {"admin_page": "categories", "user": user, "categories": categories},
    )


@router.get("/categories/new", response_class=HTMLResponse)
def admin_category_new(request: Request, user: User | None = Depends(get_current_user)):
    if user is None:
        return _redirect_login()
    return templates.TemplateResponse(
        request, "admin/category_form.html",
        {"admin_page": "categories", "user": user, "category": None},
    )


@router.get("/categories/{category_id}/edit", response_class=HTMLResponse)
def admin_category_edit(category_id: int, request: Request, db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    if user is None:
        return _redirect_login()
    category = db.get(Category, category_id)
    if category is None:
        return RedirectResponse(url="/admin/categories", status_code=303)
    return templates.TemplateResponse(
        request, "admin/category_form.html",
        {"admin_page": "categories", "user": user, "category": category},
    )
