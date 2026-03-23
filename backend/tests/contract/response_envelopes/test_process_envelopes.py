import asyncio
from collections.abc import Mapping
from unittest.mock import AsyncMock, patch

from helpers import PNG_1X1_BYTES, StubOcrProvider, _request_with_body

from app.adapters.ocr_provider import RawOcrSegment
from app.adapters.pinyin_provider import RawPinyinSegment
from app.api.v1.process import process_image
from app.schemas.process import (
    OcrData,
    OcrSegment,
    ProcessData,
    ProcessError,
    ProcessResponse,
    ProcessWarning,
)


class StubPinyinProvider:
    def __init__(self, segments: list[RawPinyinSegment]) -> None:
        self._segments = segments

    def generate(self, *, text: str) -> list[RawPinyinSegment]:
        _ = text
        return self._segments


def assert_process_envelope(envelope: Mapping[str, object]) -> None:
    assert "status" in envelope
    assert envelope["status"] in {"success", "partial", "error"}

    assert "request_id" in envelope
    assert isinstance(envelope["request_id"], str)
    assert envelope["request_id"]

    # Contract is strict snake_case with stable top-level keys.
    assert "requestId" not in envelope
    assert "payload" not in envelope

    status = envelope["status"]
    if status == "success":
        assert "data" in envelope
        assert isinstance(envelope["data"], Mapping)
        assert "ocr" in envelope["data"]
        ocr = envelope["data"]["ocr"]
        assert isinstance(ocr, Mapping)
        assert isinstance(ocr["segments"], list)
        # pinyin field is additive — may be present but is not required by contract
        if "pinyin" in envelope["data"]:
            pinyin = envelope["data"]["pinyin"]
            assert isinstance(pinyin, Mapping)
            assert isinstance(pinyin["segments"], list)
        assert "warnings" not in envelope
        assert "error" not in envelope
    elif status == "partial":
        assert "data" in envelope
        assert isinstance(envelope["data"], Mapping)
        assert "warnings" in envelope
        assert isinstance(envelope["warnings"], list)
        assert "error" not in envelope
    else:
        assert "error" in envelope
        assert isinstance(envelope["error"], Mapping)
        assert "category" in envelope["error"]
        assert "data" not in envelope


def test_process_endpoint_success_envelope_contract() -> None:
    pinyin_segments = [
        RawPinyinSegment(hanzi="你", pinyin="nǐ"),
        RawPinyinSegment(hanzi="好", pinyin="hǎo"),
    ]
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider([RawOcrSegment(text="你好", language="zh", confidence=0.91)]),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider(pinyin_segments),
    ):
        response = asyncio.run(process_image(_request_with_body(PNG_1X1_BYTES, "image/png")))
    payload = response.model_dump(exclude_none=True)
    assert_process_envelope(payload)
    # Verify pinyin is present in the success payload
    assert "pinyin" in payload["data"]
    assert payload["data"]["pinyin"]["segments"][0]["hanzi"] == "你"
    assert payload["data"]["pinyin"]["segments"][1]["hanzi"] == "好"


def test_process_endpoint_partial_envelope_contract() -> None:
    partial_response = ProcessResponse(
        status="partial",
        request_id="req-partial-contract",
        data=ProcessData(
            ocr=OcrData(segments=[OcrSegment(text="你好", language="zh", confidence=0.5)]),
            message="partially-processed",
        ),
        warnings=[ProcessWarning(code="ocr-low-confidence", message="Low confidence score")],
    )
    with patch(
        "app.api.v1.process._build_process_response",
        new=AsyncMock(return_value=partial_response),
    ):
        response = asyncio.run(process_image(_request_with_body(PNG_1X1_BYTES, "image/png")))
    assert_process_envelope(response.model_dump(exclude_none=True))


def test_process_endpoint_error_envelope_contract() -> None:
    error_response = ProcessResponse(
        status="error",
        request_id="req-error-contract",
        error=ProcessError(
            category="validation",
            code="invalid-image",
            message="Image could not be processed",
        ),
    )
    with patch(
        "app.api.v1.process._build_process_response",
        new=AsyncMock(return_value=error_response),
    ):
        response = asyncio.run(process_image(_request_with_body(PNG_1X1_BYTES, "image/png")))
    assert_process_envelope(response.model_dump(exclude_none=True))


def test_process_endpoint_validation_error_contract() -> None:
    response = asyncio.run(process_image(_request_with_body(b"nope", "image/png")))
    payload = response.model_dump(exclude_none=True)
    assert payload["status"] == "error"
    assert payload["error"]["category"] == "validation"
    assert payload["error"]["code"] == "image_decode_failed"
    assert "requestId" not in payload
    assert "payload" not in payload


def test_process_endpoint_pinyin_error_envelope_contract() -> None:
    """Pinyin failure must return a valid error envelope with category=pinyin."""
    from app.adapters.pinyin_provider import PinyinProviderUnavailableError

    class FailingPinyinProvider:
        def generate(self, *, text: str) -> list[RawPinyinSegment]:
            raise PinyinProviderUnavailableError("down")

    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider([RawOcrSegment(text="你好", language="zh", confidence=0.91)]),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=FailingPinyinProvider(),
    ):
        response = asyncio.run(process_image(_request_with_body(PNG_1X1_BYTES, "image/png")))
    payload = response.model_dump(exclude_none=True)
    assert_process_envelope(payload)
    assert payload["status"] == "error"
    assert payload["error"]["category"] == "pinyin"


def test_process_success_ocr_fields_unchanged_after_pinyin_addition() -> None:
    """Existing OCR contract fields (segments, language, confidence) must not drift."""
    pinyin_segments = [RawPinyinSegment(hanzi="你", pinyin="nǐ")]
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider([RawOcrSegment(text="你", language="zh", confidence=0.95)]),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider(pinyin_segments),
    ):
        response = asyncio.run(process_image(_request_with_body(PNG_1X1_BYTES, "image/png")))
    payload = response.model_dump(exclude_none=True)
    ocr_segment = payload["data"]["ocr"]["segments"][0]
    assert ocr_segment["text"] == "你"
    assert ocr_segment["language"] == "zh"
    assert ocr_segment["confidence"] == pytest.approx(0.95)


import pytest  # noqa: E402 – kept at bottom intentionally to avoid circular import issues

