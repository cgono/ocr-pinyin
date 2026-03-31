from __future__ import annotations

from collections.abc import Iterable

from app.schemas.process import (
    PinyinData,
    PinyinSegment,
    ReadingData,
    ReadingGroup,
    ReadingProviderInfo,
)

_PROVIDER_NAME = "built_in_rules"
_PROVIDER_VERSION = "v1"
_TERMINAL_PUNCTUATION = ("。", "！", "？", ".", "!", "?")


def _group_segments_by_line(
    segments: list[PinyinSegment],
) -> list[tuple[int, list[tuple[int, PinyinSegment]]]]:
    groups: list[tuple[int, list[tuple[int, PinyinSegment]]]] = []
    current_group: list[tuple[int, PinyinSegment]] = []
    current_line_id: int | None = None

    for index, segment in enumerate(segments):
        if segment.line_id is None:
            if current_group:
                groups.append((current_line_id or 0, current_group))
                current_group = []
                current_line_id = None
            continue

        if current_group and segment.line_id != current_line_id:
            groups.append((current_line_id or 0, current_group))
            current_group = []

        current_group.append((index, segment))
        current_line_id = segment.line_id

    if current_group:
        groups.append((current_line_id or 0, current_group))

    return groups


def _concat_source_text(group: Iterable[tuple[int, PinyinSegment]]) -> str:
    return "".join(segment.source_text for _, segment in group).strip()


def _derive_display_text(raw_text: str) -> str:
    if not raw_text:
        return raw_text
    if raw_text.endswith(_TERMINAL_PUNCTUATION):
        return raw_text
    return f"{raw_text}。"


def build_reading_projection(pinyin_data: PinyinData) -> ReadingData | None:
    groups_by_line = _group_segments_by_line(pinyin_data.segments)
    if not groups_by_line:
        return None

    reading_groups: list[ReadingGroup] = []
    applied = False
    confidences: list[float] = []

    for group_id, (line_id, indexed_segments) in enumerate(groups_by_line):
        raw_text = _concat_source_text(indexed_segments)
        if not raw_text:
            continue

        display_text = _derive_display_text(raw_text)
        group_applied = display_text != raw_text
        applied = applied or group_applied
        confidence = 0.78 if group_applied else 0.64
        confidences.append(confidence)

        reading_groups.append(
            ReadingGroup(
                group_id=f"rg_{group_id}",
                line_id=line_id,
                raw_text=raw_text,
                display_text=display_text,
                playback_text=display_text,
                confidence=confidence,
                segment_indexes=[index for index, _ in indexed_segments],
            )
        )

    if not reading_groups or not applied:
        return None

    provider_confidence = round(sum(confidences) / len(confidences), 2)
    return ReadingData(
        mode="derived",
        provider=ReadingProviderInfo(
            kind="heuristic",
            name=_PROVIDER_NAME,
            version=_PROVIDER_VERSION,
            applied=True,
            confidence=provider_confidence,
            warnings=[],
        ),
        groups=reading_groups,
    )
