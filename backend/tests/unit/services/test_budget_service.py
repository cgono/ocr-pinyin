import datetime
from unittest.mock import patch

import pytest

from app.schemas.diagnostics import CostEstimate
from app.services.budget_service import DailyCostStore, estimate_request_cost


def test_google_vision_provider_returns_full_estimate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OCR_PROVIDER", "google_vision")

    result = estimate_request_cost(file_size_bytes=50_000)

    assert result.confidence == "full"
    assert result.estimated_usd == pytest.approx(0.0015)
    assert result.estimated_sgd == pytest.approx(0.002025)


def test_unset_provider_returns_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OCR_PROVIDER", raising=False)

    result = estimate_request_cost(file_size_bytes=50_000)

    assert result.confidence == "unavailable"
    assert result.estimated_usd is None
    assert result.estimated_sgd is None


def test_textract_provider_returns_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OCR_PROVIDER", "textract")

    result = estimate_request_cost(file_size_bytes=50_000)

    assert result.confidence == "unavailable"
    assert result.estimated_usd is None
    assert result.estimated_sgd is None


def test_provider_name_with_surrounding_whitespace_is_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OCR_PROVIDER", " google_vision ")

    result = estimate_request_cost(file_size_bytes=50_000)

    assert result.confidence == "full"


def _full_estimate() -> CostEstimate:
    return CostEstimate(estimated_usd=0.0015, estimated_sgd=0.002025, confidence="full")


def test_daily_cost_store_records_full_estimate_for_today() -> None:
    store = DailyCostStore()

    store.record(_full_estimate())

    snapshot = store.snapshot()
    today = datetime.date.today().isoformat()
    assert snapshot[today]["request_count"] == 1
    assert snapshot[today]["total_usd"] == pytest.approx(0.0015)
    assert snapshot[today]["total_sgd"] == pytest.approx(0.002025)


def test_daily_cost_store_skips_unavailable_estimates() -> None:
    store = DailyCostStore()

    store.record(CostEstimate(confidence="unavailable"))

    assert store.snapshot() == {}


def test_daily_cost_store_accumulates_multiple_requests_on_same_day() -> None:
    store = DailyCostStore()
    estimate = _full_estimate()

    store.record(estimate)
    store.record(estimate)

    snapshot = store.snapshot()
    today = datetime.date.today().isoformat()
    assert snapshot[today]["request_count"] == 2
    assert snapshot[today]["total_usd"] == pytest.approx(0.003)
    assert snapshot[today]["total_sgd"] == pytest.approx(0.00405)


def test_daily_cost_store_snapshot_returns_expected_shape() -> None:
    store = DailyCostStore()

    store.record(_full_estimate())

    snapshot = store.snapshot()
    today = datetime.date.today().isoformat()
    assert snapshot == {
        today: {
            "total_usd": pytest.approx(0.0015),
            "total_sgd": pytest.approx(0.002025),
            "request_count": 1,
        }
    }


def test_daily_cost_store_day_rollover_creates_separate_entries() -> None:
    store = DailyCostStore()
    day_1 = datetime.date(2026, 3, 28)
    day_2 = datetime.date(2026, 3, 29)

    with patch("app.services.budget_service.datetime") as mock_datetime:
        mock_datetime.date.today.return_value = day_1
        store.record(_full_estimate())

        mock_datetime.date.today.return_value = day_2
        store.record(_full_estimate())

    snapshot = store.snapshot()
    assert "2026-03-28" in snapshot
    assert "2026-03-29" in snapshot
    assert snapshot["2026-03-28"]["request_count"] == 1
    assert snapshot["2026-03-29"]["request_count"] == 1
