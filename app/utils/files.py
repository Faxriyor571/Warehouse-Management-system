"""File upload helpers (used for product images)."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings
from app.utils.exceptions import ValidationError

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def save_image(file: UploadFile, subdir: str = "products") -> str:
    """Validate and store an uploaded image, returning its relative path.

    The returned path is relative to the upload directory, e.g.
    ``products/3f1c...e2.png`` and is suitable for storing on the model.
    """
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            "Rasm formati noto'g'ri. Ruxsat etilgan: "
            + ", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))
        )

    contents = file.file.read()
    if len(contents) > settings.max_upload_size_bytes:
        raise ValidationError(
            f"Fayl hajmi katta (maksimal {settings.max_upload_size_mb} MB)"
        )

    target_dir = settings.upload_path / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    target_path = target_dir / unique_name
    target_path.write_bytes(contents)

    return f"{subdir}/{unique_name}"
