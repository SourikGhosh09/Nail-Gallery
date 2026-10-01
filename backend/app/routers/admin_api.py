"""
Admin REST API (authenticated + CSRF-protected).

All routes are guarded at the router level by ``require_admin_api`` which
enforces a valid admin session cookie and, for state-changing methods, a valid
CSRF token.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, Category, NailArt, NailArtPhoto, Status, User
from app.schemas import (
    CategoryCreate,
    CategoryUpdate,
    NailArtCreate,
    NailArtUpdate,
    serialize_category,
    serialize_nail,
)
from app.security import require_admin_api
from app.services import list_nail_arts
from app.storage import ImageValidationError, delete_image, save_upload
from app.utils import slugify, unique_slug

router = APIRouter(
    prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin_api)]
)


def _save_images(uploads: list[UploadFile]) -> list[str]:
    paths = []
    try:
        for upload in uploads:
            if upload.filename:
                paths.append(save_upload(upload))
    except Exception as exc:
        for path in paths:
            delete_image(path)
        if isinstance(exc, ImageValidationError):
            raise HTTPException(status_code=422, detail={"message": str(exc), "errors": {"images": str(exc), "image": str(exc)}})
        raise
    return paths


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _validation_error(exc: ValidationError) -> HTTPException:
    """Convert a Pydantic error into a clean 422 the frontend can display."""
    errors: dict[str, str] = {}
    for err in exc.errors():
        field = ".".join(str(p) for p in err["loc"]) or "field"
        errors[field] = err["msg"]
    return HTTPException(status_code=422, detail={"message": "Validation failed.", "errors": errors})


def _log(db: Session, user: User, action: str, entity: str, entity_id: int | None, detail: str = "") -> None:
    db.add(
        AuditLog(
            user_id=user.id, action=action, entity_type=entity, entity_id=entity_id, detail=detail
        )
    )


def _nail_slug_exists(db: Session, exclude_id: int | None = None):
    def _exists(candidate: str) -> bool:
        stmt = select(NailArt.id).where(NailArt.slug == candidate)
        if exclude_id is not None:
            stmt = stmt.where(NailArt.id != exclude_id)
        return db.scalar(stmt) is not None

    return _exists


def _category_slug_exists(db: Session, exclude_id: int | None = None):
    def _exists(candidate: str) -> bool:
        stmt = select(Category.id).where(Category.slug == candidate)
        if exclude_id is not None:
            stmt = stmt.where(Category.id != exclude_id)
        return db.scalar(stmt) is not None

    return _exists


def _require_category(db: Session, category_id: int) -> Category:
    cat = db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=422, detail={"message": "Selected category does not exist.", "errors": {"category_id": "Category not found."}})
    return cat


# ===========================================================================
# Dashboard
# ===========================================================================
@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(NailArt)) or 0
    active = db.scalar(select(func.count()).select_from(NailArt).where(NailArt.status == Status.ACTIVE)) or 0
    total_categories = db.scalar(select(func.count()).select_from(Category)) or 0
    active_categories = db.scalar(select(func.count()).select_from(Category).where(Category.status == Status.ACTIVE)) or 0
    recent = list(
        db.scalars(select(NailArt).join(NailArt.category).order_by(NailArt.created_at.desc()).limit(5)).unique().all()
    )
    return {
        "total_nail_arts": total,
        "active_nail_arts": active,
        "inactive_nail_arts": total - active,
        "total_categories": total_categories,
        "active_categories": active_categories,
        "recent_nail_arts": [serialize_nail(n) for n in recent],
    }


# ===========================================================================
# Nail arts
# ===========================================================================
def _admin_status(value: str | None) -> Status | None:
    if not value or value.lower() == "all":
        return None
    return Status(value.lower())


@router.get("/nail-arts")
def admin_list_nail_arts(
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=140),
    status: str | None = Query(default=None),
    sort: str = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=60),
):
    try:
        status_enum = _admin_status(status)
    except ValueError:
        status_enum = None
    result = list_nail_arts(
        db, search=search, category=category, sort=sort, page=page,
        page_size=page_size, admin=True, status=status_enum,
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


@router.get("/nail-arts/{nail_id}")
def admin_get_nail_art(nail_id: int, db: Session = Depends(get_db)):
    nail = db.get(NailArt, nail_id)
    if nail is None:
        raise HTTPException(status_code=404, detail="Nail art not found.")
    return {"item": serialize_nail(nail)}


@router.post("/nail-arts", status_code=201)
def create_nail_art(
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_api),
    name: str = Form(...),
    description: str = Form(...),
    price: str = Form(...),
    category_id: str = Form(...),
    status: str = Form("active"),
    image_alt: str | None = Form(None),
    image: UploadFile | None = File(None),
    images: list[UploadFile] = File(default=[]),
):
    try:
        data = NailArtCreate(
            name=name, description=description, price=price,
            category_id=category_id, status=status, image_alt=image_alt,
        )
    except ValidationError as exc:
        raise _validation_error(exc)

    _require_category(db, data.category_id)

    paths = _save_images(([image] if image else []) + images)
    image_path = paths[0] if paths else None

    slug = unique_slug(data.name, _nail_slug_exists(db))
    nail = NailArt(
        name=data.name, slug=slug, description=data.description, price=data.price,
        category_id=data.category_id, status=data.status,
        image_path=image_path, image_alt=data.image_alt or data.name,
    )
    db.add(nail)
    nail.photos = [NailArtPhoto(image_path=path) for path in paths[1:]]
    try:
        db.flush()
        _log(db, user, "create", "nail_art", nail.id, nail.name)
        db.commit()
    except Exception:
        db.rollback()
        for path in paths:
            delete_image(path)
        raise
    db.refresh(nail)
    return {"item": serialize_nail(nail)}


@router.put("/nail-arts/{nail_id}")
def update_nail_art(
    nail_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_api),
    name: str = Form(...),
    description: str = Form(...),
    price: str = Form(...),
    category_id: str = Form(...),
    status: str = Form("active"),
    image_alt: str | None = Form(None),
    remove_image: str | None = Form(None),
    image: UploadFile | None = File(None),
    images: list[UploadFile] = File(default=[]),
    remove_images: list[str] = Form(default=[]),
):
    nail = db.get(NailArt, nail_id)
    if nail is None:
        raise HTTPException(status_code=404, detail="Nail art not found.")

    try:
        data = NailArtCreate(
            name=name, description=description, price=price,
            category_id=category_id, status=status, image_alt=image_alt,
        )
    except ValidationError as exc:
        raise _validation_error(exc)

    _require_category(db, data.category_id)

    if any(path not in nail.image_paths for path in remove_images):
        raise HTTPException(status_code=422, detail="A selected photo does not belong to this product.")
    paths = _save_images(([image] if image else []) + images)
    removed = set(remove_images)
    # Preserve the legacy single-image API's replacement semantics.
    if (image and image.filename) or remove_image == "true":
        if nail.image_path:
            removed.add(nail.image_path)
    old_paths = nail.image_paths
    retained = [path for path in old_paths if path not in removed] + paths
    nail.image_path = retained[0] if retained else None
    nail.photos = [NailArtPhoto(image_path=path) for path in retained[1:]]

    if data.name != nail.name:
        nail.slug = unique_slug(data.name, _nail_slug_exists(db, exclude_id=nail.id))
    nail.name = data.name
    nail.description = data.description
    nail.price = data.price
    nail.category_id = data.category_id
    nail.status = data.status
    nail.image_alt = data.image_alt or data.name

    _log(db, user, "update", "nail_art", nail.id, nail.name)
    try:
        db.commit()
    except Exception:
        db.rollback()
        for path in paths:
            delete_image(path)
        raise
    db.refresh(nail)
    for path in removed:
        delete_image(path)
    return {"item": serialize_nail(nail)}


@router.patch("/nail-arts/{nail_id}/status")
def set_nail_status(
    nail_id: int,
    status: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_api),
):
    nail = db.get(NailArt, nail_id)
    if nail is None:
        raise HTTPException(status_code=404, detail="Nail art not found.")
    try:
        nail.status = Status(status.lower())
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid status.")
    _log(db, user, "status", "nail_art", nail.id, nail.status.value)
    db.commit()
    db.refresh(nail)
    return {"item": serialize_nail(nail)}


@router.delete("/nail-arts/{nail_id}")
def delete_nail_art(
    nail_id: int,
    hard: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_api),
):
    nail = db.get(NailArt, nail_id)
    if nail is None:
        raise HTTPException(status_code=404, detail="Nail art not found.")
    if hard:
        paths = nail.image_paths
        _log(db, user, "delete", "nail_art", nail.id, nail.name)
        db.delete(nail)
        db.commit()
        for path in paths:
            delete_image(path)
        return {"detail": "Nail art permanently deleted."}
    # Soft delete (deactivate).
    nail.status = Status.INACTIVE
    _log(db, user, "deactivate", "nail_art", nail.id, nail.name)
    db.commit()
    return {"detail": "Nail art deactivated.", "item": serialize_nail(nail)}


# ===========================================================================
# Categories
# ===========================================================================
@router.get("/categories")
def admin_list_categories(db: Session = Depends(get_db)):
    cats = list(db.scalars(select(Category).order_by(Category.name)).all())
    return {"items": [serialize_category(c) for c in cats]}


@router.get("/categories/{category_id}")
def admin_get_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found.")
    return {"item": serialize_category(cat)}


@router.post("/categories", status_code=201)
def create_category(
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_api),
    name: str = Form(...),
    description: str | None = Form(None),
    status: str = Form("active"),
):
    try:
        data = CategoryCreate(name=name, description=description, status=status)
    except ValidationError as exc:
        raise _validation_error(exc)

    if db.scalar(select(Category.id).where(func.lower(Category.name) == data.name.lower())):
        raise HTTPException(status_code=409, detail={"message": "A category with this name already exists.", "errors": {"name": "Name already in use."}})

    cat = Category(
        name=data.name, slug=unique_slug(data.name, _category_slug_exists(db)),
        description=data.description, status=data.status,
    )
    db.add(cat)
    db.flush()
    _log(db, user, "create", "category", cat.id, cat.name)
    db.commit()
    db.refresh(cat)
    return {"item": serialize_category(cat)}


@router.put("/categories/{category_id}")
def update_category(
    category_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_api),
    name: str = Form(...),
    description: str | None = Form(None),
    status: str = Form("active"),
):
    cat = db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found.")
    try:
        data = CategoryUpdate(name=name, description=description, status=status)
    except ValidationError as exc:
        raise _validation_error(exc)

    if data.name and data.name.lower() != cat.name.lower():
        clash = db.scalar(select(Category.id).where(func.lower(Category.name) == data.name.lower(), Category.id != cat.id))
        if clash:
            raise HTTPException(status_code=409, detail={"message": "A category with this name already exists.", "errors": {"name": "Name already in use."}})
        cat.name = data.name
        cat.slug = unique_slug(data.name, _category_slug_exists(db, exclude_id=cat.id))
    if data.description is not None:
        cat.description = data.description
    if data.status is not None:
        cat.status = data.status

    _log(db, user, "update", "category", cat.id, cat.name)
    db.commit()
    db.refresh(cat)
    return {"item": serialize_category(cat)}


@router.patch("/categories/{category_id}/status")
def set_category_status(
    category_id: int,
    status: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_api),
):
    cat = db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found.")
    try:
        cat.status = Status(status.lower())
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid status.")
    _log(db, user, "status", "category", cat.id, cat.status.value)
    db.commit()
    db.refresh(cat)
    return {"item": serialize_category(cat)}


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    action: str | None = Query(default=None),
    target_category_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_api),
):
    """
    Safe category deletion — never orphans designs.

    * No designs  -> permanently deleted.
    * Has designs & no ``action`` -> 409 telling the client what to do.
    * ``action=deactivate`` -> category hidden (designs kept, hidden publicly).
    * ``action=reassign`` (+ ``target_category_id``) -> designs moved, then
      the empty category is deleted.
    """
    cat = db.get(Category, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found.")

    design_count = db.scalar(select(func.count()).select_from(NailArt).where(NailArt.category_id == cat.id)) or 0

    if design_count == 0:
        _log(db, user, "delete", "category", cat.id, cat.name)
        db.delete(cat)
        db.commit()
        return {"detail": "Category deleted."}

    if action == "deactivate":
        cat.status = Status.INACTIVE
        _log(db, user, "deactivate", "category", cat.id, cat.name)
        db.commit()
        return {"detail": "Category deactivated.", "item": serialize_category(cat)}

    if action == "reassign":
        if not target_category_id or target_category_id == cat.id:
            raise HTTPException(status_code=422, detail="A different target category is required to reassign designs.")
        target = db.get(Category, target_category_id)
        if target is None:
            raise HTTPException(status_code=422, detail="Target category not found.")
        db.query(NailArt).filter(NailArt.category_id == cat.id).update({NailArt.category_id: target.id})
        _log(db, user, "reassign+delete", "category", cat.id, f"{cat.name} -> {target.name}")
        db.delete(cat)
        db.commit()
        return {"detail": f"Designs moved to '{target.name}' and category deleted."}

    # Designs exist and no safe action was chosen.
    raise HTTPException(
        status_code=409,
        detail={
            "message": f"This category contains {design_count} design(s).",
            "requires_action": True,
            "design_count": design_count,
            "options": ["deactivate", "reassign"],
        },
    )
