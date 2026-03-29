# Story 4.4: Track Daily Aggregate Usage Cost

Status: done

## Story

As Clint,
I want daily cumulative cost tracked across requests,
so that I can monitor spend against my daily budget target.

## Acceptance Criteria

1. **Given** each processing request finishes with an estimable cost (GCV provider active), **When** cost accounting is updated, **Then** the system increments the daily aggregate for the current date window **And** daily totals are queryable via `GET /v1/metrics`.

2. **Given** date window rolls over to a new day, **When** new-day requests begin, **Then** aggregation segments to the new day correctly **And** prior-day values remain available for recent review.

3. **Given** a request returns `cost_estimate.confidence == "unavailable"` (e.g., NoOp provider), **When** cost accounting is updated, **Then** nothing is recorded for that request — daily totals are unchanged.

4. **Given** a request fails during upload validation (no bytes, no OCR call), **When** cost accounting is checked, **Then** no cost is recorded (GCV was never called).

5. **Given** `GET /v1/metrics` is called, **When** daily costs exist, **Then** the response includes a `daily_costs` field: a date-keyed object where each key is `"YYYY-MM-DD"` and each value contains `total_usd`, `total_sgd`, and `request_count`.

6. **Given** no estimable requests have occurred today, **When** `GET /v1/metrics` is called, **Then** `daily_costs` is an empty object `{}` — not null, not absent.

7. **Given** all existing backend tests run, **When** the changes are applied, **Then** all existing tests continue to pass.

## Tasks / Subtasks

- [x] Add `DailyCostEntry` schema and update `MetricsResponse` in `backend/app/schemas/health.py` (AC: 5, 6)
  - [x] Add `class DailyCostEntry(BaseModel)` with fields: `total_usd: float`, `total_sgd: float`, `request_count: int`
  - [x] Add `daily_costs: dict[str, DailyCostEntry] = Field(default_factory=dict)` to `MetricsResponse`

- [x] Add `DailyCostStore` and `record_request_cost()` to `backend/app/services/budget_service.py` (AC: 1, 2, 3)
  - [x] Add `import datetime` to imports
  - [x] Add `class DailyCostStore` with `record(cost_estimate: CostEstimate) -> None` and `snapshot() -> dict` methods
  - [x] `record()` must: skip when `confidence != "full"`; use `datetime.date.today().isoformat()` as key; accumulate `total_usd`, `total_sgd`, `request_count`
  - [x] Add module-level singleton: `daily_cost_store = DailyCostStore()`
  - [x] Add module-level function `record_request_cost(cost_estimate: CostEstimate) -> None` that delegates to `daily_cost_store.record(cost_estimate)`

- [x] Update `backend/app/api/v1/process.py` to record cost per request (AC: 1, 4)
  - [x] After the `if not image_bytes:` early-return block (i.e., just before `ocr_start = time.monotonic()`), add: `budget_service.record_request_cost(cost_estimate)`
  - [x] No other changes to `process.py` required

- [x] Update `backend/app/api/v1/metrics.py` to include daily costs (AC: 5, 6)
  - [x] Import `budget_service` from `app.services`
  - [x] Import `DailyCostEntry` from `app.schemas.health`
  - [x] Update `get_metrics()` to build `daily_costs` from `budget_service.daily_cost_store.snapshot()` and include it in `MetricsResponse`

- [x] Write unit tests in `backend/tests/unit/services/test_budget_service.py` (AC: 1, 2, 3, 7)
  - [x] Test: `record()` with `confidence="full"` increments `total_usd`, `total_sgd`, `request_count` for today
  - [x] Test: `record()` with `confidence="unavailable"` does not modify the store
  - [x] Test: two consecutive `record()` calls on same day accumulate (values add up)
  - [x] Test: `snapshot()` returns a dict with the correct date key and values
  - [x] Test: day rollover — monkeypatch `datetime.date.today` to return two different dates and confirm separate keys appear in `snapshot()`

- [x] Write/update integration test for metrics endpoint (AC: 5, 6, 7)
  - [x] Test: `GET /v1/metrics` returns `daily_costs: {}` when no costs recorded
  - [x] Test: after calling `budget_service.record_request_cost(CostEstimate(estimated_usd=0.0015, estimated_sgd=0.002025, confidence="full"))` directly, `GET /v1/metrics` includes today's date in `daily_costs` with correct values

## Dev Notes

### New `DailyCostStore` in `budget_service.py`

Add below the existing `estimate_request_cost` function:

```python
import datetime  # add to existing imports at top of file

class DailyCostStore:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, float | int]] = {}

    def record(self, cost_estimate: "CostEstimate") -> None:
        if cost_estimate.confidence != "full":
            return
        today = datetime.date.today().isoformat()  # "YYYY-MM-DD"
        if today not in self._data:
            self._data[today] = {"total_usd": 0.0, "total_sgd": 0.0, "request_count": 0}
        entry = self._data[today]
        entry["total_usd"] += cost_estimate.estimated_usd  # type: ignore[operator]
        entry["total_sgd"] += cost_estimate.estimated_sgd  # type: ignore[operator]
        entry["request_count"] += 1

    def snapshot(self) -> dict[str, dict[str, float | int]]:
        return dict(self._data)


daily_cost_store = DailyCostStore()


def record_request_cost(cost_estimate: "CostEstimate") -> None:
    """Record the cost of a completed request into the daily aggregate."""
    daily_cost_store.record(cost_estimate)
```

**Why forward-reference strings on `CostEstimate`:** `CostEstimate` is already imported at the top of `budget_service.py` — use the real type, not a string. Use `CostEstimate` directly (it's already imported). Remove the `"CostEstimate"` string quotes in the actual code.

**Why `dict[str, float | int]` internally:** Keeps the store simple. The schema layer (`DailyCostEntry`) enforces types at the API boundary.

**Thread safety:** Not an issue — FastAPI/Uvicorn runs in a single-process event loop for this MVP. No locking needed.

### Schema Change — `backend/app/schemas/health.py`

```python
from pydantic import BaseModel, Field  # add Field import
from typing import Literal


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]


class DailyCostEntry(BaseModel):
    total_usd: float
    total_sgd: float
    request_count: int


class MetricsResponse(BaseModel):
    process_requests_total: int
    process_requests_success: int
    process_requests_partial: int
    process_requests_error: int
    daily_costs: dict[str, DailyCostEntry] = Field(default_factory=dict)
```

**Backward compatibility:** `daily_costs` defaults to `{}`. Existing tests that construct `MetricsResponse` without `daily_costs` continue working. The metrics API response now includes `"daily_costs": {}` by default — this is additive and non-breaking.

### Updated `metrics.py`

```python
from fastapi import APIRouter

from app.core.metrics import metrics_store
from app.schemas.health import DailyCostEntry, MetricsResponse
from app.services import budget_service

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    counts = metrics_store.snapshot()
    daily_snapshot = budget_service.daily_cost_store.snapshot()
    daily_costs = {
        date: DailyCostEntry(**entry) for date, entry in daily_snapshot.items()
    }
    return MetricsResponse(**counts, daily_costs=daily_costs)
```

### Updated `process.py` change (minimal)

Find the block that starts with `if not image_bytes:` (around line 111). After the entire `if not image_bytes:` block (which returns early), insert one line before `ocr_start = time.monotonic()`:

```python
    # Record cost — OCR is about to be attempted (GCV will be called)
    budget_service.record_request_cost(cost_estimate)
    ocr_start = time.monotonic()
```

**Why here:** This is after the upload-validation-failure early return, meaning we only record cost when OCR will actually be attempted (GCV will be billed). Upload validation errors (no bytes) do not incur GCV cost. OCR service errors DO incur GCV cost (GCV was called but returned a failure) — those are already past this point.

**Important:** Do NOT move or duplicate the `estimate_request_cost()` call. It is already at the top of `_build_process_response`. Just add the single `record_request_cost` call.

### Test: Day Rollover

To monkeypatch `datetime.date.today` inside `budget_service`, you need to patch it at the right path:

```python
import datetime
import pytest
from unittest.mock import patch

from app.services.budget_service import DailyCostStore
from app.schemas.diagnostics import CostEstimate


def _full_estimate() -> CostEstimate:
    return CostEstimate(estimated_usd=0.0015, estimated_sgd=0.002025, confidence="full")


def test_day_rollover_creates_separate_entries() -> None:
    store = DailyCostStore()

    day1 = datetime.date(2026, 3, 28)
    day2 = datetime.date(2026, 3, 29)

    with patch("app.services.budget_service.datetime") as mock_dt:
        mock_dt.date.today.return_value = day1
        store.record(_full_estimate())

        mock_dt.date.today.return_value = day2
        store.record(_full_estimate())

    snapshot = store.snapshot()
    assert "2026-03-28" in snapshot
    assert "2026-03-29" in snapshot
    assert snapshot["2026-03-28"]["request_count"] == 1
    assert snapshot["2026-03-29"]["request_count"] == 1
```

**Note:** Patching `datetime.date.today` requires patching `app.services.budget_service.datetime`, not `datetime.date.today` directly, because `budget_service` does `import datetime` (whole module) and calls `datetime.date.today()`.

### Test: Accumulation

```python
def test_same_day_accumulates() -> None:
    store = DailyCostStore()
    est = _full_estimate()
    store.record(est)
    store.record(est)

    snapshot = store.snapshot()
    today = datetime.date.today().isoformat()
    assert snapshot[today]["request_count"] == 2
    assert snapshot[today]["total_usd"] == pytest.approx(0.003)
    assert snapshot[today]["total_sgd"] == pytest.approx(0.00405)
```

### Critical Files to Touch

| File | Action | Reason |
|------|--------|--------|
| `backend/app/schemas/health.py` | Modify | Add `DailyCostEntry`; add `daily_costs` field to `MetricsResponse` |
| `backend/app/services/budget_service.py` | Modify | Add `DailyCostStore` class, `daily_cost_store` singleton, `record_request_cost()` function |
| `backend/app/api/v1/metrics.py` | Modify | Import `budget_service`; build `daily_costs` from snapshot |
| `backend/app/api/v1/process.py` | Modify | Add `budget_service.record_request_cost(cost_estimate)` call before OCR |
| `backend/tests/unit/services/test_budget_service.py` | Modify | Add new tests for `DailyCostStore` |
| `backend/tests/integration/api_v1/test_metrics_route.py` | **Create or modify** | Integration tests for `daily_costs` in metrics response |

**Files NOT to touch:**
- `backend/app/schemas/diagnostics.py` — `CostEstimate` already correct from Story 4-3; no changes needed
- `backend/app/services/diagnostics_service.py` — no changes needed
- All frontend files — this is a backend-only story
- `backend/app/core/metrics.py` — request counters stay separate; daily cost belongs in `budget_service`

### Architecture Compliance

- **`budget_service.py` location:** Extending the existing `backend/app/services/budget_service.py` — consistent with architecture `budget_service` in the services directory tree
- **Global singleton pattern:** `daily_cost_store = DailyCostStore()` follows the established `metrics_store = MetricsStore()` pattern from `core/metrics.py`
- **No new dependencies.** Uses only `datetime` (stdlib) and existing project schemas
- **`GET /v1/metrics` is the right exposure point** for operational visibility — already used for request counters; daily cost follows same pattern
- **`response_model_exclude_none=True` is NOT set on the metrics route** — check `metrics.py` to confirm; the `daily_costs: dict = Field(default_factory=dict)` will serialize as `{}` when empty (correct behavior per AC 6)

### Learnings from Story 4-3

- `budget_service.py` uses `os.environ.get("OCR_PROVIDER", "").strip().lower()` — the `.strip()` was added post-spec; trust the file over the story notes
- Ruff lint must pass before commit: `cd backend && ./.venv/bin/python -m ruff check .`
- Run all backend tests from `backend/`: `./.venv/bin/python -m pytest`
- When extending `budget_service.py`, check the existing `estimate_request_cost` import chain in `process.py` — `from app.services import budget_service` is already there; just add new calls
- The `process.py` route imports `budget_service` as a module reference (not direct function import) — maintain this pattern for `record_request_cost` too: `budget_service.record_request_cost(cost_estimate)`, not `from app.services.budget_service import record_request_cost`
- Existing `test_budget_service.py` tests use `monkeypatch.setenv` — keep using pytest fixtures, no global env mutations
- CSS lives in `frontend/src/styles/main.css` (not relevant here — backend-only story)

### Git Intelligence

- `3b6a8ac` — Story 4-3: added `CostEstimate` schema + `budget_service.estimate_request_cost()`; confirmed additive nullable fields pattern
- `2d66bef` — Story 4-2: confirmed `line_id` nullable schema extension pattern
- No prior daily aggregation code exists — `DailyCostStore` is net new

### Context: Daily Tracking Scope

This story ONLY tracks daily aggregate cost in memory. It does NOT:
- Enforce or warn on thresholds (Story 4-5)
- Block requests based on cost (Story 4-5)
- Restrict oversized inputs (Story 4-6)
- Persist cost data across restarts (MVP in-memory only)

The `"budget"` error category in `ErrorCategory` (process.py) is already defined and reserved for Stories 4-5 and 4-6.

### GCV Pricing Reminder (for test values)

- Per-request: `$0.0015 USD` = `$0.002025 SGD` (1.35 fixed rate)
- Daily budget target: ~1 SGD/day ≈ 494 requests/day before concern

### References

- Story spec: `_bmad-output/planning-artifacts/epics.md` — Epic 4, Story 4.4
- Previous story: `_bmad-output/implementation-artifacts/4-3-estimate-per-request-processing-cost.md`
- Architecture: `_bmad-output/planning-artifacts/architecture.md` — budget_service in file tree; cost governance NFR
- Budget service: `backend/app/services/budget_service.py`
- Diagnostics schema: `backend/app/schemas/diagnostics.py` — `CostEstimate` model
- Metrics store: `backend/app/core/metrics.py` — `MetricsStore` singleton pattern to follow
- Metrics route: `backend/app/api/v1/metrics.py`
- Health/metrics schemas: `backend/app/schemas/health.py`
- Process route: `backend/app/api/v1/process.py` — where `record_request_cost` call is added
- Existing budget tests: `backend/tests/unit/services/test_budget_service.py`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- 2026-03-28: Added `DailyCostStore`, exposed `daily_costs` on `GET /v1/metrics`, and recorded cost estimates just before OCR execution.
- 2026-03-28: Verified targeted tests, full backend test suite, and Ruff lint all pass.

### Completion Notes List

- Implemented in-memory daily aggregate cost tracking keyed by `YYYY-MM-DD`, with accumulation of USD, SGD, and request counts only for `confidence="full"` estimates.
- Extended the metrics response schema and route so `GET /v1/metrics` always returns `daily_costs`, defaulting to `{}` when empty.
- Hooked request cost recording into the process flow after the no-bytes early return so upload validation failures do not record cost while OCR attempts do.
- Added unit coverage for full, unavailable, accumulation, snapshot, and day-rollover scenarios, plus integration coverage for empty and populated `daily_costs`.
- Validation completed with `./.venv/bin/python -m ruff check .` and `./.venv/bin/python -m pytest` from `backend/`.

### File List

- backend/app/schemas/health.py
- backend/app/services/budget_service.py
- backend/app/api/v1/process.py
- backend/app/api/v1/metrics.py
- backend/tests/unit/services/test_budget_service.py
- backend/tests/integration/api_v1/test_metrics_route.py

### Change Log

- 2026-03-28: Story created, status set to ready-for-dev
- 2026-03-28: Implemented daily aggregate cost tracking, exposed `daily_costs` in metrics, added backend unit/integration coverage, and moved story to review.
