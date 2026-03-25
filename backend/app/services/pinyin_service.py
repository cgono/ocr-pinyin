"""Pinyin generation service.

Transforms a list of OCR segments into a structured PinyinData payload.
Wraps provider exceptions in typed PinyinServiceError for clean API contracts.
"""

import asyncio

from app.adapters.pinyin_provider import (
    PinyinExecutionError,
    PinyinProviderUnavailableError,
    get_pinyin_provider,
)
from app.schemas.process import OcrSegment, PinyinData, PinyinSegment

PINYIN_ERROR_CATEGORY = "pinyin"


class PinyinServiceError(Exception):
    def __init__(
        self, *, code: str, message: str, category: str = PINYIN_ERROR_CATEGORY
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.category = category


async def generate_pinyin(segments: list[OcrSegment]) -> PinyinData:
    """Generate pinyin for each OCR segment, tracking alignment status per segment.

    Aligned segments: provider succeeded; pinyin_text is space-joined tone-marked pinyin.
    Uncertain segments: PinyinExecutionError on that segment; segment is still returned.
    Systemic failure: PinyinProviderUnavailableError raises PinyinServiceError (nothing works).
    """
    provider = get_pinyin_provider()
    loop = asyncio.get_running_loop()
    result_segments: list[PinyinSegment] = []

    for ocr_segment in segments:
        text = ocr_segment.text
        if not text:
            continue
        try:
            raw_chars = await loop.run_in_executor(
                None,
                lambda t=text: provider.generate(text=t),
            )
            pinyin_text = " ".join(seg.pinyin for seg in raw_chars)
            result_segments.append(
                PinyinSegment(
                    source_text=text,
                    pinyin_text=pinyin_text,
                    alignment_status="aligned",
                )
            )
        except PinyinProviderUnavailableError as exc:
            raise PinyinServiceError(
                code="pinyin_provider_unavailable",
                message="Pinyin generation is temporarily unavailable. Please try again.",
            ) from exc
        except PinyinExecutionError:
            result_segments.append(
                PinyinSegment(
                    source_text=text,
                    pinyin_text="",
                    alignment_status="uncertain",
                    reason_code="pinyin_execution_failed",
                )
            )

    return PinyinData(segments=result_segments)
