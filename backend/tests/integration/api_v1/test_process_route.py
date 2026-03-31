import asyncio
import logging
from unittest.mock import patch

import pytest
from helpers import PNG_1X1_BYTES, StubOcrProvider, _request_with_body

from app.adapters.ocr_provider import ProviderUnavailableError, RawOcrSegment
from app.adapters.pinyin_provider import (
    PinyinExecutionError,
    PinyinProviderUnavailableError,
    RawPinyinSegment,
)
from app.adapters.translation_provider import TranslationExecutionError
from app.api.v1.process import process_image
from app.schemas.diagnostics import CostEstimate
from app.services import budget_service
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


class StubTranslationProvider:
    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = mapping

    def translate(self, *, text: str, target_language: str) -> str:
        _ = target_language
        return self._mapping[text]


class FailingTranslationProvider:
    def translate(self, *, text: str, target_language: str) -> str:
        _ = (text, target_language)
        raise TranslationExecutionError("translate failed")


def _reset_daily_costs() -> None:
    budget_service.daily_cost_store.__dict__.update(
        budget_service.DailyCostStore().__dict__
    )


@pytest.fixture(autouse=True)
def _clean_daily_cost_store() -> None:
    _reset_daily_costs()


def _set_today_spend_sgd(sgd: float) -> None:
    _reset_daily_costs()
    estimated_usd = round(sgd / budget_service._USD_TO_SGD, 8)
    budget_service.record_request_cost(
        CostEstimate(estimated_usd=estimated_usd, estimated_sgd=sgd, confidence="full")
    )


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


def test_process_route_valid_upload_returns_success_with_ocr_and_pinyin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OCR_PROVIDER", raising=False)
    monkeypatch.setenv("TRANSLATION_ENABLED", "false")
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
    assert response.diagnostics is not None
    assert response.diagnostics.upload_context.content_type == "image/png"
    assert response.diagnostics.upload_context.file_size_bytes == len(PNG_1X1_BYTES)
    assert response.diagnostics.timing.total_ms >= 0.0
    assert response.diagnostics.timing.ocr_ms >= 0.0
    assert response.diagnostics.timing.pinyin_ms >= 0.0
    assert len(response.diagnostics.trace.steps) >= 2
    assert response.diagnostics.cost_estimate is not None
    assert response.diagnostics.cost_estimate.confidence == "unavailable"
    assert response.diagnostics.cost_estimate.estimated_usd is None


def test_process_route_success_adds_line_level_translations_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRANSLATION_ENABLED", "true")

    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [
                RawOcrSegment(text="老", language="zh", confidence=0.98, line_id=0),
                RawOcrSegment(text="师", language="zh", confidence=0.97, line_id=0),
                RawOcrSegment(text="你好", language="zh", confidence=0.96, line_id=1),
            ]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider([RawPinyinSegment(hanzi="你", pinyin="nǐ")]),
    ), patch(
        "app.services.translation_service.get_translation_provider",
        return_value=StubTranslationProvider({"老师": "teacher", "你好": "hello"}),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "success"
    assert response.data is not None
    assert response.data.pinyin is not None
    assert [segment.translation_text for segment in response.data.pinyin.segments] == [
        "teacher",
        "teacher",
        "hello",
    ]


def test_process_route_translation_disabled_returns_success_with_null_translations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRANSLATION_ENABLED", "false")

    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [RawOcrSegment(text="你好", language="zh", confidence=0.98, line_id=0)]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider(
            [
                RawPinyinSegment(hanzi="你", pinyin="nǐ"),
                RawPinyinSegment(hanzi="好", pinyin="hǎo"),
            ]
        ),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "success"
    assert response.data is not None
    assert response.data.pinyin is not None
    assert response.data.pinyin.segments[0].translation_text is None


def test_process_route_translation_failure_still_returns_success_with_null_translations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRANSLATION_ENABLED", "true")

    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [RawOcrSegment(text="你好", language="zh", confidence=0.98, line_id=0)]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider(
            [
                RawPinyinSegment(hanzi="你", pinyin="nǐ"),
                RawPinyinSegment(hanzi="好", pinyin="hǎo"),
            ]
        ),
    ), patch(
        "app.services.translation_service.get_translation_provider",
        return_value=FailingTranslationProvider(),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "success"
    assert response.data is not None
    assert response.data.pinyin is not None
    assert response.data.pinyin.segments[0].translation_text is None


def test_process_route_success_adds_reading_projection_without_mutating_raw_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRANSLATION_ENABLED", "false")

    raw_segments = [
        RawOcrSegment(text="老师", language="zh", confidence=0.98, line_id=0),
        RawOcrSegment(text="好", language="zh", confidence=0.97, line_id=0),
        RawOcrSegment(text="我们开始上课", language="zh", confidence=0.96, line_id=1),
    ]

    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(raw_segments),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider([RawPinyinSegment(hanzi="好", pinyin="hǎo")]),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "success"
    assert response.data is not None
    assert response.data.ocr is not None
    assert response.data.pinyin is not None
    assert [segment.text for segment in response.data.ocr.segments] == [
        "老师",
        "好",
        "我们开始上课",
    ]
    assert [segment.source_text for segment in response.data.pinyin.segments] == [
        "老师",
        "好",
        "我们开始上课",
    ]
    assert response.data.reading is not None
    assert response.data.reading.provider.kind == "heuristic"
    assert response.data.reading.groups[0].segment_indexes == [0, 1]
    assert response.data.reading.groups[0].display_text == "老师好。"
    assert response.data.reading.groups[1].segment_indexes == [2]
    assert response.data.reading.groups[1].display_text == "我们开始上课。"


def test_process_route_reading_projection_exception_falls_back_to_success_without_reading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRANSLATION_ENABLED", "false")

    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [RawOcrSegment(text="你好", language="zh", confidence=0.98, line_id=0)]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider([RawPinyinSegment(hanzi="你", pinyin="nǐ")]),
    ), patch(
        "app.api.v1.process.build_reading_projection",
        side_effect=RuntimeError("projection exploded"),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "success"
    assert response.data is not None
    assert response.data.reading is None


def test_process_route_low_confidence_partial_omits_reading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OCR_PROVIDER", raising=False)
    monkeypatch.setenv("TRANSLATION_ENABLED", "false")

    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [RawOcrSegment(text="你好", language="zh", confidence=0.3, line_id=0)]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider([RawPinyinSegment(hanzi="你", pinyin="nǐ")]),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "partial"
    assert response.data is not None
    assert response.data.reading is None


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
    assert response.diagnostics is None


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


def test_process_route_pinyin_failure_returns_typed_pinyin_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OCR_PROVIDER", raising=False)
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
    assert response.diagnostics is not None
    assert response.diagnostics.timing.total_ms >= 0.0
    assert response.diagnostics.timing.ocr_ms >= 0.0
    assert response.diagnostics.timing.pinyin_ms >= 0.0
    assert response.diagnostics.cost_estimate is not None
    assert response.diagnostics.cost_estimate.confidence == "unavailable"


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
    assert response.diagnostics is None


def test_process_route_enforces_size_limit_without_content_length_header() -> None:
    request = _request_with_body(b"a" * (MAX_FILE_SIZE_BYTES + 1), "image/png")
    response = asyncio.run(process_image(request))

    assert response.status == "error"
    assert response.error is not None
    assert response.error.category == "validation"
    assert response.error.code == "file_too_large"
    assert response.diagnostics is None


def test_upload_within_limits_emits_guardrail_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("OCR_PROVIDER", raising=False)

    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider([RawOcrSegment(text="你好", language="zh", confidence=0.9)]),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider([RawPinyinSegment(hanzi="你", pinyin="nǐ")]),
    ), caplog.at_level(logging.INFO, logger="app.api.v1.process"):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "success"
    assert any("input_guardrail_pass" in record.message for record in caplog.records)


def test_process_route_low_confidence_ocr_returns_partial_with_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Low-confidence OCR segments with successful pinyin returns partial with guidance warning."""
    monkeypatch.delenv("OCR_PROVIDER", raising=False)
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [RawOcrSegment(text="你好", language="zh", confidence=0.45)]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider([
            RawPinyinSegment(hanzi="你", pinyin="nǐ"),
            RawPinyinSegment(hanzi="好", pinyin="hǎo"),
        ]),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "partial"
    assert response.error is None
    assert response.warnings is not None
    assert len(response.warnings) == 1
    assert response.warnings[0].category == "ocr"
    assert response.warnings[0].code == "ocr_low_confidence"
    assert response.diagnostics is not None
    assert response.diagnostics.timing.total_ms >= 0.0
    assert response.diagnostics.timing.ocr_ms >= 0.0
    assert response.diagnostics.timing.pinyin_ms >= 0.0
    assert response.diagnostics.cost_estimate is not None
    assert response.diagnostics.cost_estimate.confidence == "unavailable"


def test_process_route_low_confidence_includes_both_ocr_and_pinyin_data() -> None:
    """Low-confidence partial response preserves both OCR and pinyin."""
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [RawOcrSegment(text="你好", language="zh", confidence=0.45)]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider([
            RawPinyinSegment(hanzi="你", pinyin="nǐ"),
            RawPinyinSegment(hanzi="好", pinyin="hǎo"),
        ]),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.data is not None
    assert response.data.ocr is not None
    assert response.data.ocr.segments[0].text == "你好"
    # pinyin IS present in low-confidence partial (unlike story 2-3 pinyin-failure partial)
    assert response.data.pinyin is not None
    assert len(response.data.pinyin.segments) == 1
    assert response.data.pinyin.segments[0].source_text == "你好"


def test_process_route_low_confidence_trace_records_confidence_check_failed() -> None:
    """Low-confidence path must record confidence_check as 'failed', not 'ok'."""
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [RawOcrSegment(text="你好", language="zh", confidence=0.45)]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider([
            RawPinyinSegment(hanzi="你", pinyin="nǐ"),
            RawPinyinSegment(hanzi="好", pinyin="hǎo"),
        ]),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "partial"
    assert response.diagnostics is not None
    steps_by_name = {s.step: s.status for s in response.diagnostics.trace.steps}
    assert steps_by_name.get("confidence_check") == "failed"


def test_process_route_works_without_middleware_request_id() -> None:
    """process_image must not crash with AttributeError when request_id not in state."""
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/process",
        "headers": [(b"content-type", b"image/png")],
        "client": ("testclient", 123),
        "server": ("testserver", 80),
        "state": {},  # no request_id set by middleware
    }

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    request = StarletteRequest(scope, receive)
    response = asyncio.run(process_image(request))
    assert isinstance(response.request_id, str)
    assert response.request_id


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


def test_process_route_block_mode_with_exceeded_budget_returns_budget_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OCR_PROVIDER", "google_vision")
    monkeypatch.setenv("BUDGET_ENFORCE_MODE", "block")
    monkeypatch.setenv("DAILY_BUDGET_SGD", "1.0")
    _set_today_spend_sgd(1.0)

    with patch("app.services.ocr_service.get_ocr_provider") as get_ocr_provider:
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "error"
    assert response.error is not None
    assert response.error.category == "budget"
    assert response.error.code == "budget_daily_limit_exceeded"
    get_ocr_provider.assert_not_called()


def test_process_route_warn_mode_with_approaching_budget_returns_budget_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OCR_PROVIDER", "google_vision")
    monkeypatch.setenv("BUDGET_ENFORCE_MODE", "warn")
    monkeypatch.setenv("DAILY_BUDGET_SGD", "1.0")
    _set_today_spend_sgd(0.8)
    pinyin_segments = [
        RawPinyinSegment(hanzi="你", pinyin="nǐ"),
        RawPinyinSegment(hanzi="好", pinyin="hǎo"),
    ]

    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider([RawOcrSegment(text="你好", language="zh", confidence=0.98)]),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider(pinyin_segments),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "partial"
    assert response.warnings is not None
    warning_codes = {warning.code for warning in response.warnings}
    assert "budget_approaching_daily_limit" in warning_codes


def test_process_route_warn_mode_with_exceeded_budget_returns_budget_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OCR_PROVIDER", "google_vision")
    monkeypatch.setenv("BUDGET_ENFORCE_MODE", "warn")
    monkeypatch.setenv("DAILY_BUDGET_SGD", "1.0")
    _set_today_spend_sgd(1.0)
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

    assert response.status == "partial"
    assert response.warnings is not None
    warning_codes = {warning.code for warning in response.warnings}
    assert "budget_daily_limit_reached" in warning_codes


def test_process_route_warn_mode_success_is_downgraded_to_partial_with_budget_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OCR_PROVIDER", "google_vision")
    monkeypatch.setenv("BUDGET_ENFORCE_MODE", "warn")
    monkeypatch.setenv("DAILY_BUDGET_SGD", "1.0")
    _set_today_spend_sgd(0.8)
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

    assert response.status == "partial"
    assert response.data is not None
    assert response.error is None
    assert response.warnings is not None
    warning_codes = {warning.code for warning in response.warnings}
    assert "budget_approaching_daily_limit" in warning_codes


def test_process_route_below_budget_threshold_has_no_budget_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OCR_PROVIDER", "google_vision")
    monkeypatch.setenv("BUDGET_ENFORCE_MODE", "warn")
    monkeypatch.setenv("DAILY_BUDGET_SGD", "1.0")
    _set_today_spend_sgd(0.79)
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
    assert response.warnings is None


def test_process_route_non_gcv_provider_never_triggers_budget_enforcement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OCR_PROVIDER", raising=False)
    monkeypatch.setenv("BUDGET_ENFORCE_MODE", "block")
    monkeypatch.setenv("DAILY_BUDGET_SGD", "0.01")
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
    assert response.error is None
    assert response.warnings is None


def test_process_route_ocr_provider_failure_does_not_record_budget_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cost must not be charged when the OCR provider is unavailable (no billable call made)."""
    monkeypatch.setenv("OCR_PROVIDER", "google_vision")
    monkeypatch.setenv("BUDGET_ENFORCE_MODE", "block")
    monkeypatch.setenv("DAILY_BUDGET_SGD", "1.0")

    class FailingOcrProvider:
        def extract(self, *, image_bytes: bytes, content_type: str) -> list[RawOcrSegment]:
            raise ProviderUnavailableError("credentials unavailable")

    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=FailingOcrProvider(),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "error"
    assert response.error is not None
    assert response.error.code == "ocr_provider_unavailable"
    # Budget must be zero — no billable OCR call was made
    import datetime
    today = datetime.date.today().isoformat()
    today_usd = budget_service.daily_cost_store.snapshot().get(today, {}).get("total_usd", 0.0)
    assert today_usd == 0.0
