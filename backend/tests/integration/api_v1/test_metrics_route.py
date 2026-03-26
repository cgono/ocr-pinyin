from unittest.mock import patch

from helpers import PNG_1X1_BYTES
from starlette.testclient import TestClient

from app.adapters.ocr_provider import RawOcrSegment
from app.adapters.pinyin_provider import RawPinyinSegment
from app.core.metrics import MetricsStore, metrics_store
from app.main import app

client = TestClient(app)


class StubPinyinProvider:
    def generate(self, *, text: str) -> list[RawPinyinSegment]:
        _ = text
        return [
            RawPinyinSegment(hanzi="你", pinyin="nǐ"),
            RawPinyinSegment(hanzi="好", pinyin="hǎo"),
        ]


def _reset_metrics() -> None:
    metrics_store.__dict__.update(MetricsStore().__dict__)


def test_metrics_returns_200() -> None:
    _reset_metrics()

    response = client.get("/v1/metrics")

    assert response.status_code == 200
    assert response.json()


def test_metrics_response_has_required_fields() -> None:
    _reset_metrics()

    response = client.get("/v1/metrics")
    body = response.json()

    assert set(body) == {
        "process_requests_total",
        "process_requests_success",
        "process_requests_partial",
        "process_requests_error",
    }


def test_metrics_initial_counts_are_zero() -> None:
    _reset_metrics()

    response = client.get("/v1/metrics")
    body = response.json()

    assert body == {
        "process_requests_total": 0,
        "process_requests_success": 0,
        "process_requests_partial": 0,
        "process_requests_error": 0,
    }


def test_metrics_increments_after_process_request() -> None:
    _reset_metrics()

    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=type(
            "StubOcrProvider",
            (),
            {
                "extract": lambda self, *, image_bytes, content_type: [
                    RawOcrSegment(text="你好", language="zh", confidence=0.95)
                ]
            },
        )(),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider(),
    ):
        process_response = client.post(
            "/v1/process",
            content=PNG_1X1_BYTES,
            headers={"content-type": "image/png"},
        )

    assert process_response.status_code == 200

    response = client.get("/v1/metrics")
    body = response.json()

    assert body["process_requests_total"] == 1
    assert body["process_requests_success"] == 1
