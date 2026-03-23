"""Unit tests for the PyPinyinProvider adapter."""


import pytest

from app.adapters.pinyin_provider import PinyinExecutionError
from app.adapters.pypinyin_provider import PyPinyinProvider


def test_generate_returns_per_char_pinyin_for_chinese_text() -> None:
    provider = PyPinyinProvider()
    result = provider.generate(text="你好")

    assert len(result) == 2
    assert result[0].hanzi == "你"
    assert result[0].pinyin  # tone-marked pinyin string, e.g. "nǐ"
    assert result[1].hanzi == "好"
    assert result[1].pinyin  # e.g. "hǎo"


def test_generate_returns_empty_list_for_empty_text() -> None:
    provider = PyPinyinProvider()
    result = provider.generate(text="")

    assert result == []


def test_generate_passes_non_chinese_chars_through() -> None:
    provider = PyPinyinProvider()
    # "A" is not Chinese; pypinyin returns it as-is
    result = provider.generate(text="A")

    assert len(result) == 1
    assert result[0].hanzi == "A"
    assert result[0].pinyin == "A"


def test_generate_pinyin_has_tone_marks() -> None:
    provider = PyPinyinProvider()
    result = provider.generate(text="你好")

    # Tone-marked pinyin uses Unicode combining characters (e.g. ǐ, ǎ)
    all_pinyin = "".join(seg.pinyin for seg in result)
    assert any(ord(char) > 127 for char in all_pinyin), (
        "Expected tone-marked Unicode characters in pinyin output"
    )


def test_generate_raises_when_provider_output_is_misaligned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = PyPinyinProvider()
    monkeypatch.setattr(
        "app.adapters.pypinyin_provider.pypinyin.pinyin",
        lambda *_args, **_kwargs: [["nǐ"]],
    )

    with pytest.raises(PinyinExecutionError, match="malformed output"):
        provider.generate(text="你好")
