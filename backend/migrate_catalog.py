"""Back up Render's complete admin catalog, then restore into an empty database.

Passwords are requested interactively and are never stored in the archive.
Run backup before restarting the old server (free Render disks are ephemeral).
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import zipfile
from datetime import datetime
from pathlib import Path

import httpx


def backup(base_url: str, archive: Path, public_counts: tuple[int, int] | None = None) -> dict:
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=90) as client:
        prefix = "/api" if public_counts else "/api/admin"
        if not public_counts:
            email = os.getenv("MIGRATION_ADMIN_EMAIL") or input("Current admin email: ")
            password = os.getenv("MIGRATION_ADMIN_PASSWORD") or getpass.getpass("Current admin password: ")
            response = client.post("/api/auth/login", json={"email": email, "password": password})
            response.raise_for_status()
        response = client.get(f"{prefix}/categories")
        response.raise_for_status()
        categories = response.json()["items"]
        nails = []
        page = 1
        while True:
            response = client.get(f"{prefix}/nail-arts", params={"page": page, "page_size": 60, "sort": "oldest"})
            response.raise_for_status()
            result = response.json()
            nails.extend(result["items"])
            if not result["has_next"]:
                break
            page += 1
        if public_counts and (len(nails), len(categories)) != public_counts:
            raise ValueError("Public counts differ from verified admin totals; use authenticated backup.")
        photos = {photo["image_path"] for nail in nails for photo in nail.get("images", [])}
        photos.update(nail["image_path"] for nail in nails if nail.get("image_path"))
        manifest = {"version": 1, "categories": categories, "nail_arts": nails, "photos": {}}
        archive.parent.mkdir(parents=True, exist_ok=True)
        temporary = archive.with_suffix(".partial")
        if archive.exists() or temporary.exists():
            raise ValueError("Backup file already exists; choose another filename.")
        try:
            with zipfile.ZipFile(temporary, "x", zipfile.ZIP_DEFLATED) as output:
                for name in sorted(photos):
                    if Path(name).name != name:
                        raise ValueError("Invalid photo filename in source catalog.")
                    response = client.get(f"/media/{name}")
                    response.raise_for_status()
                    manifest["photos"][name] = hashlib.sha256(response.content).hexdigest()
                    output.writestr(f"photos/{name}", response.content)
                output.writestr("catalog.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            temporary.rename(archive)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    return {"categories": len(categories), "products": len(nails), "photos": len(photos)}


def restore(archive: Path) -> dict:
    from sqlalchemy import func, select
    from app.database import SessionLocal, init_db
    from app.models import Category, NailArt, NailArtPhoto, Status
    from app.storage import delete_image, store_image
    from app.main import ensure_admin

    # Validate the whole backup before touching destination storage or DB.
    with zipfile.ZipFile(archive) as source:
        manifest = json.loads(source.read("catalog.json"))
        if manifest.get("version") != 1:
            raise ValueError("Unsupported backup version.")
        photos = {}
        for name, digest in manifest["photos"].items():
            if Path(name).name != name:
                raise ValueError("Unsafe photo filename.")
            content = source.read(f"photos/{name}")
            if hashlib.sha256(content).hexdigest() != digest:
                raise ValueError("Photo checksum mismatch.")
            photos[name] = content
    init_db()
    uploaded = []
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Category)) or db.scalar(select(func.count()).select_from(NailArt)):
            raise ValueError("Destination catalog must be empty; existing products will not be overwritten.")
        try:
            for name, content in photos.items():
                store_image(name, content)
                uploaded.append(name)
            for record in manifest["categories"]:
                category = Category(**{key: record[key] for key in ("id", "name", "slug", "description")}, status=Status(record["status"]))
                for key in ("created_at", "updated_at"):
                    if record.get(key):
                        setattr(category, key, datetime.fromisoformat(record[key]))
                db.add(category)
            db.flush()
            for record in manifest["nail_arts"]:
                paths = [photo["image_path"] for photo in record.get("images", [])]
                if not paths and record.get("image_path"):
                    paths = [record["image_path"]]
                if any(path not in photos for path in paths):
                    raise ValueError("A product photo is missing from the backup.")
                nail = NailArt(**{key: record[key] for key in ("id", "name", "slug", "description", "price", "category_id", "image_alt")},
                               status=Status(record["status"]), image_path=paths[0] if paths else None)
                for key in ("created_at", "updated_at"):
                    if record.get(key):
                        setattr(nail, key, datetime.fromisoformat(record[key]))
                nail.photos = [NailArtPhoto(image_path=path) for path in paths[1:]]
                db.add(nail)
            db.flush()
            if db.bind.dialect.name == "postgresql":
                from sqlalchemy import text
                for table in ("categories", "nail_arts"):
                    db.execute(text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE((SELECT MAX(id) FROM {table}), 1), EXISTS(SELECT 1 FROM {table}))"))
            db.commit()
        except Exception:
            db.rollback()
            for name in uploaded:
                delete_image(name)
            raise
    ensure_admin()
    return {"categories": len(manifest["categories"]), "products": len(manifest["nail_arts"]), "photos": len(photos)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "restore"])
    parser.add_argument("archive", type=Path)
    parser.add_argument("--source", default="https://nail-gallery-p87j.onrender.com")
    parser.add_argument("--public-counts", nargs=2, type=int, metavar=("PRODUCTS", "CATEGORIES"),
                        help="Only when admin totals have been verified to include no hidden records.")
    args = parser.parse_args()
    print(backup(args.source, args.archive, tuple(args.public_counts) if args.public_counts else None) if args.action == "backup" else restore(args.archive))
