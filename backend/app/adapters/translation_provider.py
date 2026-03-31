from typing import Protocol


class TranslationProvider(Protocol):
    def translate(self, *, text: str, target_language: str) -> str:
        """Translate source text into the requested target language."""


class TranslationProviderUnavailableError(Exception):
    pass


class TranslationExecutionError(Exception):
    pass


class NoOpTranslationProvider:
    def translate(self, *, text: str, target_language: str) -> str:
        _ = (text, target_language)
        raise TranslationProviderUnavailableError("Translation provider is not configured")


def get_translation_provider() -> TranslationProvider:
    import os

    if os.environ.get("TRANSLATION_ENABLED", "false").strip().lower() != "true":
        return NoOpTranslationProvider()

    from app.adapters.google_cloud_translate_provider import GoogleCloudTranslateProvider

    return GoogleCloudTranslateProvider()
