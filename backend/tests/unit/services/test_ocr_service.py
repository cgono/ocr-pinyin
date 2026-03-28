import asyncio

import pytest

from app.adapters.ocr_provider import RawOcrSegment
from app.services.ocr_service import OcrServiceError, extract_chinese_segments

PNG_1X1_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\xe2$\x8f"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


class StubProvider:
    def __init__(self, segments: list[RawOcrSegment]) -> None:
        self._segments = segments

    def extract(self, *, image_bytes: bytes, content_type: str) -> list[RawOcrSegment]:
        _ = (image_bytes, content_type)
        return self._segments


def test_extract_chinese_segments_normalizes_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.ocr_service.get_ocr_provider",
        lambda: StubProvider(
            [
                RawOcrSegment(text=" 你好 ", language="ZH-HANS", confidence=92, line_id=7),
                RawOcrSegment(text="hello", language="en", confidence=0.6),
            ]
        ),
    )

    segments = asyncio.run(extract_chinese_segments(PNG_1X1_BYTES, "image/png"))

    assert len(segments) == 1
    assert segments[0].text == "你好"
    assert segments[0].language == "zh-hans"
    assert segments[0].confidence == pytest.approx(0.92)
    assert segments[0].line_id == 7


def test_extract_chinese_segments_preserves_none_line_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.ocr_service.get_ocr_provider",
        lambda: StubProvider(
            [RawOcrSegment(text="你好", language="zh", confidence=0.9)]
        ),
    )

    segments = asyncio.run(extract_chinese_segments(PNG_1X1_BYTES, "image/png"))

    assert segments[0].line_id is None


def test_extract_chinese_segments_raises_when_no_usable_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.ocr_service.get_ocr_provider",
        lambda: StubProvider([]),
    )

    with pytest.raises(OcrServiceError) as exc:
        asyncio.run(extract_chinese_segments(PNG_1X1_BYTES, "image/png"))

    assert exc.value.category == "ocr"
    assert exc.value.code == "ocr_no_text_detected"


def test_extract_chinese_segments_non_chinese_only_raises_specific_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.ocr_service.get_ocr_provider",
        lambda: StubProvider(
            [
                RawOcrSegment(text="Hello World", language="en", confidence=0.95),
                RawOcrSegment(text="Page 12", language="en", confidence=0.90),
            ]
        ),
    )

    with pytest.raises(OcrServiceError) as exc:
        asyncio.run(extract_chinese_segments(PNG_1X1_BYTES, "image/png"))

    assert exc.value.category == "ocr"
    assert exc.value.code == "ocr_no_chinese_text"


def test_extract_chinese_segments_mixed_returns_only_chinese(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.ocr_service.get_ocr_provider",
        lambda: StubProvider(
            [
                RawOcrSegment(text="你好世界", language="zh-hans", confidence=0.95),
                RawOcrSegment(text="Page 1", language="en", confidence=0.90),
            ]
        ),
    )

    segments = asyncio.run(extract_chinese_segments(PNG_1X1_BYTES, "image/png"))

    assert len(segments) == 1
    assert segments[0].text == "你好世界"


def test_extract_chinese_segments_empty_raw_raises_no_text_detected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.ocr_service.get_ocr_provider",
        lambda: StubProvider([]),
    )

    with pytest.raises(OcrServiceError) as exc:
        asyncio.run(extract_chinese_segments(PNG_1X1_BYTES, "image/png"))

    assert exc.value.category == "ocr"
    assert exc.value.code == "ocr_no_text_detected"


def test_extract_raises_provider_unavailable_on_provider_unavailable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.adapters.ocr_provider import ProviderUnavailableError

    class UnavailableProvider:
        def extract(self, *, image_bytes: bytes, content_type: str) -> list[RawOcrSegment]:
            raise ProviderUnavailableError("not configured")

    monkeypatch.setattr("app.services.ocr_service.get_ocr_provider", UnavailableProvider)

    with pytest.raises(OcrServiceError) as exc:
        asyncio.run(extract_chinese_segments(PNG_1X1_BYTES, "image/png"))

    assert exc.value.category == "ocr"
    assert exc.value.code == "ocr_provider_unavailable"


def test_extract_raises_execution_failed_on_ocr_execution_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.adapters.ocr_provider import OcrExecutionError as AdapterError

    class FailingProvider:
        def extract(self, *, image_bytes: bytes, content_type: str) -> list[RawOcrSegment]:
            raise AdapterError("api call failed")

    monkeypatch.setattr("app.services.ocr_service.get_ocr_provider", FailingProvider)

    with pytest.raises(OcrServiceError) as exc:
        asyncio.run(extract_chinese_segments(PNG_1X1_BYTES, "image/png"))

    assert exc.value.category == "ocr"
    assert exc.value.code == "ocr_execution_failed"


def test_normalize_confidence_handles_edge_cases() -> None:
    from app.services.ocr_service import _normalize_confidence

    assert _normalize_confidence(None) == 0.0
    assert _normalize_confidence(0) == 0.0
    assert _normalize_confidence(0.5) == pytest.approx(0.5)
    assert _normalize_confidence(100) == pytest.approx(1.0)
    assert _normalize_confidence(150) == pytest.approx(1.0)  # clamped
    assert _normalize_confidence(-5) == pytest.approx(0.0)    # clamped


def test_normalize_language_handles_none_and_empty() -> None:
    from app.services.ocr_service import _normalize_language

    assert _normalize_language(None) == "und"
    assert _normalize_language("") == "und"
    assert _normalize_language("  ") == "und"
    assert _normalize_language("ZH-HANS") == "zh-hans"


def test_invalid_low_confidence_threshold_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from app.services.ocr_service import _resolve_low_confidence_threshold

    monkeypatch.setenv("OCR_LOW_CONFIDENCE_THRESHOLD", "not-a-number")

    with caplog.at_level("WARNING"):
        threshold = _resolve_low_confidence_threshold()

    assert threshold == pytest.approx(0.7)
    assert "Invalid OCR_LOW_CONFIDENCE_THRESHOLD" in caplog.text
