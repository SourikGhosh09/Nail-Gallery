import hashlib
import io
import json
import zipfile
from types import SimpleNamespace

import pytest
from PIL import Image
from sqlalchemy import select

from app.config import Settings, settings
from app.database import SessionLocal, normalize_database_url
from app.models import Category, NailArt
from app import storage
from helpers import make_png
from migrate_catalog import restore


def test_vercel_rejects_ephemeral_storage():
    with pytest.raises(ValueError, match="persistent Blob"):
        Settings(VERCEL="1", DATABASE_URL="sqlite://", STORAGE_BACKEND="local", _env_file=None)
    assert normalize_database_url("postgres://user:pass@db/catalog") == "postgresql+psycopg://user:pass@db/catalog"


def test_private_blob_upload_read_and_crop(monkeypatch):
    files = {}
    token = "test-only-token"
    class FakeBlob:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def put(self, name, data, **options):
            assert options["access"] == "private"
            files[name] = data
        def get(self, name, **options):
            assert options["access"] == "private"
            return SimpleNamespace(content=files[name])
        def delete(self, name):
            files.pop(name, None)
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "vercel_blob")
    monkeypatch.setattr(settings, "BLOB_READ_WRITE_TOKEN", token)
    monkeypatch.setattr(storage, "_blob_client", lambda: FakeBlob())
    storage.store_image("original.png", make_png())
    cropped = storage.crop_image("original.png", {"x": 0, "y": 0, "width": .5, "height": .5})
    with Image.open(io.BytesIO(files["original.png"])) as original, Image.open(io.BytesIO(files[cropped])) as result:
        assert result.width == original.width // 2
    storage.delete_image(cropped)
    assert cropped not in files and "original.png" in files


def test_restore_preserves_hidden_products_and_refuses_overwrite(_clean_db, tmp_path):
    photo = make_png()
    manifest = {"version": 1, "photos": {"backup.png": hashlib.sha256(photo).hexdigest()},
        "categories": [{"id": 12, "name": "Hidden category", "slug": "hidden-category", "description": "Keep", "status": "inactive"}],
        "nail_arts": [{"id": 31, "name": "Hidden product", "slug": "hidden-product", "description": "Keep all records", "price": 100,
                       "category_id": 12, "status": "inactive", "image_alt": "Photo", "images": [{"image_path": "backup.png"}]}]}
    archive = tmp_path / "backup.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("catalog.json", json.dumps(manifest))
        output.writestr("photos/backup.png", photo)
    assert restore(archive) == {"categories": 1, "products": 1, "photos": 1}
    with SessionLocal() as db:
        nail = db.get(NailArt, 31)
        assert nail.image_paths == ["backup.png"]
        assert nail.status.value == "inactive"
        assert db.get(Category, 12).status.value == "inactive"
    with pytest.raises(ValueError, match="must be empty"):
        restore(archive)
