from app.schemas.diagnostics import CostEstimate, TimingInfo, TraceInfo, TraceStep, UploadContext
from app.services.diagnostics_service import build_diagnostics


def test_build_diagnostics_returns_correct_structure() -> None:
    upload_context = UploadContext(content_type="image/jpeg", file_size_bytes=5000)
    timing = TimingInfo(total_ms=500.0, ocr_ms=300.0, pinyin_ms=150.0)
    trace = TraceInfo(steps=[TraceStep(step="ocr", status="ok")])

    result = build_diagnostics(upload_context=upload_context, timing=timing, trace=trace)

    assert result.upload_context.content_type == "image/jpeg"
    assert result.upload_context.file_size_bytes == 5000
    assert result.timing.total_ms == 500.0
    assert result.timing.ocr_ms == 300.0
    assert result.timing.pinyin_ms == 150.0
    assert len(result.trace.steps) == 1
    assert result.trace.steps[0].step == "ocr"
    assert result.trace.steps[0].status == "ok"


def test_build_diagnostics_timing_fields() -> None:
    upload_context = UploadContext(content_type="image/png", file_size_bytes=1)
    timing = TimingInfo(total_ms=12.5, ocr_ms=8.0, pinyin_ms=3.5)
    trace = TraceInfo(steps=[])

    result = build_diagnostics(upload_context=upload_context, timing=timing, trace=trace)

    assert result.timing.total_ms == 12.5
    assert result.timing.ocr_ms == 8.0
    assert result.timing.pinyin_ms == 3.5


def test_build_diagnostics_omits_cost_estimate_by_default() -> None:
    upload_context = UploadContext(content_type="image/png", file_size_bytes=1)
    timing = TimingInfo(total_ms=12.5, ocr_ms=8.0, pinyin_ms=3.5)
    trace = TraceInfo(steps=[])

    result = build_diagnostics(upload_context=upload_context, timing=timing, trace=trace)

    assert result.cost_estimate is None


def test_build_diagnostics_includes_cost_estimate_when_provided() -> None:
    upload_context = UploadContext(content_type="image/png", file_size_bytes=1)
    timing = TimingInfo(total_ms=12.5, ocr_ms=8.0, pinyin_ms=3.5)
    trace = TraceInfo(steps=[])
    cost_estimate = CostEstimate(
        estimated_usd=0.0015,
        estimated_sgd=0.002025,
        confidence="full",
    )

    result = build_diagnostics(
        upload_context=upload_context,
        timing=timing,
        trace=trace,
        cost_estimate=cost_estimate,
    )

    assert result.cost_estimate is not None
    assert result.cost_estimate.confidence == "full"
    assert result.cost_estimate.estimated_usd == 0.0015
