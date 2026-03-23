from app.main import _get_cors_origins


def test_get_cors_origins_defaults_to_local_dev_origins(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    assert _get_cors_origins() == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_get_cors_origins_parses_configured_list(monkeypatch) -> None:
    monkeypatch.setenv(
        "CORS_ALLOW_ORIGINS",
        "https://app.example.com, http://localhost:4173",
    )
    assert _get_cors_origins() == [
        "https://app.example.com",
        "http://localhost:4173",
    ]
