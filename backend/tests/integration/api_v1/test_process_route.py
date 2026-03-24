import asyncio
from unittest.mock import patch

from helpers import PNG_1X1_BYTES, StubOcrProvider, _request_with_body

from app.adapters.ocr_provider import RawOcrSegment
from app.adapters.pinyin_provider import (
    PinyinExecutionError,
    PinyinProviderUnavailableError,
    RawPinyinSegment,
)
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
    # Pinyin present — one segment per OCR segment with aligned status
    assert response.data.pinyin is not None
    assert len(response.data.pinyin.segments) == 1
    assert response.data.pinyin.segments[0].source_text == "你好"
    assert response.data.pinyin.segments[0].pinyin_text == "nǐ hǎo"
    assert response.data.pinyin.segments[0].alignment_status == "aligned"


def test_process_route_ocr_no_text_returns_typed_ocr_error() -> None:
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider([]),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "error"
    assert response.error is not None
    assert response.error.category == "ocr"
    assert response.error.code == "ocr_no_text_detected"


def test_process_route_non_chinese_only_returns_ocr_no_chinese_text_error() -> None:
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [
                RawOcrSegment(text="Hello World", language="en", confidence=0.9),
                RawOcrSegment(text="Page 12", language="en", confidence=0.85),
            ]
        ),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "error"
    assert response.error is not None
    assert response.error.category == "ocr"
    assert response.error.code == "ocr_no_chinese_text"


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

    assert response.status == "partial"
    assert response.error is None
    assert response.data is not None
    assert response.data.ocr is not None
    assert len(response.data.ocr.segments) == 1
    assert response.warnings is not None
    assert len(response.warnings) == 1
    assert response.warnings[0].category == "pinyin"
    assert response.warnings[0].code == "pinyin_provider_unavailable"


def test_process_route_pinyin_failure_partial_preserves_ocr() -> None:
    """When OCR succeeds but pinyin fails, partial response includes OCR data and no pinyin."""
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

    assert response.status == "partial"
    # OCR data preserved
    assert response.data is not None
    assert response.data.ocr is not None
    assert response.data.ocr.segments[0].text == "你好"
    # No pinyin in partial result
    assert response.data.pinyin is None
    # Warning carries the failure details
    assert response.warnings[0].category == "pinyin"
    assert isinstance(response.warnings[0].message, str)
    assert response.warnings[0].message


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


def test_process_route_mixed_segments_returns_aligned_and_uncertain() -> None:
    """Multiple OCR segments where one fails alignment → status=success with mixed segments."""
    call_count = 0

    class MixedProvider:
        def generate(self, *, text: str) -> list[RawPinyinSegment]:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise PinyinExecutionError("malformed output")
            return [RawPinyinSegment(hanzi=c, pinyin="nǐ") for c in text]

    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [
                RawOcrSegment(text="你好", language="zh", confidence=0.95),
                RawOcrSegment(text="世界", language="zh", confidence=0.90),
            ]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=MixedProvider(),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "success"
    assert response.data is not None
    assert response.data.pinyin is not None
    assert len(response.data.pinyin.segments) == 2
    assert response.data.pinyin.segments[0].alignment_status == "aligned"
    assert response.data.pinyin.segments[1].alignment_status == "uncertain"
    assert response.data.pinyin.segments[1].reason_code == "pinyin_execution_failed"
    assert response.data.pinyin.segments[1].source_text == "世界"
