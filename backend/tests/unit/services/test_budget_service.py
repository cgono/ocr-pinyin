import datetime
from unittest.mock import patch

import pytest

from app.schemas.diagnostics import CostEstimate
from app.services import budget_service
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


def _reset_daily_costs() -> None:
    budget_service.daily_cost_store.__dict__.update(
        budget_service.DailyCostStore().__dict__
    )


@pytest.fixture(autouse=True)
def _clean_daily_cost_store() -> None:
    _reset_daily_costs()


def _record_today_spend_sgd(sgd: float) -> None:
    _reset_daily_costs()
    estimated_usd = round(sgd / budget_service._USD_TO_SGD, 8)
    budget_service.record_request_cost(
        CostEstimate(estimated_usd=estimated_usd, estimated_sgd=sgd, confidence="full")
    )


def test_check_budget_threshold_returns_ok_when_no_spend_recorded() -> None:
    _reset_daily_costs()

    assert budget_service.check_budget_threshold() == "ok"


def test_check_budget_threshold_returns_warn_when_today_reaches_80_percent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DAILY_BUDGET_SGD", "1.0")
    _record_today_spend_sgd(0.8)

    assert budget_service.check_budget_threshold() == "warn"


def test_check_budget_threshold_returns_exceeded_when_today_reaches_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DAILY_BUDGET_SGD", "1.0")
    _record_today_spend_sgd(1.0)

    assert budget_service.check_budget_threshold() == "exceeded"


def test_check_budget_threshold_uses_daily_budget_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DAILY_BUDGET_SGD", "2.0")
    _record_today_spend_sgd(1.7)

    assert budget_service.check_budget_threshold() == "warn"


def test_check_budget_threshold_defaults_to_one_sgd_when_env_var_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DAILY_BUDGET_SGD", raising=False)
    _record_today_spend_sgd(1.0)

    assert budget_service.check_budget_threshold() == "exceeded"


def test_check_budget_threshold_defaults_to_one_sgd_when_env_var_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DAILY_BUDGET_SGD", "not-a-number")
    _record_today_spend_sgd(1.0)

    assert budget_service.check_budget_threshold() == "exceeded"


def test_get_budget_enforce_mode_returns_block_when_env_var_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BUDGET_ENFORCE_MODE", "block")

    assert budget_service.get_budget_enforce_mode() == "block"


def test_get_budget_enforce_mode_defaults_to_warn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BUDGET_ENFORCE_MODE", raising=False)

    assert budget_service.get_budget_enforce_mode() == "warn"


def test_get_budget_enforce_mode_returns_warn_for_unknown_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BUDGET_ENFORCE_MODE", "surprise")

    assert budget_service.get_budget_enforce_mode() == "warn"


def test_check_budget_threshold_returns_ok_when_cost_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OCR_PROVIDER", raising=False)
    budget_service.record_request_cost(budget_service.estimate_request_cost(file_size_bytes=50_000))

    assert budget_service.check_budget_threshold() == "ok"


def test_check_budget_threshold_defaults_to_one_sgd_when_env_var_is_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DAILY_BUDGET_SGD", "0")
    _record_today_spend_sgd(0.5)

    assert budget_service.check_budget_threshold() == "ok"


def test_check_budget_threshold_defaults_to_one_sgd_when_env_var_is_negative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DAILY_BUDGET_SGD", "-1.0")
    _record_today_spend_sgd(0.5)

    assert budget_service.check_budget_threshold() == "ok"


def test_check_budget_threshold_defaults_to_one_sgd_when_env_var_is_nan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DAILY_BUDGET_SGD", "nan")
    _record_today_spend_sgd(1.0)

    assert budget_service.check_budget_threshold() == "exceeded"


def test_check_budget_threshold_defaults_to_one_sgd_when_env_var_is_inf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DAILY_BUDGET_SGD", "inf")
    _record_today_spend_sgd(1.0)

    assert budget_service.check_budget_threshold() == "exceeded"
