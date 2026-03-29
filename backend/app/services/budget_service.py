import datetime
import math
import os
from typing import Literal

from app.schemas.diagnostics import CostEstimate

_GCV_USD_PER_IMAGE = 0.0015
_USD_TO_SGD = 1.35
_BUDGET_WARN_FRACTION = 0.8


def estimate_request_cost(*, file_size_bytes: int) -> CostEstimate:  # noqa: ARG001
    """Estimate the processing cost for a single request.

    Provider is determined from the OCR_PROVIDER environment variable.
    file_size_bytes is accepted for future per-size cost models; not used by GCV.
    """
    provider = os.environ.get("OCR_PROVIDER", "").strip().lower()

    if provider == "google_vision":
        estimated_sgd = round(_GCV_USD_PER_IMAGE * _USD_TO_SGD, 6)
        return CostEstimate(
            estimated_usd=_GCV_USD_PER_IMAGE,
            estimated_sgd=estimated_sgd,
            confidence="full",
        )

    return CostEstimate(confidence="unavailable")


class DailyCostStore:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, float | int]] = {}

    def record(self, cost_estimate: CostEstimate) -> None:
        if cost_estimate.confidence != "full":
            return

        today = datetime.date.today().isoformat()
        entry = self._data.setdefault(
            today,
            {"total_usd": 0.0, "total_sgd": 0.0, "request_count": 0},
        )
        entry["total_usd"] += cost_estimate.estimated_usd
        entry["total_sgd"] += cost_estimate.estimated_sgd
        entry["request_count"] += 1

    def snapshot(self) -> dict[str, dict[str, float | int]]:
        return {date: dict(entry) for date, entry in self._data.items()}


daily_cost_store = DailyCostStore()


def record_request_cost(cost_estimate: CostEstimate) -> None:
    """Record the cost of a request that is about to attempt OCR (GCV will be billed)."""
    daily_cost_store.record(cost_estimate)


def check_budget_threshold() -> Literal["ok", "warn", "exceeded"]:
    """Check today's spend against the configured daily budget."""
    try:
        budget_sgd = float(os.environ.get("DAILY_BUDGET_SGD", "1.0"))
    except ValueError:
        budget_sgd = 1.0
    if not math.isfinite(budget_sgd) or budget_sgd <= 0:
        budget_sgd = 1.0

    today = datetime.date.today().isoformat()
    snapshot = daily_cost_store.snapshot()
    today_sgd = float(snapshot.get(today, {}).get("total_sgd", 0.0))

    if today_sgd >= budget_sgd:
        return "exceeded"
    if today_sgd >= budget_sgd * _BUDGET_WARN_FRACTION:
        return "warn"
    return "ok"


def get_budget_enforce_mode() -> Literal["warn", "block"]:
    """Read the budget enforcement mode from the environment."""
    mode = os.environ.get("BUDGET_ENFORCE_MODE", "warn").strip().lower()
    return "block" if mode == "block" else "warn"
