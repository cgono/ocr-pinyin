# Story 4.3: Estimate Per-Request Processing Cost

Status: done

## Story

As Clint,
I want each processing request to include an estimated cost value,
so that I can understand spend impact per page.

**Note:** Renumbered from Story 4.1 — see sprint-change-proposal-2026-03-28.md

## Acceptance Criteria

1. **Given** a processing request completes (success or partial), **When** response is prepared, **Then** estimated request cost is calculated using configured rules **And** cost value is returned in the `diagnostics.cost_estimate` field.

2. **Given** cost cannot be fully computed (e.g., NoOp provider or unknown provider), **When** estimate fallback is used, **Then** `cost_estimate.confidence` is `"unavailable"` **And** `estimated_usd` / `estimated_sgd` are absent from the JSON response **And** processing result still returns normally.

3. **Given** the Google Cloud Vision OCR provider is active, **When** a request completes, **Then** `cost_estimate.confidence` is `"full"` **And** `estimated_usd` and `estimated_sgd` are numeric values.

4. **Given** an error response is returned (validation failure, OCR failure), **When** diagnostics are excluded per the existing schema rule, **Then** `cost_estimate` is also absent (no change to error response contract).

5. **Given** all existing backend tests run, **When** the schema change is applied, **Then** all existing tests continue to pass.

## Tasks / Subtasks

- [x] Add `CostEstimate` model and `cost_estimate` field to `backend/app/schemas/diagnostics.py` (AC: 1, 2, 3, 5)
  - [x] Add `CostEstimate(BaseModel)` with fields: `estimated_usd: float | None = None`, `estimated_sgd: float | None = None`, `confidence: Literal["full", "fallback", "unavailable"]`
  - [x] Add `cost_estimate: CostEstimate | None = None` to `DiagnosticsPayload`

- [x] Create `backend/app/services/budget_service.py` (AC: 1, 2, 3)
  - [x] Implement `estimate_request_cost(*, file_size_bytes: int) -> CostEstimate`
  - [x] Read `OCR_PROVIDER` env var to determine provider
  - [x] GCV path: return `CostEstimate(estimated_usd=0.0015, estimated_sgd=0.002025, confidence="full")`
  - [x] All other paths (NoOp, textract, unset): return `CostEstimate(confidence="unavailable")`

- [x] Update `backend/app/services/diagnostics_service.py` (AC: 1, 5)
  - [x] Add `cost_estimate: CostEstimate | None = None` parameter to `build_diagnostics`
  - [x] Pass `cost_estimate=cost_estimate` into `DiagnosticsPayload(...)` constructor

- [x] Update `backend/app/api/v1/process.py` to wire cost estimation (AC: 1, 2, 4)
  - [x] Import `budget_service` from `app.services`
  - [x] Add `cost_estimate` parameter to `_make_diagnostics` helper signature
  - [x] In `_build_process_response`, call `budget_service.estimate_request_cost(file_size_bytes=...)` once, before `_make_diagnostics`
  - [x] Pass `cost_estimate=cost_estimate` to every `_make_diagnostics` call
  - [x] Pass `cost_estimate=cost_estimate` through to `build_diagnostics` in `_make_diagnostics`

- [x] Create `backend/tests/unit/services/test_budget_service.py` (AC: 2, 3, 5)
  - [x] Test: `OCR_PROVIDER=google_vision` → `confidence="full"`, `estimated_usd=0.0015`, `estimated_sgd=0.002025`
  - [x] Test: `OCR_PROVIDER` unset → `confidence="unavailable"`, `estimated_usd` is None
  - [x] Test: `OCR_PROVIDER=textract` → `confidence="unavailable"`

- [x] Verify existing contract tests still pass without changes (AC: 5)
  - `backend/tests/unit/schemas/test_process_response_contract.py` uses `_minimal_diagnostics()` which creates `DiagnosticsPayload` without `cost_estimate` → still valid since field defaults to `None`

## Dev Notes

### New File: `backend/app/services/budget_service.py`

```python
import os
from typing import Literal

from app.schemas.diagnostics import CostEstimate

# GCV DOCUMENT_TEXT_DETECTION pricing: $1.50 USD per 1,000 images (post-free-tier)
_GCV_USD_PER_IMAGE: float = 0.0015

# Fixed exchange rate: 1 USD = 1.35 SGD (monthly rate approximation; not live FX)
_USD_TO_SGD: float = 1.35


def estimate_request_cost(*, file_size_bytes: int) -> CostEstimate:  # noqa: ARG001
    """Estimate the processing cost for a single request.

    Provider is determined from the OCR_PROVIDER environment variable.
    file_size_bytes is accepted for future per-size cost models; not used by GCV.
    """
    provider = os.environ.get("OCR_PROVIDER", "").lower()

    if provider == "google_vision":
        sgd = round(_GCV_USD_PER_IMAGE * _USD_TO_SGD, 6)
        return CostEstimate(
            estimated_usd=_GCV_USD_PER_IMAGE,
            estimated_sgd=sgd,
            confidence="full",
        )

    # NoOp, Textract, or unknown provider — cannot estimate meaningfully
    return CostEstimate(confidence="unavailable")
```

**Why `file_size_bytes` is accepted but unused:** GCV prices per image regardless of size, but the parameter is part of the contract so future per-size providers (e.g., a hypothetical pay-per-MB API) can extend without breaking callers.

**Why `# noqa: ARG001`:** Ruff would flag the unused parameter; the noqa suppresses that intentionally.

### Schema Change — `backend/app/schemas/diagnostics.py`

```python
# ADD: import Literal at the top (already present if using Python 3.12)
from typing import Literal

from pydantic import BaseModel, Field


class UploadContext(BaseModel):
    content_type: str
    file_size_bytes: int = Field(..., ge=0)


class TimingInfo(BaseModel):
    total_ms: float = Field(..., ge=0)
    ocr_ms: float = Field(..., ge=0)
    pinyin_ms: float = Field(..., ge=0)


class TraceStep(BaseModel):
    step: Literal["ocr", "pinyin", "confidence_check"]
    status: Literal["ok", "skipped", "failed"]


class TraceInfo(BaseModel):
    steps: list[TraceStep]


# NEW: add before DiagnosticsPayload
class CostEstimate(BaseModel):
    estimated_usd: float | None = None
    estimated_sgd: float | None = None
    confidence: Literal["full", "fallback", "unavailable"]


class DiagnosticsPayload(BaseModel):
    upload_context: UploadContext
    timing: TimingInfo
    trace: TraceInfo
    cost_estimate: CostEstimate | None = None  # NEW
```

**Backward compatibility:** `cost_estimate` defaults to `None`. All existing tests that construct `DiagnosticsPayload(upload_context=..., timing=..., trace=...)` continue working unchanged.

**JSON serialization with `response_model_exclude_none=True`:**
- When `confidence="full"`: `"cost_estimate": {"estimated_usd": 0.0015, "estimated_sgd": 0.002025, "confidence": "full"}`
- When `confidence="unavailable"`: `"cost_estimate": {"confidence": "unavailable"}` (None fields excluded)
- When `cost_estimate=None` (legacy callers): key absent from JSON entirely

### Updated `diagnostics_service.py`

```python
from app.schemas.diagnostics import CostEstimate, DiagnosticsPayload, TimingInfo, TraceInfo, UploadContext


def build_diagnostics(
    *,
    upload_context: UploadContext,
    timing: TimingInfo,
    trace: TraceInfo,
    cost_estimate: CostEstimate | None = None,  # NEW
) -> DiagnosticsPayload:
    return DiagnosticsPayload(
        upload_context=upload_context,
        timing=timing,
        trace=trace,
        cost_estimate=cost_estimate,  # NEW
    )
```

### Updated `_make_diagnostics` in `process.py`

The helper function needs `cost_estimate` threaded through it. Minimal change:

```python
# Before the function, add budget_service import at the top:
from app.services import budget_service

# Modified _make_diagnostics signature:
def _make_diagnostics(
    *,
    upload_context: UploadContext,
    start_time: float,
    ocr_ms: float,
    pinyin_ms: float,
    trace_steps: list[TraceStep],
    cost_estimate,  # NEW: type is CostEstimate from app.schemas.diagnostics
) -> DiagnosticsPayload:
    return build_diagnostics(
        upload_context=upload_context,
        timing=TimingInfo(
            total_ms=(time.monotonic() - start_time) * 1000,
            ocr_ms=ocr_ms,
            pinyin_ms=pinyin_ms,
        ),
        trace=TraceInfo(steps=trace_steps),
        cost_estimate=cost_estimate,  # NEW
    )
```

In `_build_process_response`, add cost estimation once after `upload_context` is created:

```python
async def _build_process_response(
    image_bytes: bytes | None,
    content_type: str,
    *,
    request_id: str,
    start_time: float,
) -> ProcessResponse:
    upload_context = UploadContext(
        content_type=content_type,
        file_size_bytes=len(image_bytes) if image_bytes else 0,
    )
    # NEW: estimate cost once per request
    cost_estimate = budget_service.estimate_request_cost(
        file_size_bytes=upload_context.file_size_bytes
    )
    trace_steps: list[TraceStep] = []
    ...
    # Pass cost_estimate to every _make_diagnostics call
    diagnostics = _make_diagnostics(
        upload_context=upload_context,
        start_time=start_time,
        ocr_ms=ocr_ms,
        pinyin_ms=pinyin_ms,
        trace_steps=trace_steps,
        cost_estimate=cost_estimate,  # NEW
    )
```

**Important:** The early return for `not image_bytes` (lines ~68–82 in process.py) returns `ProcessResponse(status="error", ...)` with NO diagnostics — cost_estimate is not referenced there. No change needed for that path.

### Test File: `backend/tests/unit/services/test_budget_service.py`

```python
import pytest

from app.services.budget_service import estimate_request_cost


def test_google_vision_provider_returns_full_estimate(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_unknown_provider_returns_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OCR_PROVIDER", "some_future_provider")
    result = estimate_request_cost(file_size_bytes=0)
    assert result.confidence == "unavailable"
```

### Import Hygiene

Add to `process.py` imports (use `from app.services import budget_service` pattern, NOT direct function import — the module reference makes it easy to mock in tests):

```python
from app.services import budget_service
from app.schemas.diagnostics import CostEstimate  # only if used as type hint
```

If `CostEstimate` is needed as a type hint in `_make_diagnostics`, add it to the `from app.schemas.diagnostics import ...` line at the top of `process.py`.

### Critical Files to Touch

| File | Action | Reason |
|------|--------|--------|
| `backend/app/schemas/diagnostics.py` | Modify | Add `CostEstimate` model; add `cost_estimate` field to `DiagnosticsPayload` |
| `backend/app/services/budget_service.py` | **Create** | New service: `estimate_request_cost()` |
| `backend/app/services/diagnostics_service.py` | Modify | Add `cost_estimate` parameter to `build_diagnostics` |
| `backend/app/api/v1/process.py` | Modify | Import `budget_service`; call `estimate_request_cost`; thread through `_make_diagnostics` |
| `backend/tests/unit/services/test_budget_service.py` | **Create** | Unit tests for cost estimation logic |

**Files NOT to touch:**
- `backend/tests/unit/schemas/test_process_response_contract.py` — existing tests use `_minimal_diagnostics()` which creates `DiagnosticsPayload` without `cost_estimate` → still valid (field defaults to `None`)
- All frontend files — this is backend-only
- `backend/app/schemas/process.py` — `DiagnosticsPayload` is already included in `ProcessResponse`; no change needed
- `backend/app/adapters/` — no change to OCR/pinyin adapters

### Architecture Compliance

- **`budget_service.py` location:** `backend/app/services/budget_service.py` — exactly as defined in the architecture directory tree
- **No new dependencies.** Uses only `os` (stdlib) and existing project schemas
- **Error taxonomy unchanged.** `budget` category is already in `ErrorCategory` in `process.py`; this story doesn't emit budget errors yet (that's Story 4-5)
- **Response envelope unchanged.** `cost_estimate` is inside `DiagnosticsPayload`, which is already inside `ProcessResponse.diagnostics`. No change to envelope shape or validator
- **`response_model_exclude_none=True` on the process route** means `estimated_usd`/`estimated_sgd` are omitted when None, and `cost_estimate` is omitted when None — matches expected JSON outputs described above

### Previous Story (4-2) Learnings

- CSS lives in `frontend/src/styles/main.css` (confirmed by both 4-1 and 4-2)
- Test files: backend unit tests go in `backend/tests/unit/services/`, not alongside source
- Use `monkeypatch` (pytest fixture) for env var testing — don't set env vars globally in test files
- Ruff lint must pass before commit: `cd backend && ./.venv/bin/python -m ruff check .`
- Run all backend tests from `backend/`: `./.venv/bin/python -m pytest`
- The `process.py` route file is long — look for existing import blocks at the top and add to them rather than creating duplicate import lines

### Git Intelligence

- `2d66bef` — Story 4-2: added `line_id` to diagnostics schemas; confirmed pattern for additive nullable fields
- `4fabddf` — Story 4-1: frontend-only; no backend changes
- `3857eaa` — Story 4-0: docs only
- No previous `budget_service.py` in the codebase — this is the first cost-related backend service

### Context: Cost Estimation Scope

This story only **estimates and reports** cost per request. It does NOT:
- Accumulate daily totals (Story 4-4)
- Enforce or warn on thresholds (Story 4-5)
- Block requests based on size/cost (Story 4-6)

The cost estimate is read-only diagnostic output. The `budget` error category (`"budget"`) in `ErrorCategory` is already defined in `process.py` for use by Stories 4-5 and 4-6.

### GCV Pricing Rationale

Google Cloud Vision `DOCUMENT_TEXT_DETECTION` is billed per "unit" (= 1 image/page):
- Tiers: 0–1,000 free/month; 1,001–5,000,000 at $1.50/1,000; 5M+ at $0.60/1,000
- For MVP personal use, we use the $1.50/1,000 = $0.0015/image rate (post-free-tier conservative estimate)
- USD→SGD: 1.35 (fixed; not live FX) → $0.002025 SGD/request
- Daily budget target ~1 SGD/day ≈ ~494 requests/day before budget concern

### References

- Story spec: `_bmad-output/planning-artifacts/epics.md` — Epic 4, Story 4.3
- Architecture: `_bmad-output/planning-artifacts/architecture.md` — budget_service in file tree and cost governance in NFR section
- Diagnostics schema: `backend/app/schemas/diagnostics.py`
- Diagnostics service: `backend/app/services/diagnostics_service.py`
- Process route: `backend/app/api/v1/process.py`
- Contract tests: `backend/tests/unit/schemas/test_process_response_contract.py`
- OCR provider: `backend/app/adapters/ocr_provider.py` — `get_ocr_provider()` reads `OCR_PROVIDER` env var

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-03-28: Loaded story, sprint status, and backend diagnostics/process route context.
- 2026-03-28: Added red-phase tests for cost estimate schema/service and process-route diagnostics coverage.
- 2026-03-28: Implemented `CostEstimate`, `budget_service.estimate_request_cost()`, and threaded `cost_estimate` through diagnostics generation.
- 2026-03-28: Validation passed with `./.venv/bin/python -m pytest` (123 passed) and `./.venv/bin/python -m ruff check app tests`.

### Completion Notes List

- Added `CostEstimate` to diagnostics schema as an additive nullable field, preserving existing response contracts when diagnostics or estimate data are absent.
- Created `backend/app/services/budget_service.py` to estimate per-request cost from `OCR_PROVIDER`, returning full fixed-rate estimates for Google Vision and unavailable estimates for other providers.
- Threaded `cost_estimate` through diagnostics construction in `process.py` for success and partial responses only, leaving error envelopes unchanged.
- Added unit coverage for budget estimation and schema/service behavior, plus integration assertions that process responses now expose unavailable cost estimates by default.
- Verified the full backend regression suite and lint pass: `pytest` (123 passed) and `ruff check app tests`.

### File List

- backend/app/schemas/diagnostics.py
- backend/app/services/diagnostics_service.py
- backend/app/services/budget_service.py
- backend/app/api/v1/process.py
- backend/tests/unit/services/test_budget_service.py
- backend/tests/unit/services/test_diagnostics_service.py
- backend/tests/unit/schemas/test_diagnostics_schema.py
- backend/tests/integration/api_v1/test_process_route.py

### Change Log

- 2026-03-28: Story created, status set to ready-for-dev
- 2026-03-28: Implemented per-request cost estimation in diagnostics, added backend tests, and moved story to review.
