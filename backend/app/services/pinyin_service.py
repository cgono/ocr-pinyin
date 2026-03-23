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
    """Generate pinyin for all OCR segments and return a structured PinyinData.

    Args:
        segments: Non-empty list of OCR segments with Chinese text.

    Returns:
        PinyinData containing one PinyinSegment per character across all segments.

    Raises:
        PinyinServiceError: on provider unavailability or execution failure.
    """
    provider = get_pinyin_provider()
    loop = asyncio.get_running_loop()

    all_segments: list[PinyinSegment] = []

    for ocr_segment in segments:
        text = ocr_segment.text
        if not text:
            continue
        try:
            raw_segments = await loop.run_in_executor(
                None,
                lambda t=text: provider.generate(text=t),
            )
        except PinyinProviderUnavailableError as exc:
            raise PinyinServiceError(
                code="pinyin_provider_unavailable",
                message="Pinyin generation is temporarily unavailable. Please try again.",
            ) from exc
        except PinyinExecutionError as exc:
            raise PinyinServiceError(
                code="pinyin_execution_failed",
                message="Pinyin generation encountered an error. Please try again.",
            ) from exc

        all_segments.extend(
            PinyinSegment(hanzi=seg.hanzi, pinyin=seg.pinyin)
            for seg in raw_segments
        )

    return PinyinData(segments=all_segments)
