from io import BytesIO

import pytest
from fastapi import UploadFile

from app.services import image_validation
from app.services.image_validation import (
    MAX_FILE_SIZE_BYTES,
    MAX_IMAGE_PIXELS,
    ImageValidationError,
    ValidatedImage,
    get_configured_max_image_pixels,
    get_configured_max_upload_bytes,
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

# 2×2 RGB PNG (4 pixels) — used to test pixel-limit env var override
PNG_2X2_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x02\x00\x00\x00\x02"
    b"\x08\x02\x00\x00\x00\xfd\xd4\x9as\x00\x00\x00\x0bIDATx\x9cc`@\x06"
    b"\x00\x00\x0e\x00\x01\xa9\x91s\xb1\x00\x00\x00\x00IEND\xaeB`\x82"
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


def test_get_configured_max_upload_bytes_returns_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MAX_UPLOAD_BYTES", raising=False)

    assert get_configured_max_upload_bytes() == MAX_FILE_SIZE_BYTES


def test_get_configured_max_upload_bytes_reads_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "4194304")

    assert get_configured_max_upload_bytes() == 4_194_304


def test_get_configured_max_upload_bytes_invalid_env_var_uses_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "bad")

    assert get_configured_max_upload_bytes() == MAX_FILE_SIZE_BYTES


def test_get_configured_max_image_pixels_returns_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MAX_UPLOAD_PIXELS", raising=False)

    assert get_configured_max_image_pixels() == MAX_IMAGE_PIXELS


def test_get_configured_max_image_pixels_reads_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_UPLOAD_PIXELS", "1000000")

    assert get_configured_max_image_pixels() == 1_000_000


def test_get_configured_max_image_pixels_invalid_env_var_uses_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_UPLOAD_PIXELS", "bad")

    assert get_configured_max_image_pixels() == MAX_IMAGE_PIXELS


def test_get_configured_max_upload_bytes_zero_uses_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "0")

    assert get_configured_max_upload_bytes() == MAX_FILE_SIZE_BYTES


def test_get_configured_max_upload_bytes_negative_uses_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "-1")

    assert get_configured_max_upload_bytes() == MAX_FILE_SIZE_BYTES


def test_get_configured_max_image_pixels_zero_uses_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_UPLOAD_PIXELS", "0")

    assert get_configured_max_image_pixels() == MAX_IMAGE_PIXELS


def test_get_configured_max_image_pixels_negative_uses_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_UPLOAD_PIXELS", "-1")

    assert get_configured_max_image_pixels() == MAX_IMAGE_PIXELS


def test_validate_image_upload_respects_env_var_size_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "4")
    file = _upload_file("photo.png", "image/png", PNG_1X1_BYTES)

    with pytest.raises(ImageValidationError) as exc:
        validate_image_upload(file)

    assert exc.value.code == "file_too_large"


def test_validate_image_upload_respects_env_var_pixel_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_UPLOAD_PIXELS", "1")  # 2x2 image has 4 pixels, exceeds limit
    file = _upload_file("photo.png", "image/png", PNG_2X2_BYTES)

    with pytest.raises(ImageValidationError) as exc:
        validate_image_upload(file)

    assert exc.value.code == "image_too_large_pixels"
