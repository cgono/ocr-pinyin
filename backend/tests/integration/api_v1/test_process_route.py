import asyncio
from unittest.mock import patch

from helpers import PNG_1X1_BYTES, StubOcrProvider, _request_with_body

from app.adapters.ocr_provider import RawOcrSegment
from app.adapters.pinyin_provider import PinyinProviderUnavailableError, RawPinyinSegment
from app.api.v1.process import process_image
from app.services.image_validation import MAX_FILE_SIZE_BYTES


class StubPinyinProvider:
    def __init__(self, segments: list[RawPinyinSegment]) -> None:
        self._segments = segments

    def generate(self, *, text: str) -> list[RawPinyinSegment]:
        _ = text
        return self._segments


class FailingPinyinProvider:
    def generate(self, *, text: str) -> list[RawPinyinSegment]:
        raise PinyinProviderUnavailableError("pinyin unavailable")


def test_process_route_returns_envelope() -> None:
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider([RawOcrSegment(text="你好", language="zh", confidence=0.9)]),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status in {"success", "partial", "error"}
    assert isinstance(response.request_id, str)
    assert response.request_id
    assert response.data is not None or response.error is not None


def test_process_route_invalid_upload_returns_validation_error() -> None:
    request = _request_with_body(b"not-an-image", "image/png")
    response = asyncio.run(process_image(request))

    assert response.status == "error"
    assert response.error is not None
    assert response.error.category == "validation"
    assert response.error.code == "image_decode_failed"
    assert isinstance(response.error.message, str)


def test_process_route_valid_upload_returns_success_with_ocr_and_pinyin() -> None:
    pinyin_segments = [
        RawPinyinSegment(hanzi="你", pinyin="nǐ"),
        RawPinyinSegment(hanzi="好", pinyin="hǎo"),
    ]
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [RawOcrSegment(text="你好", language="zh", confidence=0.98)]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider(pinyin_segments),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "success"
    assert response.request_id
    assert response.data is not None
    # OCR preserved
    assert response.data.ocr is not None
    assert response.data.ocr.segments[0].text == "你好"
    assert response.data.ocr.segments[0].language == "zh"
    assert response.data.ocr.segments[0].confidence == 0.98
    # Pinyin present
    assert response.data.pinyin is not None
    assert len(response.data.pinyin.segments) == 2
    assert response.data.pinyin.segments[0].hanzi == "你"
    assert response.data.pinyin.segments[0].pinyin == "nǐ"
    assert response.data.pinyin.segments[1].hanzi == "好"
    assert response.data.pinyin.segments[1].pinyin == "hǎo"


def test_process_route_ocr_no_text_returns_typed_ocr_error() -> None:
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider([RawOcrSegment(text="hello", language="en", confidence=0.7)]),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "error"
    assert response.error is not None
    assert response.error.category == "ocr"
    assert response.error.code == "ocr_no_text_detected"


def test_process_route_pinyin_failure_returns_typed_pinyin_error() -> None:
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [RawOcrSegment(text="你好", language="zh", confidence=0.95)]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=FailingPinyinProvider(),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "error"
    assert response.error is not None
    assert response.error.category == "pinyin"
    assert response.error.code == "pinyin_provider_unavailable"


def test_process_route_missing_file_returns_validation_error() -> None:
    request = _request_with_body(b"", "")
    response = asyncio.run(process_image(request))

    assert response.status == "error"
    assert response.error is not None
    assert response.error.category == "validation"
    assert response.error.code == "missing_file"


def test_process_route_enforces_size_limit_without_content_length_header() -> None:
    request = _request_with_body(b"a" * (MAX_FILE_SIZE_BYTES + 1), "image/png")
    response = asyncio.run(process_image(request))

    assert response.status == "error"
    assert response.error is not None
    assert response.error.category == "validation"
    assert response.error.code == "file_too_large"
