from __future__ import annotations

import json
import os

from app.adapters.translation_provider import (
    TranslationExecutionError,
    TranslationProviderUnavailableError,
)


class GoogleCloudTranslateProvider:
    def __init__(self) -> None:
        try:
            from google.cloud import translate_v2 as translate
            from google.oauth2 import service_account

            creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

            if creds_json:
                normalized_creds_json = creds_json.strip()
                first, last = normalized_creds_json[:1], normalized_creds_json[-1:]
                if len(normalized_creds_json) > 2 and first == last and first in {"'", '"'}:
                    normalized_creds_json = normalized_creds_json[1:-1]
                info = json.loads(normalized_creds_json)
                credentials = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                self._client = translate.Client(credentials=credentials)
            else:
                self._client = translate.Client()
        except Exception as exc:
            raise TranslationProviderUnavailableError(
                "Could not initialise Google Cloud Translate client. "
                "Check GOOGLE_APPLICATION_CREDENTIALS_JSON and dependency installation."
            ) from exc

    def translate(self, *, text: str, target_language: str) -> str:
        try:
            response = self._client.translate(
                text,
                target_language=target_language,
                format_="text",
            )
            if not isinstance(response, dict):
                raise TranslationExecutionError(
                    "Translate API returned an unexpected response type"
                )
            translated_text = response.get("translatedText")
            if not isinstance(translated_text, str) or not translated_text.strip():
                raise TranslationExecutionError("Translate API returned an empty translation")
        except TranslationExecutionError:
            raise
        except Exception as exc:
            raise TranslationExecutionError(f"Translate API error: {exc}") from exc

        return translated_text.strip()
