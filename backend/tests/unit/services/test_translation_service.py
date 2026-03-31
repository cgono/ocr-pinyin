import asyncio
import time

import pytest

from app.adapters.translation_provider import (
    TranslationExecutionError,
    TranslationProviderUnavailableError,
)
from app.schemas.process import PinyinData, PinyinSegment
from app.services.translation_service import enrich_translations


def _make_segment(
    source_text: str,
    *,
    line_id: int | None = None,
    translation_text: str | None = None,
) -> PinyinSegment:
    return PinyinSegment(
        source_text=source_text,
        pinyin_text="placeholder",
        alignment_status="aligned",
        line_id=line_id,
        translation_text=translation_text,
    )


class RecordingTranslationProvider:
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping
        self.calls: list[str] = []

    def translate(self, *, text: str, target_language: str) -> str:
        self.calls.append(text)
        return self.mapping[text]


def test_enrich_translations_applies_same_line_translation_to_each_segment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = RecordingTranslationProvider(
        {
            "老师": "teacher",
            "你好": "hello",
        }
    )
    monkeypatch.setenv("TRANSLATION_ENABLED", "true")
    monkeypatch.setattr(
        "app.services.translation_service.get_translation_provider",
        lambda: provider,
    )

    result = asyncio.run(
        enrich_translations(
            PinyinData(
                segments=[
                    _make_segment("老", line_id=0),
                    _make_segment("师", line_id=0),
                    _make_segment("你好", line_id=1),
                ]
            )
        )
    )

    assert provider.calls == ["老师", "你好"]
    assert [segment.translation_text for segment in result.segments] == [
        "teacher",
        "teacher",
        "hello",
    ]


def test_enrich_translations_returns_nulls_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRANSLATION_ENABLED", "false")

    result = asyncio.run(
        enrich_translations(
            PinyinData(segments=[_make_segment("你好", line_id=0, translation_text="stale")])
        )
    )

    assert result.segments[0].translation_text is None


def test_enrich_translations_returns_nulls_when_provider_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class UnavailableProvider:
        def translate(self, *, text: str, target_language: str) -> str:
            raise TranslationProviderUnavailableError("not configured")

    monkeypatch.setenv("TRANSLATION_ENABLED", "true")
    monkeypatch.setattr(
        "app.services.translation_service.get_translation_provider",
        UnavailableProvider,
    )

    with caplog.at_level("WARNING"):
        result = asyncio.run(
            enrich_translations(PinyinData(segments=[_make_segment("你好", line_id=0)]))
        )

    assert result.segments[0].translation_text is None
    assert "translation provider unavailable" in caplog.text.lower()


def test_enrich_translations_returns_nulls_when_translation_execution_fails(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class FailingProvider:
        def translate(self, *, text: str, target_language: str) -> str:
            raise TranslationExecutionError("boom")

    monkeypatch.setenv("TRANSLATION_ENABLED", "true")
    monkeypatch.setattr(
        "app.services.translation_service.get_translation_provider",
        FailingProvider,
    )

    with caplog.at_level("WARNING"):
        result = asyncio.run(
            enrich_translations(PinyinData(segments=[_make_segment("你好", line_id=0)]))
        )

    assert result.segments[0].translation_text is None
    assert "translation execution failed" in caplog.text.lower()


def test_enrich_translations_skips_translation_for_segments_with_null_line_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P-6/P-7: segments with line_id=None should never trigger a provider call."""

    class AssertNotCalledProvider:
        def translate(self, *, text: str, target_language: str) -> str:
            raise AssertionError("translate must not be called for null line_id segments")

    monkeypatch.setenv("TRANSLATION_ENABLED", "true")
    monkeypatch.setattr(
        "app.services.translation_service.get_translation_provider",
        lambda: AssertNotCalledProvider(),
    )

    result = asyncio.run(
        enrich_translations(
            PinyinData(
                segments=[
                    _make_segment("老师叫", line_id=None),
                    _make_segment("同学们好", line_id=None),
                ]
            )
        )
    )

    assert all(seg.translation_text is None for seg in result.segments)


def test_enrich_translations_returns_null_translation_when_translate_times_out(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """P-3: a hanging translate call should time out and return null, not block forever."""

    class SlowProvider:
        def translate(self, *, text: str, target_language: str) -> str:
            time.sleep(0.05)  # longer than the patched timeout
            return "hello"

    monkeypatch.setenv("TRANSLATION_ENABLED", "true")
    monkeypatch.setattr(
        "app.services.translation_service.get_translation_provider",
        lambda: SlowProvider(),
    )
    monkeypatch.setattr(
        "app.services.translation_service._TRANSLATION_TIMEOUT_SECONDS",
        0.01,
    )

    with caplog.at_level("WARNING"):
        result = asyncio.run(
            enrich_translations(
                PinyinData(segments=[_make_segment("你好", line_id=0)])
            )
        )

    assert result.segments[0].translation_text is None


def test_enrich_translations_returns_null_translation_on_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """P-4: any unexpected exception from translate should be caught and return null."""

    class BuggyProvider:
        def translate(self, *, text: str, target_language: str) -> str:
            raise RuntimeError("unexpected internal error")

    monkeypatch.setenv("TRANSLATION_ENABLED", "true")
    monkeypatch.setattr(
        "app.services.translation_service.get_translation_provider",
        lambda: BuggyProvider(),
    )

    with caplog.at_level("WARNING"):
        result = asyncio.run(
            enrich_translations(
                PinyinData(segments=[_make_segment("你好", line_id=0)])
            )
        )

    assert result.segments[0].translation_text is None
