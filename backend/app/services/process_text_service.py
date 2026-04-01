import os
import re

from app.schemas.process import OcrSegment

TEXT_ERROR_CATEGORY = "validation"
_CJK_CHAR_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
_DEFAULT_MAX_SOURCE_TEXT_CHARS = 5000


class TextValidationError(Exception):
    def __init__(self, *, code: str, message: str, category: str = TEXT_ERROR_CATEGORY) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.category = category


def _get_max_source_text_chars() -> int:
    raw_value = os.getenv("TEXT_INPUT_MAX_CHARS", str(_DEFAULT_MAX_SOURCE_TEXT_CHARS))
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return _DEFAULT_MAX_SOURCE_TEXT_CHARS
    return parsed if parsed > 0 else _DEFAULT_MAX_SOURCE_TEXT_CHARS


def build_text_segments(source_text: str) -> list[OcrSegment]:
    normalized_text = source_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized_text:
        raise TextValidationError(
            code="text_empty",
            message="Paste some Chinese text to continue.",
        )

    if len(normalized_text) > _get_max_source_text_chars():
        raise TextValidationError(
            code="text_too_long",
            message="Text is too long. Shorten it and try again.",
        )

    candidate_lines = [line.strip() for line in normalized_text.split("\n") if line.strip()]
    segments: list[OcrSegment] = []

    for line in candidate_lines:
        language = "zh" if _CJK_CHAR_RE.search(line) is not None else "und"
        segments.append(
            OcrSegment(
                text=line,
                language=language,
                confidence=1.0,
                line_id=len(segments),
            )
        )

    if not any(s.language == "zh" for s in segments):
        raise TextValidationError(
            code="text_no_chinese_text",
            message="No Chinese text was detected. Paste Chinese text and try again.",
        )

    return segments
