# Story 3.3: Add Health and Metrics Endpoints

Status: done

## Story

As Clint,
I want operational endpoints for service health and metrics,
So that I can monitor runtime behavior and troubleshoot quickly.

## Acceptance Criteria

1. **Given** backend is running, **When** GET /v1/health is called, **Then** it returns structured service status suitable for uptime checks **And** failure states are represented clearly.

2. **Given** GET /v1/metrics is called, **When** operational counters/timings are requested, **Then** structured metrics are returned for local monitoring use **And** response format stays consistent with versioned API conventions.

## Tasks / Subtasks

- [x] Create `backend/app/core/metrics.py` — in-memory metrics store (AC: 2)
  - [x] Define `MetricsStore` class with counters: `process_requests_total`, `process_requests_success`, `process_requests_partial`, `process_requests_error`
  - [x] Implement `increment(outcome: Literal["success", "partial", "error"]) -> None` — increments `process_requests_total` plus the matching outcome counter
  - [x] Implement `snapshot() -> dict[str, int]` — returns dict of all current counter values
  - [x] Export a module-level singleton: `metrics_store = MetricsStore()`

- [x] Create `backend/app/schemas/health.py` — health and metrics response schemas (AC: 1, 2)
  - [x] Define `HealthResponse(BaseModel)`: `status: Literal["healthy", "degraded"]`
  - [x] Define `MetricsResponse(BaseModel)`: `process_requests_total: int`, `process_requests_success: int`, `process_requests_partial: int`, `process_requests_error: int`

- [x] Create `backend/app/api/v1/health.py` — health router (AC: 1)
  - [x] Define `router = APIRouter()`
  - [x] Implement `GET /health` → `HealthResponse`: returns `HealthResponse(status="healthy")` (MVP: no external deps to check; always returns healthy when reachable)
  - [x] Route decorator: `@router.get("/health", response_model=HealthResponse)`

- [x] Create `backend/app/api/v1/metrics.py` — metrics router (AC: 2)
  - [x] Define `router = APIRouter()`
  - [x] Implement `GET /metrics` → `MetricsResponse`: reads snapshot from `metrics_store` and returns `MetricsResponse(**metrics_store.snapshot())`
  - [x] Route decorator: `@router.get("/metrics", response_model=MetricsResponse)`
  - [x] Import `metrics_store` from `app.core.metrics`

- [x] Update `backend/app/api/v1/process.py` — increment metrics after each response (AC: 2)
  - [x] Import `metrics_store` from `app.core.metrics`
  - [x] In `_build_process_response`: call `metrics_store.increment(outcome)` once per response, just before each `return ProcessResponse(...)` — use `"success"`, `"partial"`, or `"error"` as the outcome string
  - [x] Error paths (validation error, OcrServiceError early returns) also call `metrics_store.increment("error")`

- [x] Update `backend/app/api/v1/router.py` — register new routers (AC: 1, 2)
  - [x] Import `health_router` from `app.api.v1.health`
  - [x] Import `metrics_router` from `app.api.v1.metrics`
  - [x] Add `api_v1_router.include_router(health_router)` and `api_v1_router.include_router(metrics_router)`

- [x] Write integration tests in `backend/tests/integration/api_v1/test_health_route.py` (AC: 1)
  - [x] `test_health_returns_healthy`: GET /v1/health → 200, `{ "status": "healthy" }`
  - [x] `test_health_response_structure`: verify response has `status` field; value is one of `["healthy", "degraded"]`
  - [x] Use `TestClient(app)` from `starlette.testclient`

- [x] Write integration tests in `backend/tests/integration/api_v1/test_metrics_route.py` (AC: 2)
  - [x] `test_metrics_returns_200`: GET /v1/metrics → 200 with JSON
  - [x] `test_metrics_response_has_required_fields`: response includes `process_requests_total`, `process_requests_success`, `process_requests_partial`, `process_requests_error`
  - [x] `test_metrics_initial_counts_are_zero`: on a fresh metrics store, all counts are 0 (reset store in test setup)
  - [x] `test_metrics_increments_after_process_request`: post a request to `/v1/process` (with stub providers), then GET /v1/metrics and verify `process_requests_total` > 0
  - [x] Use `TestClient(app)` — reset `metrics_store` counters in setup/teardown to avoid cross-test contamination
  - [x] Import `metrics_store` from `app.core.metrics` to reset between tests

- [x] Verify all backend tests pass and `ruff check .` is clean

## Dev Notes

### Story Foundation

- **Epic goal**: Epic 3 builds the diagnostics/observability layer. Stories 3-1 and 3-2 established the diagnostics payload schema and frontend panel. Story 3-3 adds the two operational endpoints (health + metrics) that allow uptime monitoring and basic operational visibility.
- **FRs covered**: FR27 (health endpoint), FR28 (metrics endpoint)
- **No frontend changes** — this story is backend only. These endpoints are accessed directly or by monitoring tools.
- **Dependencies**: Epic 1 (process route), Stories 3-1/3-2 (no blocking dependency, but 3-3 builds on the established patterns). Metrics counters are seeded by the process endpoint.

### Current State — What Exists

**`backend/app/api/v1/router.py`** — currently only includes `process_router`:
```python
from fastapi import APIRouter
from app.api.v1.process import router as process_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(process_router)
```

**`backend/app/core/`** — directory exists but is empty. This story introduces the first file in `core/`.

**`backend/app/schemas/`** — currently contains only `common.py`, `process.py`, `diagnostics.py`.

**`backend/app/api/v1/`** — currently contains only `__init__.py`, `process.py`, `router.py`.

**`backend/app/services/`** — `diagnostics_service.py`, `image_validation.py`, `ocr_service.py`, `pinyin_service.py`. No metrics service needed — store lives in `core/`.

**Current test baseline**: 96 backend tests passing (post-3-1 code review). Story 3-2 was frontend only — backend count unchanged.

### New File: `backend/app/core/metrics.py`

```python
from typing import Literal


class MetricsStore:
    def __init__(self) -> None:
        self.process_requests_total: int = 0
        self.process_requests_success: int = 0
        self.process_requests_partial: int = 0
        self.process_requests_error: int = 0

    def increment(self, outcome: Literal["success", "partial", "error"]) -> None:
        self.process_requests_total += 1
        if outcome == "success":
            self.process_requests_success += 1
        elif outcome == "partial":
            self.process_requests_partial += 1
        else:
            self.process_requests_error += 1

    def snapshot(self) -> dict[str, int]:
        return {
            "process_requests_total": self.process_requests_total,
            "process_requests_success": self.process_requests_success,
            "process_requests_partial": self.process_requests_partial,
            "process_requests_error": self.process_requests_error,
        }


metrics_store = MetricsStore()
```

Key points:
- Module-level singleton `metrics_store` — imported by `process.py` and `metrics.py`
- Process-scoped (in-memory, resets on restart) — appropriate for MVP
- `increment()` accepts `Literal["success", "partial", "error"]` matching the process response status values
- `snapshot()` returns a plain dict — `MetricsResponse(**metrics_store.snapshot())` works directly
- No thread-safety needed for MVP (FastAPI with Uvicorn uses a single worker by default; GIL protects simple integer increments anyway)
- Reset for tests: `metrics_store.process_requests_total = 0` etc., or re-assign `metrics_store.__dict__.update(MetricsStore().__dict__)`

### New File: `backend/app/schemas/health.py`

```python
from typing import Literal
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]


class MetricsResponse(BaseModel):
    process_requests_total: int
    process_requests_success: int
    process_requests_partial: int
    process_requests_error: int
```

Both co-located in `health.py` since they are both operational schemas. `MetricsResponse` could also live in `metrics.py` but co-locating avoids proliferating small schema files. No `extra="forbid"` needed — these are response-only schemas, not API input roots.

### New File: `backend/app/api/v1/health.py`

```python
from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy")
```

MVP always returns `"healthy"` — the endpoint existing and returning 200 is the primary value for uptime monitors. If future stories add external dependencies (DB, Sentry), degraded detection can be added then. No `Request` argument needed for this simple GET.

### New File: `backend/app/api/v1/metrics.py`

```python
from fastapi import APIRouter

from app.core.metrics import metrics_store
from app.schemas.health import MetricsResponse

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    return MetricsResponse(**metrics_store.snapshot())
```

### Updated `backend/app/api/v1/router.py`

```python
from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.process import router as process_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(process_router)
api_v1_router.include_router(health_router)
api_v1_router.include_router(metrics_router)
```

### Updated `backend/app/api/v1/process.py` — metrics increment

Add `from app.core.metrics import metrics_store` to imports.

In `_build_process_response`, call `metrics_store.increment(status)` just before each return. The process response `status` field uses the same `"success"`, `"partial"`, `"error"` literals as the `MetricsStore.increment()` parameter. Example:

```python
# Early error path (no image bytes or validation error):
metrics_store.increment("error")
return ProcessResponse(status="error", ...)

# OcrServiceError early return:
metrics_store.increment("error")
return ProcessResponse(status="error", ...)

# Partial (pinyin failure):
metrics_store.increment("partial")
return ProcessResponse(status="partial", ...)

# Partial (low confidence):
metrics_store.increment("partial")
return ProcessResponse(status="partial", ...)

# Success:
metrics_store.increment("success")
return ProcessResponse(status="success", ...)
```

Count all returned `ProcessResponse` objects — do NOT skip the early validation-error return at the top of the handler (in `process_image` itself before calling `_build_process_response`). Check `process_image` for any early returns before `_build_process_response` is called and increment there too if needed.

### Test File: `backend/tests/integration/api_v1/test_health_route.py`

```python
from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200() -> None:
    response = client.get("/v1/health")
    assert response.status_code == 200


def test_health_returns_healthy_status() -> None:
    response = client.get("/v1/health")
    assert response.json()["status"] == "healthy"


def test_health_response_structure() -> None:
    response = client.get("/v1/health")
    body = response.json()
    assert "status" in body
    assert body["status"] in ("healthy", "degraded")
```

### Test File: `backend/tests/integration/api_v1/test_metrics_route.py`

```python
from unittest.mock import patch

from starlette.testclient import TestClient

from app.core.metrics import metrics_store
from app.main import app

client = TestClient(app)


def _reset_metrics() -> None:
    metrics_store.process_requests_total = 0
    metrics_store.process_requests_success = 0
    metrics_store.process_requests_partial = 0
    metrics_store.process_requests_error = 0


def test_metrics_returns_200() -> None:
    response = client.get("/v1/metrics")
    assert response.status_code == 200


def test_metrics_response_has_required_fields() -> None:
    response = client.get("/v1/metrics")
    body = response.json()
    assert "process_requests_total" in body
    assert "process_requests_success" in body
    assert "process_requests_partial" in body
    assert "process_requests_error" in body


def test_metrics_initial_counts_are_zero() -> None:
    _reset_metrics()
    response = client.get("/v1/metrics")
    body = response.json()
    assert body["process_requests_total"] == 0
    assert body["process_requests_success"] == 0
    assert body["process_requests_partial"] == 0
    assert body["process_requests_error"] == 0


def test_metrics_increments_after_process_request() -> None:
    from helpers import PNG_1X1_BYTES
    from app.adapters.ocr_provider import RawOcrSegment
    from app.adapters.pinyin_provider import RawPinyinSegment

    class StubOcrProvider:
        def extract(self, *, image_bytes: bytes, content_type: str) -> list[RawOcrSegment]:
            _ = (image_bytes, content_type)
            return [RawOcrSegment(text="你好", language="zh", confidence=0.95)]

    class StubPinyinProvider:
        def generate(self, *, text: str) -> list[RawPinyinSegment]:
            _ = text
            return [RawPinyinSegment(hanzi="你好", pinyin="nǐhǎo")]

    _reset_metrics()
    with patch("app.services.ocr_service.get_ocr_provider", return_value=StubOcrProvider()), \
         patch("app.services.pinyin_service.get_pinyin_provider", return_value=StubPinyinProvider()):
        client.post("/v1/process", content=PNG_1X1_BYTES, headers={"content-type": "image/png"})

    response = client.get("/v1/metrics")
    body = response.json()
    assert body["process_requests_total"] >= 1
```

**Note on TestClient vs asyncio.run():** The existing process tests call `process_image()` directly via `asyncio.run()` using a manually constructed `Request`. For GET endpoints with no body, `TestClient` is cleaner and equally valid — it exercises the full ASGI stack including middleware and router dispatch, which is valuable for verifying routing is correct.

**Note on cross-test isolation:** The `_reset_metrics()` helper is called explicitly in tests that check counts. Tests that only check response structure/fields don't need reset since the presence of fields doesn't depend on count values.

### Architecture Compliance

- **`/v1` prefix**: both new routes sit under `api_v1_router` which has `prefix="/v1"` — resulting in `GET /v1/health` and `GET /v1/metrics` as required.
- **snake_case fields**: `process_requests_total`, `process_requests_success`, etc. follow the API conventions.
- **Pydantic response models**: `HealthResponse` and `MetricsResponse` use `response_model=` decorator — consistent with `ProcessResponse` pattern on the process route.
- **No new external dependencies**: `MetricsStore` is pure Python, no new packages.
- **`backend/app/core/` directory**: already exists (created during project scaffold), was empty — this story introduces the first module there.
- **Test approach**: `TestClient(app)` exercises the full ASGI stack via `httpx` (which is already in dev dependencies at `0.28.1`). This is consistent with Starlette/FastAPI best practices for GET endpoint testing.

### File Structure Requirements

**New files:**
- `backend/app/core/metrics.py`
- `backend/app/schemas/health.py`
- `backend/app/api/v1/health.py`
- `backend/app/api/v1/metrics.py`
- `backend/tests/integration/api_v1/test_health_route.py`
- `backend/tests/integration/api_v1/test_metrics_route.py`

**Modified files:**
- `backend/app/api/v1/router.py` — add health and metrics router includes
- `backend/app/api/v1/process.py` — import `metrics_store`, add `metrics_store.increment(...)` before each `return ProcessResponse`

**Files NOT to touch:**
- `frontend/` — no frontend changes
- `backend/app/schemas/process.py` — no changes
- `backend/app/schemas/diagnostics.py` — no changes
- `backend/app/services/` — no changes to existing services
- `backend/app/middleware/` — no changes
- `backend/app/main.py` — no changes needed (routers are registered via `api_v1_router` which is already included)

### Previous Story Intelligence (3-2 → 3-3)

- **96 backend tests passing** after Story 3-1 code review. Story 3-2 was frontend-only — backend count still 96.
- **36 frontend tests passing** after Story 3-2.
- **`process.py` structure**: `_build_process_response` is the central function — contains all success/partial/error return points. Metrics increment calls go inside this function (and any early-return path in `process_image` before the call to `_build_process_response`).
- **`request.state.request_id`**: set by `RequestIdMiddleware` and read in `process_image` — no changes to middleware needed.
- **`response_model_exclude_none=True`** on process route — irrelevant to health/metrics (those responses have no optional fields).
- **`backend/app/core/` exists but is empty** — confirmed from Story 3-1 notes. First use of this directory.
- **Existing tests use `asyncio.run()` with direct handler calls** — health/metrics tests can use `TestClient` instead, which is simpler for GET endpoints and exercises routing.

### Git Intelligence

- `3427a01` (current): Story 3-2 — collapsible diagnostics panel (frontend only).
- `513c009`: Story 3-1 — diagnostics payload and request correlation middleware. Established `RequestIdMiddleware`, `DiagnosticsPayload` schema, `diagnostics_service`, wired into process endpoint. This established the patterns for router, schema, and service files.
- `674f74a`: Course correction — Render + Sentry selected as deployment/monitoring platform (health/metrics endpoints remain unchanged in principle per the sprint-change-proposal-2026-03-26.md).
- **Key pattern**: new routers follow the `app.api.v1.*` module structure; schemas go in `app.schemas.*`; core utilities go in `app.core.*`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-3.3 — acceptance criteria, FR27, FR28]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project-Directory-Structure — health.py, metrics.py, core/ paths]
- [Source: _bmad-output/planning-artifacts/architecture.md#API-Boundaries — /v1 prefix, health and metrics as operational boundaries]
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming-Conventions — snake_case fields, APIRouter pattern]
- [Source: backend/app/api/v1/router.py — current router structure, include_router pattern]
- [Source: backend/app/api/v1/process.py — _build_process_response structure, all return points]
- [Source: backend/app/core/ — exists but empty, ready for metrics.py]
- [Source: backend/pyproject.toml — httpx==0.28.1 available for TestClient; pytest==8.4.2 test framework]
- [Source: backend/tests/helpers.py — PNG_1X1_BYTES, StubOcrProvider patterns reusable in metrics integration test]
- [Source: _bmad-output/implementation-artifacts/3-1-capture-request-metadata-and-structured-diagnostics-payload.md — 96 test baseline, process.py wiring patterns]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-26.md — health/metrics endpoints remain unchanged by Render/Sentry platform correction]

## Dev Agent Record

### Agent Model Used

gpt-5-codex

### Debug Log References

- Red phase: `./.venv/bin/python -m pytest tests/integration/api_v1/test_health_route.py tests/integration/api_v1/test_metrics_route.py` failed during collection with `ModuleNotFoundError: No module named 'app.core.metrics'`
- Green phase: `./.venv/bin/python -m pytest tests/unit/core/test_metrics.py tests/integration/api_v1/test_health_route.py tests/integration/api_v1/test_metrics_route.py` passed (`8 passed`)
- Regression: `./.venv/bin/python -m pytest` passed (`104 passed`)
- Lint: `./.venv/bin/ruff check .` passed after fixing import ordering in `backend/tests/integration/api_v1/test_metrics_route.py`

### Completion Notes List

- Added in-memory `MetricsStore` singleton and response schemas for `/v1/health` and `/v1/metrics`.
- Registered new versioned API routers and wired metrics counting into all `ProcessResponse` outcomes, including validation errors before `_build_process_response`.
- Added integration coverage for health and metrics endpoints plus unit coverage for metrics store behavior.

### File List

- backend/app/api/v1/health.py
- backend/app/api/v1/metrics.py
- backend/app/api/v1/process.py
- backend/app/api/v1/router.py
- backend/app/core/metrics.py
- backend/app/schemas/health.py
- backend/tests/integration/api_v1/test_health_route.py
- backend/tests/integration/api_v1/test_metrics_route.py
- backend/tests/unit/core/test_metrics.py

### Change Log

- 2026-03-26: Implemented Story 3.3 health and metrics endpoints, added metrics counting to process responses, and validated with full backend test and lint runs.
