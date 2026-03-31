import pytest

from app.adapters.translation_provider import (
    NoOpTranslationProvider,
    get_translation_provider,
)


def test_get_translation_provider_returns_noop_when_translation_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRANSLATION_ENABLED", "false")

    provider = get_translation_provider()

    assert isinstance(provider, NoOpTranslationProvider)
