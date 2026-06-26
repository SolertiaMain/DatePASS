from __future__ import annotations

import re
from io import BytesIO
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

PHOTO_MAX_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class ValidatedPhoto:
    data: bytes
    content_type: str
    extension: str
    filename: str


def sanitize_filename(filename: str | None) -> str:
    value = (filename or "memory-photo").rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip()
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return value[:120] or "memory-photo"


def detect_image(data: bytes) -> tuple[str, str] | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR":
        return "image/png", "png"
    return None


def validate_photo(data: bytes, filename: str | None = None) -> ValidatedPhoto:
    if not data:
        raise ValueError("Photo file is required")
    if len(data) > PHOTO_MAX_BYTES:
        raise ValueError("Photo exceeds the 10 MB limit")
    detected = detect_image(data)
    if not detected:
        raise ValueError("Unsupported image format")
    content_type, extension = detected
    return ValidatedPhoto(
        data=data,
        content_type=content_type,
        extension=extension,
        filename=sanitize_filename(filename),
    )


def _center_crop(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_width, target_height = size
    width, height = image.size
    scale = max(target_width / width, target_height / height)
    resized = image.resize((round(width * scale), round(height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - target_width) // 2
    top = (resized.height - target_height) // 2
    return resized.crop((left, top, left + target_width, top + target_height))


def _png_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def build_wallet_photo_assets(data: bytes) -> dict[str, bytes]:
    try:
        with Image.open(BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Unsupported image format") from exc

    return {
        "background.png": _png_bytes(_center_crop(image, (180, 220))),
        "background@2x.png": _png_bytes(_center_crop(image, (360, 440))),
        "background@3x.png": _png_bytes(_center_crop(image, (540, 660))),
        "strip.png": _png_bytes(_center_crop(image, (375, 123))),
        "strip@2x.png": _png_bytes(_center_crop(image, (750, 246))),
        "strip@3x.png": _png_bytes(_center_crop(image, (1125, 369))),
        "thumbnail.png": _png_bytes(_center_crop(image, (90, 90))),
        "thumbnail@2x.png": _png_bytes(_center_crop(image, (180, 180))),
        "thumbnail@3x.png": _png_bytes(_center_crop(image, (270, 270))),
    }
