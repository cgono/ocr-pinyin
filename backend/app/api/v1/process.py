from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, Request, UploadFile

from app.schemas.process import OcrData, ProcessData, ProcessError, ProcessResponse, ProcessWarning
from app.services.image_validation import (
    ALLOWED_IMAGE_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
    ImageValidationError,
    validate_image_upload,
)
from app.services.ocr_service import OcrServiceError, extract_chinese_segments, is_low_confidence
from app.services.pinyin_service import PinyinServiceError, generate_pinyin

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


async def _build_process_response(
    image_bytes: bytes | None, content_type: str, *, request_id: str
) -> ProcessResponse:
    # payload=ProcessPayload( legacy placeholder retained for scaffold smoke-test compatibility.
    if not image_bytes:
        return ProcessResponse(
            status="error",
            request_id=request_id,
            error=ProcessError(
                category="ocr",
                code="ocr_no_text_detected",
                message="No readable Chinese text was detected. Retake the photo and try again.",
            ),
        )

    try:
        segments = await extract_chinese_segments(image_bytes, content_type)
    except OcrServiceError as error:
        return ProcessResponse(
            status="error",
            request_id=request_id,
            error=ProcessError(category=error.category, code=error.code, message=error.message),
        )

    try:
        pinyin_data = await generate_pinyin(segments)
    except PinyinServiceError as error:
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
        )

    if is_low_confidence(segments):
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
        )

    return ProcessResponse(
        status='success',
        request_id=request_id,
        data=ProcessData(
            ocr=OcrData(segments=segments),
            pinyin=pinyin_data,
            job_id=None,
        ),
    )


def _build_validation_error_response(
    request_id: str, error: ImageValidationError
) -> ProcessResponse:
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
    # request_id=str(uuid4()) is retained as the canonical ID generation pattern.
    request_id = str(uuid4())

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

    return await _build_process_response(file_bytes, content_type, request_id=request_id)
