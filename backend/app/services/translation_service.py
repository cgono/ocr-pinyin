from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor

from app.adapters.translation_provider import (
    TranslationExecutionError,
    TranslationProviderUnavailableError,
    get_translation_provider,
)
from app.schemas.process import PinyinData, PinyinSegment

logger = logging.getLogger(__name__)

_TRANSLATION_TIMEOUT_SECONDS: float = 5.0
# Bounded executor: wait_for cancels the await but not the underlying thread. Capping
# max_workers limits how many stalled threads can accumulate when provider calls hang.
_TRANSLATION_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="translation")


def _translation_enabled() -> bool:
    return os.environ.get("TRANSLATION_ENABLED", "false").strip().lower() == "true"


def _clone_with_translation(
    segments: Iterable[PinyinSegment], translation_text: str | None
) -> list[PinyinSegment]:
    return [
        segment.model_copy(update={"translation_text": translation_text}) for segment in segments
    ]


def _group_segments_by_line(segments: list[PinyinSegment]) -> list[list[PinyinSegment]]:
    if not segments:
        return []

    groups: list[list[PinyinSegment]] = []
    current_group: list[PinyinSegment] = []
    current_line_id = object()

    for segment in segments:
        line_id = segment.line_id
        if current_group and line_id != current_line_id:
            groups.append(current_group)
            current_group = []
        current_group.append(segment)
        current_line_id = line_id

    if current_group:
        groups.append(current_group)

    return groups


async def enrich_translations(pinyin_data: PinyinData) -> PinyinData:
    if not _translation_enabled():
        return PinyinData(segments=_clone_with_translation(pinyin_data.segments, None))

    if not pinyin_data.segments:
        return pinyin_data

    try:
        provider = get_translation_provider()
    except TranslationProviderUnavailableError:
        logger.warning("Translation provider unavailable during initialization")
        return PinyinData(segments=_clone_with_translation(pinyin_data.segments, None))

    translated_segments: list[PinyinSegment] = []
    loop = asyncio.get_running_loop()

    for group in _group_segments_by_line(pinyin_data.segments):
        if group[0].line_id is None:
            translated_segments.extend(_clone_with_translation(group, None))
            continue

        source_text = "".join(segment.source_text for segment in group).strip()
        if not source_text:
            translated_segments.extend(_clone_with_translation(group, None))
            continue

        try:
            translation_text = await asyncio.wait_for(
                loop.run_in_executor(
                    _TRANSLATION_EXECUTOR,
                    lambda text=source_text: provider.translate(
                        text=text,
                        target_language="en",
                    ),
                ),
                timeout=_TRANSLATION_TIMEOUT_SECONDS,
            )
        except TranslationProviderUnavailableError:
            logger.warning("Translation provider unavailable while translating line")
            translation_text = None
        except TranslationExecutionError:
            logger.warning("Translation execution failed for line", exc_info=True)
            translation_text = None
        except asyncio.TimeoutError:
            logger.warning("Translation timed out for line")
            translation_text = None
        except Exception:
            logger.warning("Unexpected error during translation for line", exc_info=True)
            translation_text = None

        translated_segments.extend(_clone_with_translation(group, translation_text))

    return PinyinData(segments=translated_segments)
