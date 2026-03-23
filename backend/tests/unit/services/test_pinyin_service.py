"""Unit tests for the pinyin generation service."""

import asyncio

import pytest

from app.adapters.pinyin_provider import RawPinyinSegment
from app.schemas.process import OcrSegment
from app.services.pinyin_service import PinyinServiceError, generate_pinyin


class StubPinyinProvider:
    def __init__(self, segments: list[RawPinyinSegment]) -> None:
        self._segments = segments

    def generate(self, *, text: str) -> list[RawPinyinSegment]:
        _ = text
        return self._segments


def _make_ocr_segment(text: str, language: str = "zh", confidence: float = 0.9) -> OcrSegment:
    return OcrSegment(text=text, language=language, confidence=confidence)


def test_generate_pinyin_returns_per_char_segments(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.pinyin_service.get_pinyin_provider",
        lambda: StubPinyinProvider(
            [
                RawPinyinSegment(hanzi="你", pinyin="nǐ"),
                RawPinyinSegment(hanzi="好", pinyin="hǎo"),
            ]
        ),
    )
    segments = [_make_ocr_segment("你好")]
    result = asyncio.run(generate_pinyin(segments))

    assert len(result.segments) == 2
    assert result.segments[0].hanzi == "你"
    assert result.segments[0].pinyin == "nǐ"
    assert result.segments[1].hanzi == "好"
    assert result.segments[1].pinyin == "hǎo"


def test_generate_pinyin_concatenates_multiple_ocr_segments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    class CountingProvider:
        def generate(self, *, text: str) -> list[RawPinyinSegment]:
            nonlocal call_count
            call_count += 1
            if text == "你好":
                return [
                    RawPinyinSegment(hanzi="你", pinyin="nǐ"),
                    RawPinyinSegment(hanzi="好", pinyin="hǎo"),
                ]
            return [RawPinyinSegment(hanzi="世", pinyin="shì")]

    monkeypatch.setattr("app.services.pinyin_service.get_pinyin_provider", CountingProvider)
    segments = [_make_ocr_segment("你好"), _make_ocr_segment("世")]
    result = asyncio.run(generate_pinyin(segments))

    assert call_count == 2
    assert len(result.segments) == 3
    assert result.segments[2].hanzi == "世"


def test_generate_pinyin_skips_empty_segment_text(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class TrackingProvider:
        def generate(self, *, text: str) -> list[RawPinyinSegment]:
            calls.append(text)
            return [RawPinyinSegment(hanzi="你", pinyin="nǐ")]

    monkeypatch.setattr("app.services.pinyin_service.get_pinyin_provider", TrackingProvider)
    segments = [_make_ocr_segment(""), _make_ocr_segment("你")]
    result = asyncio.run(generate_pinyin(segments))

    # Empty-text segment should not trigger a provider call
    assert calls == ["你"]
    assert len(result.segments) == 1


def test_generate_pinyin_raises_on_provider_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.adapters.pinyin_provider import PinyinProviderUnavailableError

    class UnavailableProvider:
        def generate(self, *, text: str) -> list[RawPinyinSegment]:
            raise PinyinProviderUnavailableError("not configured")

    monkeypatch.setattr("app.services.pinyin_service.get_pinyin_provider", UnavailableProvider)

    with pytest.raises(PinyinServiceError) as exc:
        asyncio.run(generate_pinyin([_make_ocr_segment("你好")]))

    assert exc.value.category == "pinyin"
    assert exc.value.code == "pinyin_provider_unavailable"


def test_generate_pinyin_raises_on_execution_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.adapters.pinyin_provider import PinyinExecutionError

    class FailingProvider:
        def generate(self, *, text: str) -> list[RawPinyinSegment]:
            raise PinyinExecutionError("internal failure")

    monkeypatch.setattr("app.services.pinyin_service.get_pinyin_provider", FailingProvider)

    with pytest.raises(PinyinServiceError) as exc:
        asyncio.run(generate_pinyin([_make_ocr_segment("你好")]))

    assert exc.value.category == "pinyin"
    assert exc.value.code == "pinyin_execution_failed"
