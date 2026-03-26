from unittest.mock import MagicMock, patch

from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.core.sentry import init_sentry


def test_init_sentry_no_dsn_does_not_raise(monkeypatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)

    init_sentry()


def test_init_sentry_empty_dsn_does_not_raise(monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "")

    init_sentry()


def test_init_sentry_calls_sentry_sdk_init_when_dsn_set(monkeypatch) -> None:
    fake_dsn = "https://abc123@o0.ingest.sentry.io/0"
    monkeypatch.setenv("SENTRY_DSN", fake_dsn)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_VERSION", "0.0.1")

    with patch("sentry_sdk.init") as mock_init:
        init_sentry()

    mock_init.assert_called_once()
    kwargs = mock_init.call_args.kwargs
    assert kwargs["dsn"] == fake_dsn
    assert kwargs["environment"] == "test"
    assert kwargs["release"] == "0.0.1"
    assert kwargs["send_default_pii"] is False
    assert kwargs["traces_sample_rate"] == 1.0
    integration_types = [type(i) for i in kwargs["integrations"]]
    assert StarletteIntegration in integration_types
    assert FastApiIntegration in integration_types


def test_init_sentry_suppresses_init_exception(monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "https://fake@o0.ingest.sentry.io/0")

    with patch("sentry_sdk.init", side_effect=RuntimeError("SDK error")):
        init_sentry()
