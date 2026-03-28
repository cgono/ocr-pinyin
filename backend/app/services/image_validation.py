import io
import os

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

VALIDATION_ERROR_CATEGORY = "validation"
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000

# Disable Pillow's built-in decompression-bomb limit; we enforce MAX_IMAGE_PIXELS explicitly below.
Image.MAX_IMAGE_PIXELS = None


class ValidatedImage:
    __slots__ = ("content_type", "size_bytes", "width", "height")

    def __init__(self, *, content_type: str, size_bytes: int, width: int, height: int) -> None:
        self.content_type = content_type
        self.size_bytes = size_bytes
        self.width = width
        self.height = height


class ImageValidationError(Exception):
    """Raised when an uploaded image fails a validation check."""

    def __init__(self, *, code: str, message: str, category: str = VALIDATION_ERROR_CATEGORY) -> None:  # noqa: E501
        super().__init__(message)
        self.code = code
        self.message = message
        self.category = category


def get_configured_max_upload_bytes() -> int:
    """Return the effective file-size ceiling, preferring MAX_UPLOAD_BYTES env var."""
    try:
        value = int(os.environ.get("MAX_UPLOAD_BYTES", ""))
        if value > 0:
            return value
    except (ValueError, TypeError):
        pass
    return MAX_FILE_SIZE_BYTES


def get_configured_max_image_pixels() -> int:
    """Return the effective pixel-count ceiling, preferring MAX_UPLOAD_PIXELS env var."""
    try:
        value = int(os.environ.get("MAX_UPLOAD_PIXELS", ""))
        if value > 0:
            return value
    except (ValueError, TypeError):
        pass
    return MAX_IMAGE_PIXELS


def validate_image_upload(file: UploadFile | None) -> ValidatedImage:
    if file is None:
        raise ImageValidationError(
            code="missing_file",
            message="No image was uploaded. Please take a photo or upload an image file.",
        )

    content_type = (file.content_type or "").lower().strip()
    if content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise ImageValidationError(
            code="invalid_mime_type",
            message="Unsupported file type. Please upload a JPG, PNG, or WEBP image.",
        )

    file.file.seek(0, 2)
    size_bytes = file.file.tell()
    file.file.seek(0)
    if size_bytes > get_configured_max_upload_bytes():
        raise ImageValidationError(
            code="file_too_large",
            message="Image is too large. Please upload a smaller file and try again.",
        )

    image_bytes = file.file.read()
    file.file.seek(0)
    if not image_bytes:
        raise ImageValidationError(
            code="image_decode_failed",
            message="The uploaded file could not be read as an image. Please retake the photo.",
        )

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size  # Header-only: no pixel decode yet.
            if width * height <= get_configured_max_image_pixels():
                img.load()  # Full decode only within safe bounds; validates integrity.
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise ImageValidationError(
            code="image_decode_failed",
            message="The uploaded file could not be read as an image. Please retake the photo.",
        ) from None

    if width * height > get_configured_max_image_pixels():
        raise ImageValidationError(
            code="image_too_large_pixels",
            message="Image dimensions are too large. Please capture a lower-resolution image.",
        )

    return ValidatedImage(
        content_type=content_type,
        size_bytes=size_bytes,
        width=width,
        height=height,
    )

