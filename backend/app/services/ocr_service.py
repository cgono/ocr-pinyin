import asyncio
import logging
import re

from app.adapters.ocr_provider import (
    OcrExecutionError,
    ProviderUnavailableError,
    RawOcrSegment,
    get_ocr_provider,
)
from app.schemas.process import OcrSegment

OCR_ERROR_CATEGORY = "ocr"

logger = logging.getLogger(__name__)


class OcrServiceError(Exception):
    def __init__(self, *, code: str, message: str, category: str = OCR_ERROR_CATEGORY) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.category = category


_CJK_CHAR_RE = re.compile(r"[\u3400-\u9fff]")


async def extract_chinese_segments(image_bytes: bytes, content_type: str) -> list[OcrSegment]:
    provider = get_ocr_provider()
    loop = asyncio.get_running_loop()
    try:
        raw_segments = await loop.run_in_executor(
            None,
            lambda: provider.extract(image_bytes=image_bytes, content_type=content_type),
        )
    except ProviderUnavailableError as exc:
        logger.exception("OCR provider unavailable: %s", exc)
        raise OcrServiceError(
            code="ocr_provider_unavailable",
            message="Text extraction is temporarily unavailable. Please try again.",
        ) from exc
    except OcrExecutionError as exc:
        logger.exception("OCR execution error: %s", exc)
        raise OcrServiceError(
            code="ocr_execution_failed",
            message="Text extraction encountered an error. Please try again.",
        ) from exc

    segments = [_normalize_segment(segment) for segment in raw_segments]
    usable_segments = [segment for segment in segments if _is_usable_chinese_segment(segment)]

    if not usable_segments:
        # Distinguish blank/unreadable image from non-Chinese content
        non_chinese = [s for s in segments if s.text]
        if non_chinese:
            logger.debug(
                "OCR returned %d non-Chinese segment(s); no Chinese text detected",
                len(non_chinese),
            )
            raise OcrServiceError(
                code="ocr_no_chinese_text",
                message=(
                    "No Chinese text was detected. The image may contain non-Chinese content."
                    " Retake the photo focused on Chinese text."
                ),
            )
        raise OcrServiceError(
            code="ocr_no_text_detected",
            message="No readable Chinese text was detected. Retake the photo and try again.",
        )

    return usable_segments


def _normalize_segment(segment: RawOcrSegment) -> OcrSegment:
    return OcrSegment(
        text=(segment.text or "").strip(),
        language=_normalize_language(segment.language),
        confidence=_normalize_confidence(segment.confidence),
    )


def _normalize_language(language: str | None) -> str:
    value = (language or "und").strip().lower()
    return value or "und"


def _normalize_confidence(confidence: float | int | None) -> float:
    if confidence is None:
        return 0.0

    normalized = float(confidence)
    if normalized > 1.0 and normalized <= 100.0:
        normalized = normalized / 100.0

    return max(0.0, min(normalized, 1.0))


def _is_usable_chinese_segment(segment: OcrSegment) -> bool:
    if not segment.text:
        return False
    has_cjk_text = _CJK_CHAR_RE.search(segment.text) is not None
    is_chinese_language = segment.language.startswith("zh")
    return has_cjk_text or is_chinese_language
