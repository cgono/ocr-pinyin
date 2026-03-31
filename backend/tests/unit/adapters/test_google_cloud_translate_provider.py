import json
from unittest.mock import Mock

import pytest

from app.adapters.google_cloud_translate_provider import GoogleCloudTranslateProvider
from app.adapters.translation_provider import TranslationProviderUnavailableError


def test_translate_provider_initializes_client_with_credentials_without_project_kw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_ctor = Mock()
    credentials_factory = Mock(return_value="creds")
    translate_module = type("TranslateModule", (), {"Client": client_ctor})
    service_account_module = type(
        "ServiceAccountModule",
        (),
        {"Credentials": type("Creds", (), {"from_service_account_info": credentials_factory})},
    )

    monkeypatch.setattr("google.cloud.translate_v2", translate_module, raising=False)
    monkeypatch.setattr("google.oauth2.service_account", service_account_module, raising=False)
    monkeypatch.setenv(
        "GOOGLE_APPLICATION_CREDENTIALS_JSON",
        json.dumps({"type": "service_account", "project_id": "demo"}),
    )
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "ignored-project")

    GoogleCloudTranslateProvider()

    credentials_factory.assert_called_once()
    client_ctor.assert_called_once_with(credentials="creds")


def test_translate_provider_raises_typed_error_when_client_init_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BoomError(Exception):
        pass

    class FailingTranslateClient:
        def __init__(self, credentials=None) -> None:
            _ = credentials
            raise BoomError("bad init")

    translate_module = type("TranslateModule", (), {"Client": FailingTranslateClient})
    service_account_module = type(
        "ServiceAccountModule",
        (),
        {
            "Credentials": type(
                "Creds",
                (),
                {"from_service_account_info": staticmethod(lambda info, scopes: "creds")},
            )
        },
    )

    monkeypatch.setattr("google.cloud.translate_v2", translate_module, raising=False)
    monkeypatch.setattr("google.oauth2.service_account", service_account_module, raising=False)
    monkeypatch.setenv(
        "GOOGLE_APPLICATION_CREDENTIALS_JSON",
        json.dumps({"type": "service_account", "project_id": "demo"}),
    )

    with pytest.raises(TranslationProviderUnavailableError):
        GoogleCloudTranslateProvider()


def test_translate_raises_execution_error_when_api_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P-5: translate() must raise TranslationExecutionError when client returns None."""

    class NoneReturningClient:
        def translate(self, text: str, *, target_language: str, format_: str) -> None:
            return None

    client_ctor = Mock(return_value=NoneReturningClient())
    translate_module = type("TranslateModule", (), {"Client": client_ctor})
    service_account_module = type(
        "ServiceAccountModule",
        (),
        {
            "Credentials": type(
                "Creds", (), {"from_service_account_info": Mock(return_value="creds")}
            )
        },
    )

    monkeypatch.setattr("google.cloud.translate_v2", translate_module, raising=False)
    monkeypatch.setattr("google.oauth2.service_account", service_account_module, raising=False)
    monkeypatch.setenv(
        "GOOGLE_APPLICATION_CREDENTIALS_JSON",
        json.dumps({"type": "service_account", "project_id": "demo"}),
    )

    from app.adapters.translation_provider import TranslationExecutionError

    provider = GoogleCloudTranslateProvider()
    with pytest.raises(TranslationExecutionError):
        provider.translate(text="你好", target_language="en")
