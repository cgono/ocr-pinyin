import time
from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, Request, UploadFile

from app.core.metrics import metrics_store
from app.schemas.diagnostics import (
    DiagnosticsPayload,
    TimingInfo,
    TraceInfo,
    TraceStep,
    UploadContext,
)
from app.schemas.process import OcrData, ProcessData, ProcessError, ProcessResponse, ProcessWarning
from app.services.diagnostics_service import build_diagnostics
from app.services.image_validation import (
    ALLOWED_IMAGE_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
    ImageValidationError,
    validate_image_upload,
)
from app.services.ocr_service import OcrServiceError, extract_chinese_segments, is_low_confidence
from app.services.pinyin_service import PinyinServiceError, generate_pinyin

try:
    import sentry_sdk
except ImportError:  # pragma: no cover
    # Dependency should be installed, but requests must still work.
    sentry_sdk = None

router = APIRouter()


def _binary_openapi_content() -> dict[str, dict[str, dict[str, str]]]:
    return {
        mime_type: {"schema": {"type": "string", "format": "binary"}}
        for mime_type in sorted(ALLOWED_IMAGE_MIME_TYPES)
    }


async def _read_request_body_with_limit(request: Request, *, max_bytes: int) -> bytes:
    """Read request body incrementally and enforce a strict byte ceiling."""
    total_bytes = 0
    chunks: list[bytes] = []
    async for chunk in request.stream():
        if not chunk:
            continue
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            raise ImageValidationError(
                code="file_too_large",
                message="Image is too large. Please upload a smaller file and try again.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _make_diagnostics(
    *,
    upload_context: UploadContext,
    start_time: float,
    ocr_ms: float,
    pinyin_ms: float,
    trace_steps: list[TraceStep],
) -> DiagnosticsPayload:
    return build_diagnostics(
        upload_context=upload_context,
        timing=TimingInfo(
            total_ms=(time.monotonic() - start_time) * 1000,
            ocr_ms=ocr_ms,
            pinyin_ms=pinyin_ms,
        ),
        trace=TraceInfo(steps=trace_steps),
    )


def _set_sentry_tag(key: str, value: str) -> None:
    if sentry_sdk is None:
        return
    try:
        sentry_sdk.set_tag(key, value)
    except Exception:
        pass


def _set_sentry_request_context(request_id: str) -> None:
    _set_sentry_tag("request_id", request_id)


async def _build_process_response(
    image_bytes: bytes | None,
    content_type: str,
    *,
    request_id: str,
    start_time: float,
) -> ProcessResponse:
    upload_context = UploadContext(
        content_type=content_type,
        file_size_bytes=len(image_bytes) if image_bytes else 0,
    )
    trace_steps: list[TraceStep] = []

    if not image_bytes:
        _set_sentry_tag("outcome", "error")
        _set_sentry_tag("error_category", "upload")
        metrics_store.increment("error")
        return ProcessResponse(
            status="error",
            request_id=request_id,
            error=ProcessError(
                category="ocr",
                code="ocr_no_text_detected",
                message="No readable Chinese text was detected. Retake the photo and try again.",
            ),
        )

    ocr_start = time.monotonic()
    try:
        segments = await extract_chinese_segments(image_bytes, content_type)
        ocr_ms = (time.monotonic() - ocr_start) * 1000
        trace_steps.append(TraceStep(step="ocr", status="ok"))
    except OcrServiceError as error:
        trace_steps.append(TraceStep(step="ocr", status="failed"))
        _set_sentry_tag("outcome", "error")
        _set_sentry_tag("error_category", error.category)
        metrics_store.increment("error")
        return ProcessResponse(
            status="error",
            request_id=request_id,
            error=ProcessError(category=error.category, code=error.code, message=error.message),
        )

    pinyin_start = time.monotonic()
    try:
        pinyin_data = await generate_pinyin(segments)
        pinyin_ms = (time.monotonic() - pinyin_start) * 1000
        trace_steps.append(TraceStep(step="pinyin", status="ok"))
    except PinyinServiceError as error:
        pinyin_ms = (time.monotonic() - pinyin_start) * 1000
        trace_steps.append(TraceStep(step="pinyin", status="failed"))
        _set_sentry_tag("outcome", "partial")
        diagnostics = _make_diagnostics(
            upload_context=upload_context,
            start_time=start_time,
            ocr_ms=ocr_ms,
            pinyin_ms=pinyin_ms,
            trace_steps=trace_steps,
        )
        metrics_store.increment("partial")
        return ProcessResponse(
            status="partial",
            request_id=request_id,
            data=ProcessData(
                ocr=OcrData(segments=segments),
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

    if is_low_confidence(segments):
        trace_steps.append(TraceStep(step="confidence_check", status="failed"))
        _set_sentry_tag("outcome", "partial")
        diagnostics = _make_diagnostics(
            upload_context=upload_context,
            start_time=start_time,
            ocr_ms=ocr_ms,
            pinyin_ms=pinyin_ms,
            trace_steps=trace_steps,
        )
        metrics_store.increment("partial")
        return ProcessResponse(
            status="partial",
            request_id=request_id,
            data=ProcessData(
                ocr=OcrData(segments=segments),
                pinyin=pinyin_data,
                job_id=None,
            ),
            warnings=[
                ProcessWarning(
                    category="ocr",
                    code="ocr_low_confidence",
                    message=(
                        "OCR confidence is low. Consider retaking the photo for better results."
                    ),
                )
            ],
            diagnostics=diagnostics,
        )

    trace_steps.append(TraceStep(step="confidence_check", status="ok"))
    _set_sentry_tag("outcome", "success")
    diagnostics = _make_diagnostics(
        upload_context=upload_context,
        start_time=start_time,
        ocr_ms=ocr_ms,
        pinyin_ms=pinyin_ms,
        trace_steps=trace_steps,
    )
    metrics_store.increment("success")
    return ProcessResponse(
        status="success",
        request_id=request_id,
        data=ProcessData(
            ocr=OcrData(segments=segments),
            pinyin=pinyin_data,
            job_id=None,
        ),
        diagnostics=diagnostics,
    )


def _build_validation_error_response(
    request_id: str, error: ImageValidationError
) -> ProcessResponse:
    _set_sentry_tag("outcome", "error")
    _set_sentry_tag("error_category", error.category)
    metrics_store.increment("error")
    return ProcessResponse(
        status="error",
        request_id=request_id,
        error=ProcessError(
            category=error.category,
            code=error.code,
            message=error.message,
        ),
    )


@router.post('/process',
    response_model=ProcessResponse,
    response_model_exclude_none=True,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": _binary_openapi_content(),
        }
    },
)
async def process_image(
    request: Request,
) -> ProcessResponse:
    start_time = time.monotonic()
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    _set_sentry_request_context(request_id)

    # Guard: check Content-Length before reading the full body into memory (DoS protection).
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > MAX_FILE_SIZE_BYTES:
                return _build_validation_error_response(
                    request_id=request_id,
                    error=ImageValidationError(
                        code="file_too_large",
                        message="Image is too large. Please upload a smaller file and try again.",
                    ),
                )
        except ValueError:
            pass  # Malformed Content-Length header; let validation handle it after body read.

    try:
        file_bytes = await _read_request_body_with_limit(
            request,
            max_bytes=MAX_FILE_SIZE_BYTES,
        )
    except ImageValidationError as error:
        return _build_validation_error_response(request_id=request_id, error=error)

    content_type = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    file = None
    if file_bytes:
        file = UploadFile(
            filename="upload",
            file=BytesIO(file_bytes),
            headers={"content-type": content_type},
        )

    try:
        validate_image_upload(file)
    except ImageValidationError as error:
        return _build_validation_error_response(request_id=request_id, error=error)

    return await _build_process_response(
        file_bytes,
        content_type,
        request_id=request_id,
        start_time=start_time,
    )
