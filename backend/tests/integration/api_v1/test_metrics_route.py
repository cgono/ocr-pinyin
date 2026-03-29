import datetime
from unittest.mock import patch

from helpers import PNG_1X1_BYTES
from starlette.testclient import TestClient

from app.adapters.ocr_provider import RawOcrSegment
from app.adapters.pinyin_provider import RawPinyinSegment
from app.core.metrics import MetricsStore, metrics_store
from app.main import app
from app.schemas.diagnostics import CostEstimate
from app.services import budget_service

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


def _reset_daily_costs() -> None:
    budget_service.daily_cost_store.__dict__.update(
        budget_service.DailyCostStore().__dict__
    )


def test_metrics_returns_200() -> None:
    _reset_metrics()
    _reset_daily_costs()

    response = client.get("/v1/metrics")

    assert response.status_code == 200
    assert response.json()


def test_metrics_response_has_required_fields() -> None:
    _reset_metrics()
    _reset_daily_costs()

    response = client.get("/v1/metrics")
    body = response.json()

    assert set(body) == {
        "process_requests_total",
        "process_requests_success",
        "process_requests_partial",
        "process_requests_error",
        "daily_costs",
    }


def test_metrics_initial_counts_are_zero() -> None:
    _reset_metrics()
    _reset_daily_costs()

    response = client.get("/v1/metrics")
    body = response.json()

    assert body == {
        "process_requests_total": 0,
        "process_requests_success": 0,
        "process_requests_partial": 0,
        "process_requests_error": 0,
        "daily_costs": {},
    }


def test_metrics_returns_recorded_daily_costs() -> None:
    _reset_metrics()
    _reset_daily_costs()
    budget_service.record_request_cost(
        CostEstimate(estimated_usd=0.0015, estimated_sgd=0.002025, confidence="full")
    )

    response = client.get("/v1/metrics")

    assert response.status_code == 200
    today = datetime.date.today().isoformat()
    assert response.json()["daily_costs"] == {
        today: {
            "total_usd": 0.0015,
            "total_sgd": 0.002025,
            "request_count": 1,
        }
    }


def test_metrics_increments_after_process_request() -> None:
    _reset_metrics()
    _reset_daily_costs()

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
    ), patch.dict("os.environ", {"OCR_PROVIDER": "google_vision"}):
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
    today = datetime.date.today().isoformat()
    assert today in body["daily_costs"]
    assert body["daily_costs"][today]["request_count"] == 1


def test_metrics_daily_costs_includes_prior_day_entries() -> None:
    _reset_metrics()
    _reset_daily_costs()
    estimate = CostEstimate(estimated_usd=0.0015, estimated_sgd=0.002025, confidence="full")

    with patch("app.services.budget_service.datetime") as mock_dt:
        mock_dt.date.today.return_value = datetime.date(2026, 3, 28)
        budget_service.record_request_cost(estimate)

        mock_dt.date.today.return_value = datetime.date(2026, 3, 29)
        budget_service.record_request_cost(estimate)

    response = client.get("/v1/metrics")

    assert response.status_code == 200
    daily_costs = response.json()["daily_costs"]
    assert "2026-03-28" in daily_costs
    assert "2026-03-29" in daily_costs
    assert daily_costs["2026-03-28"]["request_count"] == 1
    assert daily_costs["2026-03-29"]["request_count"] == 1
