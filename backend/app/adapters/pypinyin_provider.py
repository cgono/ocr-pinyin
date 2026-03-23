"""PyPinyin-backed pinyin provider.

Uses the `pypinyin` library (pinned: 0.55.0) to convert Chinese characters
into tone-marked pinyin strings.  One RawPinyinSegment is produced per
input character; non-Chinese characters are passed through unchanged.
"""

import pypinyin

from app.adapters.pinyin_provider import PinyinExecutionError, RawPinyinSegment


class PyPinyinProvider:
    """Synchronous pinyin provider that wraps pypinyin.pinyin()."""

    def generate(self, *, text: str) -> list[RawPinyinSegment]:
        """Return per-character pinyin for *text*.

        Raises:
            PinyinExecutionError: if pypinyin raises an unexpected exception.
        """
        if not text:
            return []

        try:
            # TONE style: returns tone marks as Unicode combining characters (e.g. "nǐ").
            # heteronym=False uses the most-common reading for each character.
            per_char_pinyin: list[list[str]] = pypinyin.pinyin(
                text, style=pypinyin.Style.TONE, heteronym=False
            )
        except Exception as exc:  # pragma: no cover – unexpected library error
            raise PinyinExecutionError(str(exc)) from exc

        characters = list(text)
        if len(per_char_pinyin) != len(characters):
            raise PinyinExecutionError("Pinyin provider returned malformed output")
        segments: list[RawPinyinSegment] = []
        for char, pinyin_options in zip(characters, per_char_pinyin):
            # pypinyin returns a list of readings per character; take the first.
            reading = pinyin_options[0] if pinyin_options else char
            segments.append(RawPinyinSegment(hanzi=char, pinyin=reading))

        return segments
