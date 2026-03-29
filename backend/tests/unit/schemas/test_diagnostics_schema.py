"""Tests for diagnostics schema validation constraints."""
import pytest
from pydantic import ValidationError

from app.schemas.diagnostics import CostEstimate, TimingInfo, TraceStep, UploadContext

# --- TimingInfo: required fields (#12) ---


def test_timing_info_requires_ocr_ms() -> None:
    with pytest.raises(ValidationError):
        TimingInfo(total_ms=100.0, pinyin_ms=50.0)  # ocr_ms missing


def test_timing_info_requires_pinyin_ms() -> None:
    with pytest.raises(ValidationError):
        TimingInfo(total_ms=100.0, ocr_ms=50.0)  # pinyin_ms missing


def test_timing_info_accepts_all_required_fields() -> None:
    t = TimingInfo(total_ms=200.0, ocr_ms=100.0, pinyin_ms=80.0)
    assert t.total_ms == 200.0
    assert t.ocr_ms == 100.0
    assert t.pinyin_ms == 80.0


# --- TimingInfo / UploadContext: non-negative constraints (#10) ---


def test_timing_info_rejects_negative_total_ms() -> None:
    with pytest.raises(ValidationError):
        TimingInfo(total_ms=-1.0, ocr_ms=0.0, pinyin_ms=0.0)


def test_timing_info_rejects_negative_ocr_ms() -> None:
    with pytest.raises(ValidationError):
        TimingInfo(total_ms=100.0, ocr_ms=-0.1, pinyin_ms=0.0)


def test_timing_info_rejects_negative_pinyin_ms() -> None:
    with pytest.raises(ValidationError):
        TimingInfo(total_ms=100.0, ocr_ms=0.0, pinyin_ms=-1.0)


def test_upload_context_rejects_negative_file_size() -> None:
    with pytest.raises(ValidationError):
        UploadContext(content_type="image/png", file_size_bytes=-1)


def test_upload_context_accepts_zero_file_size() -> None:
    ctx = UploadContext(content_type="image/png", file_size_bytes=0)
    assert ctx.file_size_bytes == 0


# --- TraceStep.step: Literal constraint (#6) ---


def test_trace_step_rejects_invalid_step_name() -> None:
    with pytest.raises(ValidationError):
        TraceStep(step="unknown_step", status="ok")


def test_trace_step_rejects_typo_in_step_name() -> None:
    with pytest.raises(ValidationError):
        TraceStep(step="OCR", status="ok")  # wrong case


def test_trace_step_accepts_ocr() -> None:
    ts = TraceStep(step="ocr", status="ok")
    assert ts.step == "ocr"


def test_trace_step_accepts_pinyin() -> None:
    ts = TraceStep(step="pinyin", status="ok")
    assert ts.step == "pinyin"


def test_trace_step_accepts_confidence_check() -> None:
    ts = TraceStep(step="confidence_check", status="ok")
    assert ts.step == "confidence_check"


def test_cost_estimate_accepts_full_with_numeric_values() -> None:
    estimate = CostEstimate(
        estimated_usd=0.0015,
        estimated_sgd=0.002025,
        confidence="full",
    )

    assert estimate.estimated_usd == pytest.approx(0.0015)
    assert estimate.estimated_sgd == pytest.approx(0.002025)
    assert estimate.confidence == "full"


def test_cost_estimate_accepts_unavailable_without_currency_values() -> None:
    estimate = CostEstimate(confidence="unavailable")

    assert estimate.estimated_usd is None
    assert estimate.estimated_sgd is None
    assert estimate.confidence == "unavailable"


def test_cost_estimate_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        CostEstimate(confidence="estimated")


def test_cost_estimate_rejects_full_confidence_without_currency_values() -> None:
    with pytest.raises(ValidationError):
        CostEstimate(confidence="full")


def test_cost_estimate_rejects_negative_usd() -> None:
    with pytest.raises(ValidationError):
        CostEstimate(confidence="full", estimated_usd=-0.001, estimated_sgd=0.002025)


def test_cost_estimate_rejects_negative_sgd() -> None:
    with pytest.raises(ValidationError):
        CostEstimate(confidence="full", estimated_usd=0.0015, estimated_sgd=-0.001)
