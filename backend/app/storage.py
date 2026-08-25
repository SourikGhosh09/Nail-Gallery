"""
Image upload handling: validation, security checks and optimisation.

* Rejects files that are too large, have a disallowed extension, or are not
  genuinely decodable images (defends against disguised/malicious uploads).
* Strips metadata, fixes EXIF orientation, downsizes very large photos and
  re-encodes them for fast loading.
* Stores files with random names inside the configured upload directory, so
  there is no path-traversal or filename-collision risk.
"""
from __future__ import annotations

import io
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

# Pillow format name -> canonical extension we will store the file with.
_FORMAT_TO_EXT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
_MAX_DIMENSION = 1400  # longest edge, in pixels
_JPEG_QUALITY = 82


class ImageValidationError(Exception):
    """Raised when an uploaded file is not an acceptable image."""


def save_upload(upload) -> str:
    """
    Validate, optimise and store an uploaded image.

    ``upload`` is a Starlette/FastAPI ``UploadFile``.  Returns the stored
    file's path **relative** to the upload directory (e.g. ``"a1b2c3.jpg"``).
    Raises :class:`ImageValidationError` on any problem.
    """
    filename = (upload.filename or "").strip()
    if not filename:
        raise ImageValidationError("No file was provided.")

    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_extensions:
        allowed = ", ".join(sorted(settings.allowed_extensions))
        raise ImageValidationError(f"Unsupported file type. Allowed: {allowed}.")

    # Read at most max+1 bytes so an oversized upload can't exhaust memory.
    data = upload.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise ImageValidationError(
            f"Image is too large. Maximum size is {settings.MAX_UPLOAD_MB} MB."
        )
    if not data:
        raise ImageValidationError("The uploaded file is empty.")

    # Confirm it is really an image by decoding it with Pillow.
    try:
        probe = Image.open(io.BytesIO(data))
        probe.verify()  # checks integrity; must reopen afterwards
        image = Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, OSError):
        raise ImageValidationError("The file is not a valid image.")

    fmt = (image.format or "").upper()
    if fmt not in _FORMAT_TO_EXT:
        raise ImageValidationError("Unsupported image format.")

    # Normalise orientation and colour mode.
    image = ImageOps.exif_transpose(image)
    out_ext = _FORMAT_TO_EXT[fmt]
    save_kwargs: dict = {}

    if fmt == "JPEG":
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        save_kwargs = {"quality": _JPEG_QUALITY, "optimize": True, "progressive": True}
    elif fmt == "PNG":
        save_kwargs = {"optimize": True}
    elif fmt == "WEBP":
        save_kwargs = {"quality": _JPEG_QUALITY, "method": 6}

    # Downscale very large photos (keeps aspect ratio).
    image.thumbnail((_MAX_DIMENSION, _MAX_DIMENSION), Image.LANCZOS)

    stored_name = f"{uuid.uuid4().hex}{out_ext}"
    dest = settings.upload_path / stored_name
    image.save(dest, format=fmt, **save_kwargs)
    return stored_name


def delete_image(image_path: str | None) -> None:
    """Safely delete a stored image (no-op if missing or outside upload dir)."""
    if not image_path:
        return
    upload_root = settings.upload_path.resolve()
    target = (upload_root / Path(image_path).name).resolve()
    # Guard against path traversal — only delete inside the upload directory.
    if upload_root in target.parents and target.is_file():
        try:
            target.unlink()
        except OSError:
            pass
