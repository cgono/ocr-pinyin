# Story 4.5: Enforce or Warn on Daily Budget Threshold

Status: done

## Story

As Clint,
I want configurable budget-threshold warning/enforcement behavior,
so that I avoid accidental overspend beyond the daily limit.

## Acceptance Criteria

1. **Given** daily SGD spend has reached ≥80% of `DAILY_BUDGET_SGD` (default 1.0 SGD) but is below the limit, **When** a request is submitted, **Then** the response includes a `budget` warning with code `budget_approaching_daily_limit` **And** the request still processes normally.

2. **Given** daily SGD spend has reached or exceeded `DAILY_BUDGET_SGD` and `BUDGET_ENFORCE_MODE=block`, **When** a request is submitted, **Then** the response is `status="error"` with `category="budget"` and code `budget_daily_limit_exceeded` **And** no OCR call is made.

3. **Given** daily SGD spend has reached or exceeded `DAILY_BUDGET_SGD` and `BUDGET_ENFORCE_MODE=warn` (the default), **When** a request is submitted, **Then** the response includes a `budget` warning with code `budget_daily_limit_reached` **And** the request still processes normally.

4. **Given** `OCR_PROVIDER` is not `google_vision` (cost unavailable), **When** any request is submitted, **Then** budget threshold check returns "ok" and enforcement is never triggered (no cost to track).

5. **Given** `DAILY_BUDGET_SGD` env var is absent or invalid, **When** threshold is evaluated, **Then** the default 1.0 SGD is used.

6. **Given** all existing backend tests run, **When** this story's changes are applied, **Then** all existing tests continue to pass.

## Tasks / Subtasks

- [x] Add `check_budget_threshold()` and `get_budget_enforce_mode()` to `backend/app/services/budget_service.py` (AC: 1–5)
  - [x] Add `from typing import Literal` to imports
  - [x] Add module constant: `_BUDGET_WARN_FRACTION = 0.8`
  - [x] Add `check_budget_threshold() -> Literal["ok", "warn", "exceeded"]` — reads `DAILY_BUDGET_SGD` env var, compares `daily_cost_store.snapshot()` today entry's `total_sgd`
  - [x] Add `get_budget_enforce_mode() -> Literal["warn", "block"]` — reads `BUDGET_ENFORCE_MODE` env var (default `"warn"`; any unknown value → `"warn"`)

- [x] Update `backend/app/api/v1/process.py` to apply budget check in `process_image` (AC: 1–3, 6)
  - [x] In `process_image`, replace the final `return await _build_process_response(...)` with budget check + conditional warning injection (see Dev Notes for exact code)
  - [x] Block path: return `ProcessResponse(status="error", ...)` before OCR, increment metrics, set sentry tags
  - [x] Warn path: call `_build_process_response`, then inject `budget_warn` into the returned response

- [x] Write unit tests in `backend/tests/unit/services/test_budget_service.py` (AC: 1–5)
  - [x] `check_budget_threshold` returns "ok" when no spend recorded
  - [x] `check_budget_threshold` returns "warn" when today's SGD ≥ 80% of threshold
  - [x] `check_budget_threshold` returns "exceeded" when today's SGD ≥ threshold
  - [x] `check_budget_threshold` uses `DAILY_BUDGET_SGD` env var when set
  - [x] `check_budget_threshold` defaults to 1.0 SGD when env var absent
  - [x] `check_budget_threshold` defaults to 1.0 SGD when env var is invalid (non-float)
  - [x] `get_budget_enforce_mode` returns "block" when `BUDGET_ENFORCE_MODE=block`
  - [x] `get_budget_enforce_mode` returns "warn" by default (env var absent)
  - [x] `get_budget_enforce_mode` returns "warn" for unknown values
  - [x] NoOp provider: `check_budget_threshold` returns "ok" (no cost recorded, today_sgd=0.0)

- [x] Write integration tests in `backend/tests/integration/api_v1/test_process_route.py` (AC: 1–3, 6)
  - [x] Block mode + exceeded budget → 200 with `status="error"` and `category="budget"`, no OCR call made
  - [x] Warn mode + approaching budget (≥80%) → 200 with `status="partial"`, warnings include `budget_approaching_daily_limit`
  - [x] Warn mode + exceeded budget → 200 with `status="partial"`, warnings include `budget_daily_limit_reached`
  - [x] Warn mode + successful OCR result → `status="partial"` (downgraded from success) with budget warning
  - [x] No budget warning when spend is below 80% threshold

## Dev Notes

### New functions in `backend/app/services/budget_service.py`

Add after the `daily_cost_store` and `record_request_cost` definitions:

```python
from typing import Literal  # add to top-of-file imports

_BUDGET_WARN_FRACTION = 0.8  # warn when this fraction of daily budget consumed


def check_budget_threshold() -> Literal["ok", "warn", "exceeded"]:
    """Check today's SGD spend against the configured daily budget.

    Reads DAILY_BUDGET_SGD env var (default: 1.0 SGD).
    Returns "ok", "warn" (≥80% consumed), or "exceeded" (≥100%).
    If no confidence="full" estimates exist today, returns "ok".
    """
    try:
        budget_sgd = float(os.environ.get("DAILY_BUDGET_SGD", "1.0"))
    except ValueError:
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
    """Read BUDGET_ENFORCE_MODE env var. Unknown values default to "warn"."""
    mode = os.environ.get("BUDGET_ENFORCE_MODE", "warn").strip().lower()
    return "block" if mode == "block" else "warn"
```

### Changes to `backend/app/api/v1/process.py`

**No new imports needed.** `budget_service`, `ProcessWarning`, `ProcessError`, `ProcessResponse`, `metrics_store`, and `_set_sentry_tag` are all already imported/defined.

In `process_image`, find the final `return await _build_process_response(...)` call (around line 303). Replace it with:

```python
    # Budget check — runs before OCR to skip expensive processing when blocking.
    budget_threshold = budget_service.check_budget_threshold()
    enforce_mode = budget_service.get_budget_enforce_mode()

    if budget_threshold == "exceeded" and enforce_mode == "block":
        _set_sentry_tag("outcome", "error")
        _set_sentry_tag("error_category", "budget")
        metrics_store.increment("error")
        return ProcessResponse(
            status="error",
            request_id=request_id,
            error=ProcessError(
                category="budget",
                code="budget_daily_limit_exceeded",
                message="Daily processing budget has been reached. Please try again tomorrow.",
            ),
        )

    budget_warn: ProcessWarning | None = None
    if budget_threshold in ("warn", "exceeded"):
        budget_warn = ProcessWarning(
            category="budget",
            code=(
                "budget_daily_limit_reached"
                if budget_threshold == "exceeded"
                else "budget_approaching_daily_limit"
            ),
            message=(
                "Daily processing budget has been reached. Results may be limited soon."
                if budget_threshold == "exceeded"
                else "Daily processing budget is nearly reached."
            ),
        )

    response = await _build_process_response(
        file_bytes,
        content_type,
        request_id=request_id,
        start_time=start_time,
    )

    # Inject budget warning into non-error responses.
    if budget_warn is not None and response.status != "error":
        if response.status == "success":
            # Downgrade to partial — success responses cannot carry warnings per schema.
            return ProcessResponse(
                status="partial",
                request_id=response.request_id,
                data=response.data,
                warnings=[budget_warn],
                diagnostics=response.diagnostics,
            )
        # Already partial: append budget warning to existing list.
        return ProcessResponse(
            status="partial",
            request_id=response.request_id,
            data=response.data,
            warnings=(response.warnings or []) + [budget_warn],
            diagnostics=response.diagnostics,
        )

    return response
```

**Why in `process_image` (not `_build_process_response`):** Keeps all budget gating logic in one place without touching the inner processing function. Zero changes to `_build_process_response` means zero regression risk there.

**Why budget warning converts success → partial:** `ProcessResponse` schema validator explicitly rejects `status="success"` with `warnings`. A `"partial"` status with data+warnings+diagnostics is the correct envelope for "processed successfully but with caveats".

**Metrics note:** When budget warning converts success → partial, `metrics_store` has already incremented "success" inside `_build_process_response`. For MVP, this minor counter inaccuracy is acceptable — the response envelope correctly shows "partial".

### Integration test helpers

To set today's SGD spend to a specific value before testing, use:

```python
from app.schemas.diagnostics import CostEstimate
from app.services import budget_service

def _reset_daily_costs() -> None:
    budget_service.daily_cost_store.__dict__.update(
        budget_service.DailyCostStore().__dict__
    )

def _set_today_spend_sgd(sgd: float) -> None:
    """Pre-seed today's spend to trigger threshold checks."""
    _reset_daily_costs()
    # 1 SGD = _USD_TO_SGD conversion; invert to get USD from SGD
    _USD_TO_SGD = 1.35
    estimated_usd = round(sgd / _USD_TO_SGD, 8)
    budget_service.record_request_cost(
        CostEstimate(estimated_usd=estimated_usd, estimated_sgd=sgd, confidence="full")
    )
```

For block-mode tests, set `BUDGET_ENFORCE_MODE=block` via `monkeypatch.setenv` and `OCR_PROVIDER=google_vision`. The OCR mock should NOT be called when blocking — assert it is NOT called (e.g., `patch("app.services.ocr_service.get_ocr_provider")` and verify its `extract` was never invoked, or just assert the response has `category="budget"` without needing to mock OCR at all, since the route returns before OCR).

For warn-mode integration tests, also stub OCR + pinyin providers so the main processing path succeeds, then check the response has budget warning in `warnings`.

### Architecture Compliance

- **`budget_service.py` location:** Extending `backend/app/services/budget_service.py` — correct per architecture file tree
- **Env var naming:** `DAILY_BUDGET_SGD` and `BUDGET_ENFORCE_MODE` — consistent with the existing `OCR_PROVIDER` naming convention (SCREAMING_SNAKE_CASE)
- **No new dependencies** — stdlib only (`os`, `datetime`), `Literal` from `typing`
- **`"budget"` error category** is already defined in `ErrorCategory` in `schemas/process.py` — reserved explicitly for this story
- **Response envelope shapes preserved** — `ProcessResponse` validator constraints respected; partial response used for warnings

### GCV Pricing / Budget Math

- Per-request cost: `$0.002025 SGD` (1.35 × $0.0015 USD)
- Default daily budget: `1.0 SGD`
- Warn threshold (80%): `0.80 SGD` ≈ 395 requests
- Hard limit (100%): `1.00 SGD` ≈ 494 requests
- With `BUDGET_ENFORCE_MODE=block`, request #495+ gets blocked before OCR

### Critical Files to Touch

| File | Action | Reason |
|------|--------|--------|
| `backend/app/services/budget_service.py` | Modify | Add `check_budget_threshold()`, `get_budget_enforce_mode()`, `_BUDGET_WARN_FRACTION` |
| `backend/app/api/v1/process.py` | Modify | Replace final `return await _build_process_response(...)` with budget check + warning injection |
| `backend/tests/unit/services/test_budget_service.py` | Modify | Add threshold and enforce mode tests |
| `backend/tests/integration/api_v1/test_process_route.py` | Modify | Add budget block/warn integration tests |

**Files NOT to touch:**
- `backend/app/schemas/process.py` — `ErrorCategory` already includes `"budget"`; `ProcessWarning` and `ProcessError` already defined correctly
- `backend/app/schemas/health.py` — no changes needed
- `backend/app/api/v1/metrics.py` — no changes needed
- All frontend files — this is a backend-only story

### Learnings from Story 4-4

- `budget_service.py` uses `import datetime` (whole module) and calls `datetime.date.today()` — match this pattern in new functions; patching requires `patch("app.services.budget_service.datetime")`
- `os.environ.get(...).strip().lower()` is the established pattern for env var reading in this codebase (see `estimate_request_cost`)
- Ruff lint must pass: `cd backend && ./.venv/bin/python -m ruff check .`
- Run all backend tests from `backend/`: `./.venv/bin/python -m pytest`
- `process.py` uses `budget_service` as module reference (not direct import) — keep this pattern: `budget_service.check_budget_threshold()`, `budget_service.get_budget_enforce_mode()`
- `_reset_daily_costs()` helper in `test_metrics_route.py` is the pattern for resetting the singleton between tests — replicate in process route tests that need fresh budget state

### Git Intelligence

- `9c82a15` — Story 4-4: `DailyCostStore`, `daily_cost_store` singleton, `record_request_cost()` in `budget_service.py`; `daily_costs` exposed on `GET /v1/metrics`
- `3b6a8ac` — Story 4-3: `estimate_request_cost()`, `CostEstimate` schema confirmed additive
- Budget enforcement (this story) builds directly on `daily_cost_store.snapshot()` already in place — no new data model needed

### References

- Epic spec: `_bmad-output/planning-artifacts/epics.md` — Epic 4, Story 4.5
- Architecture: `_bmad-output/planning-artifacts/architecture.md` — budget_service in file tree; `"budget"` error category
- NFR6: "track per-request and daily estimated processing cost, and enforce or warn at approximately 1 SGD/day"
- Previous story: `_bmad-output/implementation-artifacts/4-4-track-daily-aggregate-usage-cost.md`
- Budget service: `backend/app/services/budget_service.py`
- Process route: `backend/app/api/v1/process.py`
- Process schemas: `backend/app/schemas/process.py` — `ProcessWarning`, `ProcessError`, `ErrorCategory`
- Existing budget tests: `backend/tests/unit/services/test_budget_service.py`
- Process integration tests: `backend/tests/integration/api_v1/test_process_route.py`

## Dev Agent Record

### Agent Model Used

Codex (GPT-5-based)

### Debug Log References

- `./.venv/bin/python -m pytest tests/unit/services/test_budget_service.py tests/integration/api_v1/test_process_route.py`
- `./.venv/bin/python -m ruff check .`
- `./.venv/bin/python -m pytest`

### Completion Notes List

- Added budget threshold helpers in `budget_service.py` for warn/exceeded evaluation and enforce-mode normalization.
- Applied pre-OCR budget gating in `process_image`, including block-mode short-circuiting and warn-mode response injection.
- Added unit coverage for budget threshold defaults, env-var handling, and unavailable-cost behavior.
- Added integration coverage for block mode, approaching-limit warnings, reached-limit warnings, success-to-partial downgrade, and below-threshold behavior.
- Verified backend lint and full backend regression suite passed.

### File List

- backend/app/services/budget_service.py
- backend/app/api/v1/process.py
- backend/tests/unit/services/test_budget_service.py
- backend/tests/integration/api_v1/test_process_route.py

### Change Log

- 2026-03-28: Story created, status set to ready-for-dev
- 2026-03-28: Implemented daily budget threshold warn/block behavior, added backend unit/integration coverage, and advanced status to review.
