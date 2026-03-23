from io import BytesIO

import pytest
from fastapi import UploadFile

from app.services import image_validation
from app.services.image_validation import (
    ImageValidationError,
    ValidatedImage,
    validate_image_upload,
)

PNG_1X1_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\xe2$\x8f"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _upload_file(name: str, content_type: str, content: bytes) -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(content), headers={"content-type": content_type})


def test_rejects_unsupported_mime_type() -> None:
    file = _upload_file("notes.txt", "text/plain", b"not-an-image")
    with pytest.raises(ImageValidationError) as exc:
        validate_image_upload(file)
    assert exc.value.code == "invalid_mime_type"


def test_rejects_oversized_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(image_validation, "MAX_FILE_SIZE_BYTES", 4)
    file = _upload_file("photo.png", "image/png", PNG_1X1_BYTES)
    with pytest.raises(ImageValidationError) as exc:
        validate_image_upload(file)
    assert exc.value.code == "file_too_large"


def test_rejects_unreadable_image_bytes() -> None:
    file = _upload_file("photo.png", "image/png", b"this-is-not-a-valid-image")
    with pytest.raises(ImageValidationError) as exc:
        validate_image_upload(file)
    assert exc.value.code == "image_decode_failed"


def test_rejects_excessive_pixel_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(image_validation, "MAX_IMAGE_PIXELS", 0)
    file = _upload_file("photo.png", "image/png", PNG_1X1_BYTES)
    with pytest.raises(ImageValidationError) as exc:
        validate_image_upload(file)
    assert exc.value.code == "image_too_large_pixels"


def test_accepts_valid_image_sample() -> None:
    file = _upload_file("photo.png", "image/png", PNG_1X1_BYTES)
    result = validate_image_upload(file)
    assert isinstance(result, ValidatedImage)
    assert result.content_type == "image/png"
    assert result.width == 1
    assert result.height == 1
