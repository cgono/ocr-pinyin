import logging
import time
from uuid import uuid4

from fastapi import APIRouter, Request

from app.api.v1.process import (
    _build_validation_error_response,
    _make_diagnostics,
    _set_sentry_request_context,
    _set_sentry_tag,
)
from app.core.metrics import metrics_store
from app.schemas.diagnostics import CostEstimate, TraceStep, UploadContext
from app.schemas.process import (
    PinyinData,
    PinyinSegment,
    ProcessData,
    ProcessError,
    ProcessResponse,
    ProcessWarning,
    TextProcessRequest,
)
from app.services import budget_service
from app.services.pinyin_service import PinyinServiceError, generate_pinyin
from app.services.process_text_service import TextValidationError, build_text_segments
from app.services.reading_service import build_reading_projection
from app.services.translation_service import enrich_translations

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/process-text",
    response_model=ProcessResponse,
    response_model_exclude_none=True,
)
async def process_text(payload: TextProcessRequest, request: Request) -> ProcessResponse:
    start_time = time.monotonic()
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    _set_sentry_request_context(request_id)

    budget_threshold = budget_service.check_budget_threshold()
    enforce_mode = budget_service.get_budget_enforce_mode()
    if budget_threshold == "exceeded" and enforce_mode == "block":
        _set_sentry_tag("outcome", "error")
        _set_sentry_tag("error_category", "budget")
        metrics_store.increment("error")
        return ProcessResponse(
            status="error",
            request_id=request_id,
            error=ProcessError(
                category="budget",
                code="budget_daily_limit_exceeded",
                message="Daily processing budget has been reached. Please try again tomorrow.",
            ),
        )

    try:
        segments = build_text_segments(payload.source_text)
    except TextValidationError as error:
        return _build_validation_error_response(request_id=request_id, error=error)

    cjk_segments = [s for s in segments if s.language == "zh"]
    passthrough_segments = [s for s in segments if s.language != "zh"]

    upload_context = UploadContext(
        content_type="text/plain",
        file_size_bytes=len(payload.source_text.encode("utf-8")),
    )
    translated_char_count = sum(len(segment.text) for segment in cjk_segments)
    cost_estimate = budget_service.estimate_text_processing_cost(
        char_count=translated_char_count
    )

    pinyin_start = time.monotonic()
    try:
        pinyin_data = await generate_pinyin(cjk_segments)
        pinyin_ms = (time.monotonic() - pinyin_start) * 1000
        try:
            pinyin_data = await enrich_translations(pinyin_data)
        except Exception:
            logger.exception("translation enrichment failed; continuing without translations")
            cost_estimate = CostEstimate(confidence="unavailable")
        if passthrough_segments:
            passthrough_pinyin = [
                PinyinSegment(
                    source_text=s.text,
                    pinyin_text=s.text,
                    alignment_status="aligned",
                    line_id=s.line_id,
                )
                for s in passthrough_segments
            ]
            merged = pinyin_data.segments + passthrough_pinyin
            merged.sort(key=lambda seg: seg.line_id if seg.line_id is not None else float("inf"))
            pinyin_data = PinyinData(segments=merged)
        budget_service.record_request_cost(cost_estimate)
        try:
            reading_data = build_reading_projection(pinyin_data)
        except Exception:
            logger.exception(
                "reading projection failed for pasted text; falling back to reading=None"
            )
            reading_data = None
        trace_steps = [
            TraceStep(step="ocr", status="skipped"),
            TraceStep(step="pinyin", status="ok"),
        ]
    except PinyinServiceError as error:
        pinyin_ms = (time.monotonic() - pinyin_start) * 1000
        _set_sentry_tag("outcome", "partial")
        diagnostics = _make_diagnostics(
            upload_context=upload_context,
            start_time=start_time,
            ocr_ms=0.0,
            pinyin_ms=pinyin_ms,
            trace_steps=[
                TraceStep(step="ocr", status="skipped"),
                TraceStep(step="pinyin", status="failed"),
            ],
            cost_estimate=cost_estimate,
        )
        metrics_store.increment("partial")
        return ProcessResponse(
            status="partial",
            request_id=request_id,
            data=ProcessData(
                message=(
                    "Text was accepted, but pronunciation generation is temporarily"
                    " unavailable."
                ),
                job_id=None,
            ),
            warnings=[
                ProcessWarning(
                    category=error.category,
                    code=error.code,
                    message=error.message,
                )
            ],
            diagnostics=diagnostics,
        )

    diagnostics = _make_diagnostics(
        upload_context=upload_context,
        start_time=start_time,
        ocr_ms=0.0,
        pinyin_ms=pinyin_ms,
        trace_steps=trace_steps,
        cost_estimate=cost_estimate,
    )

    budget_warn: ProcessWarning | None = None
    if budget_threshold in ("warn", "exceeded"):
        budget_warn = ProcessWarning(
            category="budget",
            code=(
                "budget_daily_limit_reached"
                if budget_threshold == "exceeded"
                else "budget_approaching_daily_limit"
            ),
            message=(
                "Daily processing budget has been reached. Results may be limited soon."
                if budget_threshold == "exceeded"
                else "Daily processing budget is nearly reached."
            ),
        )

    _set_sentry_tag("outcome", "success")
    metrics_store.increment("success")
    response = ProcessResponse(
        status="success",
        request_id=request_id,
        data=ProcessData(
            pinyin=pinyin_data,
            reading=reading_data,
            job_id=None,
        ),
        diagnostics=diagnostics,
    )

    if budget_warn is not None:
        return ProcessResponse(
            status="partial",
            request_id=response.request_id,
            data=response.data,
            warnings=[budget_warn],
            diagnostics=response.diagnostics,
        )

    return response
