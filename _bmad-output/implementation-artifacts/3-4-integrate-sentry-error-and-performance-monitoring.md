# Story 3.4: Integrate Sentry Error and Performance Monitoring

Status: done

## Story

As Clint,
I want backend and frontend failures captured in Sentry with request context and performance traces,
So that I can troubleshoot production issues quickly without adopting a heavyweight observability stack.

## Acceptance Criteria

1. **Given** processing requests execute across success/partial/error paths, **When** exceptions, typed warnings, or slow traces occur, **Then** Sentry captures the event with key fields (`request_id` tag, `outcome` tag (success/partial/error), timing via auto-instrumentation from `StarletteIntegration`/`FastApiIntegration`, `error_category` tag where applicable) **And** `release`/`environment` tags are included for triage.

2. **Given** Sentry is unavailable or disabled, **When** instrumentation is attempted, **Then** core processing flow still completes **And** monitoring failures do not break user responses.

## Tasks / Subtasks

- [x] Add `sentry-sdk[fastapi]` to `backend/pyproject.toml` (AC: 1)
  - [x] Append `"sentry-sdk[fastapi]>=2.0,<3.0"` to the `dependencies` list

- [x] Create `backend/app/core/sentry.py` — Sentry initialization helper (AC: 1, 2)
  - [x] Implement `init_sentry() -> None` — reads `SENTRY_DSN` env var; no-ops if unset/empty
  - [x] If DSN is set, call `sentry_sdk.init(...)` with `environment`, `release`, `traces_sample_rate=1.0`, `StarletteIntegration`, and `FastApiIntegration`
  - [x] Wrap the entire init block in `try/except Exception` → log warning on failure, never raise
  - [x] Set `send_default_pii=False`

- [x] Update `backend/app/main.py` — call `init_sentry()` at startup (AC: 1, 2)
  - [x] Import `init_sentry` from `app.core.sentry`
  - [x] Call `init_sentry()` after the `logging.basicConfig(...)` call and before `app = FastAPI(...)`

- [x] Update `backend/app/api/v1/process.py` — add Sentry request context (AC: 1)
  - [x] Import `sentry_sdk` (conditional: use `try/except ImportError` guard so it's truly optional)
  - [x] At the start of `process_image()`, after `request_id` is resolved: call `_set_sentry_tags(request_id)` (see helper below)
  - [x] Remove both TODO comments referencing story 3-4; replace with the Sentry tag/context calls
  - [x] In the `OcrServiceError` except block: call `sentry_sdk.set_tag("error_category", error.category)` before the return
  - [x] In `_build_validation_error_response`: call `sentry_sdk.set_tag("error_category", error.category)` before the return
  - [x] Do NOT add `sentry_sdk.capture_exception()` calls — the FastAPI+Starlette integration handles unhandled exceptions automatically; for handled errors (like OcrServiceError), set context tags only

- [x] Update `backend/.env.example` — document Sentry env vars (AC: 1)
  - [x] Add `SENTRY_DSN=` (blank — user must supply their Sentry project DSN)
  - [x] Add `APP_VERSION=0.1.0` (used as `release` tag in Sentry)
  - [x] Add `SENTRY_TRACES_SAMPLE_RATE=1.0` (tunable; default 1.0 is acceptable at personal-use scale; lower for higher traffic)
  - [x] Ensure `APP_ENV=development` is already present (it is — verify)

- [x] Write unit tests in `backend/tests/unit/core/test_sentry.py` (AC: 2)
  - [x] `test_init_sentry_no_dsn_does_not_raise`: call `init_sentry()` with `SENTRY_DSN` unset → no exception
  - [x] `test_init_sentry_empty_dsn_does_not_raise`: set `SENTRY_DSN=""` → no exception
  - [x] `test_init_sentry_calls_sentry_sdk_init_when_dsn_set`: mock `sentry_sdk.init`, set a fake DSN → verify `sentry_sdk.init` was called once with `dsn=<fake_dsn>`
  - [x] `test_init_sentry_suppresses_init_exception`: mock `sentry_sdk.init` to raise `RuntimeError` → `init_sentry()` should not raise
  - [x] Use `monkeypatch.setenv` / `monkeypatch.delenv` for env var manipulation

- [x] Add `@sentry/react` to `frontend/package.json` (AC: 1)
  - [x] Add `"@sentry/react": "^8.0.0"` to the `dependencies` section

- [x] Update `frontend/src/main.jsx` — initialize Sentry before React render (AC: 1, 2)
  - [x] Import `* as Sentry` from `@sentry/react`
  - [x] Call `initSentry()` helper before `createRoot(...)` call
  - [x] `initSentry()`: reads `import.meta.env.VITE_SENTRY_DSN`; if falsy, returns early (no-op)
  - [x] If DSN present: call `Sentry.init({ dsn, environment, release, tracesSampleRate: 1.0, integrations: [Sentry.browserTracingIntegration()] })`
  - [x] Wrap in `try/catch` — log warning to console on failure, never throw

- [x] Update `frontend/src/App.jsx` — wrap app with Sentry ErrorBoundary (AC: 1)
  - [x] Import `ErrorBoundary` from `@sentry/react`
  - [x] Wrap the returned JSX with `<Sentry.ErrorBoundary fallback={<p>Something went wrong.</p>}>`

- [x] Update `frontend/.env.example` — document Sentry env vars (AC: 1)
  - [x] Add `VITE_SENTRY_DSN=` (blank)
  - [x] Add `VITE_APP_ENV=development`
  - [x] Add `VITE_APP_VERSION=0.1.0`
  - [x] Add `VITE_SENTRY_TRACES_SAMPLE_RATE=1.0` (tunable; default 1.0; lower for production scale)

- [x] Write frontend tests in `frontend/src/__tests__/sentry.test.js` (AC: 2)
  - [x] `it renders without crashing when sentry dsn is missing`: render `<App />` with no VITE_SENTRY_DSN → no throw
  - [x] Use `vi.mock('@sentry/react', ...)` to stub Sentry so tests don't require a real DSN

- [x] Verify all backend tests pass (`cd backend && ./.venv/bin/python -m pytest`) and ruff is clean
- [x] Verify all frontend tests pass (`cd frontend && npm test`)

## Dev Notes

### Story Foundation

- **Epic goal**: Epic 3 builds observability. Stories 3-1/3-2 established diagnostics payload and UI panel; 3-3 added health/metrics endpoints. Story 3-4 integrates Sentry as the error and performance monitoring sink (selected in the 2026-03-26 sprint course correction replacing the previous Datadog placeholder).
- **FRs covered**: FR26 (telemetry emission for Sentry monitoring)
- **NFR covered**: NFR7 (emit telemetry compatible with Sentry monitoring)
- **Sprint change context**: The 2026-03-26 sprint-change-proposal confirmed Sentry + Render as the operational stack. Story 3.4 was explicitly rewritten from "generic Datadog-compatible telemetry" to "Sentry integration."

### Current State — What Exists

**`backend/app/main.py`** — sets up `logging.basicConfig`, creates `FastAPI` app, adds CORS and `RequestIdMiddleware`, includes `api_v1_router`. No Sentry init today.

**`backend/app/core/`** — contains only `metrics.py` (singleton `MetricsStore`). `sentry.py` does not exist yet.

**`backend/app/api/v1/process.py`** — contains two TODO comments explicitly calling out story 3-4:
```python
# TODO: log upload_context and request_id here once Sentry/structured logging
# is in place (story 3-4). Upload metadata captured but not yet persisted.
```
These appear in the `_build_process_response` function — in the "no image bytes" early return and in the `OcrServiceError` except block. Both should be resolved in this story.

**`backend/pyproject.toml`** — does NOT yet include `sentry-sdk`. Current dependencies: `fastapi==0.129.0`, `pydantic==2.11.9`, `uvicorn[standard]==0.37.0`, `langchain-core==0.3.81`, `pypinyin==0.55.0`, `google-cloud-vision>=3.7,<4.0`, `pillow==11.3.0`, `python-multipart==0.0.22`.

**`frontend/package.json`** — does NOT yet include `@sentry/react`. Current dependencies: `@tanstack/react-query`, `react`, `react-dom`.

**`frontend/src/main.jsx`** — creates `QueryClient`, wraps `App` in `QueryClientProvider`, renders to `#root`. No Sentry init.

**`frontend/src/App.jsx`** — renders `<UploadForm />` inside `<main>`. No error boundary.

**Backend test baseline**: 104 tests passing (as of story 3-3). Test runner: `pytest==8.4.2`. Run from `backend/` with `./.venv/bin/python -m pytest`.

**Frontend test baseline**: 36 tests passing (as of story 3-2, unchanged in 3-3). Test runner: Vitest (configured in `vite.config.js`). Run from `frontend/` with `npm test`.

### New File: `backend/app/core/sentry.py`

```python
import logging
import os

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Initialize Sentry SDK if SENTRY_DSN is configured.

    If SENTRY_DSN is unset or empty, Sentry is silently disabled.
    Initialization failures are logged as warnings and never propagate —
    monitoring must never break core request processing.
    """
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("APP_ENV", "development"),
            release=os.getenv("APP_VERSION", "0.1.0"),
            traces_sample_rate=1.0,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(),
            ],
            send_default_pii=False,
        )
        logger.info("Sentry initialized (env=%s)", os.getenv("APP_ENV", "development"))
    except Exception:
        logger.warning("Sentry initialization failed; monitoring disabled.", exc_info=True)
```

Key points:
- `traces_sample_rate` — read from `SENTRY_TRACES_SAMPLE_RATE` env var (default `1.0`); captures all transactions at default; lower for production scale (e.g., `0.1`)
- `StarletteIntegration(transaction_style="endpoint")` — groups transactions by endpoint path, not by URL parameters
- `FastApiIntegration()` — adds FastAPI-specific context (route, parameters)
- `send_default_pii=False` — never sends PII (no auth in MVP, but good hygiene)
- The `try/except ImportError` is NOT needed since sentry-sdk is in `dependencies` (always installed); `try/except Exception` is sufficient to catch DSN parse errors or network issues

### Updated `backend/app/main.py`

```python
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.sentry import init_sentry
from app.middleware.request_id import RequestIdMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)

init_sentry()  # Must be called before app = FastAPI(...)

app = FastAPI(
    title="OCR Pinyin API",
    version="0.1.0",
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Local development",
        }
    ],
)

# ... rest unchanged
```

**Why before `FastAPI()`?** The Sentry SDK must be initialized before any instrumented code instantiates, otherwise the ASGI middleware and integrations won't be wired into the app object.

### Updated `backend/app/api/v1/process.py` — Sentry context

Add import at top (after existing imports):
```python
try:
    import sentry_sdk as _sentry_sdk
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False
```

Wait — since `sentry-sdk` is in the required dependencies (not optional), use a simpler import:
```python
import sentry_sdk
```

Add a private helper function:
```python
def _set_sentry_request_context(request_id: str) -> None:
    """Set Sentry scope tags for request correlation. No-ops if Sentry is not enabled."""
    try:
        sentry_sdk.set_tag("request_id", request_id)
    except Exception:
        pass  # Never let Sentry context setting break request handling
```

In `process_image()`, after `request_id` is resolved:
```python
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    _set_sentry_request_context(request_id)  # Add this line
```

In `_build_process_response`, replace the TODO comment in the "no image bytes" block:
```python
    if not image_bytes:
        sentry_sdk.set_tag("outcome", "error")
        metrics_store.increment("error")
        return ProcessResponse(...)
```

In the `OcrServiceError` except block, replace the TODO comment:
```python
    except OcrServiceError as error:
        trace_steps.append(TraceStep(step="ocr", status="failed"))
        sentry_sdk.set_tag("outcome", "error")
        sentry_sdk.set_tag("error_category", error.category)
        metrics_store.increment("error")
        return ProcessResponse(...)
```

In `_build_validation_error_response`, add context:
```python
def _build_validation_error_response(
    request_id: str, error: ImageValidationError
) -> ProcessResponse:
    sentry_sdk.set_tag("outcome", "error")
    sentry_sdk.set_tag("error_category", error.category)
    metrics_store.increment("error")
    return ProcessResponse(...)
```

For the success path, add outcome tag before return:
```python
    trace_steps.append(TraceStep(step="confidence_check", status="ok"))
    # ...
    sentry_sdk.set_tag("outcome", "success")
    metrics_store.increment("success")
    return ProcessResponse(status="success", ...)
```

For the partial paths (PinyinServiceError, low confidence), add `sentry_sdk.set_tag("outcome", "partial")` before each `metrics_store.increment("partial")`.

**Note on `sentry_sdk.set_tag` safety**: when Sentry is not initialized (no DSN), `sentry_sdk.set_tag()` is a no-op and does not raise — this is by design in the SDK. The `try/except` in `_set_sentry_request_context` is an extra safety net, but the direct `sentry_sdk.set_tag()` calls in `_build_process_response` do NOT need wrapping since the SDK guarantees no-op behavior without init.

### Frontend: `frontend/src/main.jsx`

```jsx
import React from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import * as Sentry from '@sentry/react'

import './styles/main.css'
import App from './App'

function initSentry() {
  const dsn = import.meta.env.VITE_SENTRY_DSN
  if (!dsn) return

  try {
    Sentry.init({
      dsn,
      environment: import.meta.env.VITE_APP_ENV || 'development',
      release: import.meta.env.VITE_APP_VERSION || '0.1.0',
      tracesSampleRate: 1.0,
      integrations: [Sentry.browserTracingIntegration()],
    })
  } catch (err) {
    console.warn('Sentry initialization failed; monitoring disabled.', err)
  }
}

initSentry()

const queryClient = new QueryClient()

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
)
```

### Frontend: `frontend/src/App.jsx`

```jsx
import { ErrorBoundary } from '@sentry/react'
import UploadForm from './features/process/components/UploadForm'

function ErrorFallback() {
  return <p className="error-fallback">Something went wrong. Please reload and try again.</p>
}

export default function App() {
  return (
    <ErrorBoundary fallback={<ErrorFallback />}>
      <main className="app-shell">
        <h1 className="app-title">Process Image</h1>
        <UploadForm />
      </main>
    </ErrorBoundary>
  )
}
```

### Test File: `backend/tests/unit/core/test_sentry.py`

```python
import os
from unittest.mock import MagicMock, patch

import pytest

from app.core.sentry import init_sentry


def test_init_sentry_no_dsn_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    init_sentry()  # should complete without raising


def test_init_sentry_empty_dsn_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "")
    init_sentry()  # should complete without raising


def test_init_sentry_calls_sdk_init_when_dsn_set(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_dsn = "https://abc123@o0.ingest.sentry.io/0"
    monkeypatch.setenv("SENTRY_DSN", fake_dsn)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_VERSION", "0.0.1")

    mock_init = MagicMock()
    with patch("sentry_sdk.init", mock_init):
        init_sentry()

    mock_init.assert_called_once()
    call_kwargs = mock_init.call_args.kwargs
    assert call_kwargs["dsn"] == fake_dsn
    assert call_kwargs["environment"] == "test"
    assert call_kwargs["release"] == "0.0.1"
    assert call_kwargs["send_default_pii"] is False


def test_init_sentry_suppresses_init_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "https://fake@o0.ingest.sentry.io/0")

    with patch("sentry_sdk.init", side_effect=RuntimeError("SDK error")):
        init_sentry()  # should not raise — monitoring never breaks startup
```

### Test File: `frontend/src/__tests__/sentry.test.js`

```javascript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../../App'

// Stub @sentry/react so tests run without a real DSN and without network calls
vi.mock('@sentry/react', () => ({
  init: vi.fn(),
  ErrorBoundary: ({ children, fallback }) => {
    // Minimal stub: renders children; renders fallback on error
    return children
  },
  browserTracingIntegration: vi.fn(() => ({})),
}))

describe('Sentry integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders App without crashing when VITE_SENTRY_DSN is not set', () => {
    // VITE_SENTRY_DSN is not set in test env — init_sentry() should no-op
    expect(() => render(<App />)).not.toThrow()
  })

  it('renders the upload form within the ErrorBoundary', () => {
    render(<App />)
    // UploadForm renders a file input or upload button — verify basic render
    expect(document.querySelector('main.app-shell')).not.toBeNull()
  })
})
```

### Updated `backend/.env.example`

Add to the bottom:
```
# Sentry monitoring (optional — leave blank to disable)
SENTRY_DSN=
APP_VERSION=0.1.0
```

`APP_ENV=development` is already present. `APP_VERSION` is new.

### Updated `frontend/.env.example`

Full contents:
```
VITE_API_BASE_URL=
VITE_SENTRY_DSN=
VITE_APP_ENV=development
VITE_APP_VERSION=0.1.0
```

### Architecture Compliance

- **No new API endpoints** — this story is pure instrumentation, no new routes
- **`backend/app/core/` directory** — follows the established pattern (metrics.py already there)
- **Graceful degradation** — both backend and frontend degrade gracefully when DSN is absent, satisfying NFR4-style robustness
- **`send_default_pii=False`** — no PII in Sentry events (required for security baseline)
- **`traces_sample_rate=1.0`** — OK at personal-use MVP scale; note for future if volume grows
- **Environment variable naming**: `SENTRY_DSN`, `APP_ENV`, `APP_VERSION` (backend); `VITE_SENTRY_DSN`, `VITE_APP_ENV`, `VITE_APP_VERSION` (frontend) — `VITE_` prefix required by Vite for client-side env vars
- **Sentry SDK auto-instrumentation**: `FastApiIntegration` + `StarletteIntegration` auto-captures unhandled exceptions across all routes — no per-route `try/except` wrappers needed

### File Structure Requirements

**New files:**
- `backend/app/core/sentry.py`
- `backend/tests/unit/core/test_sentry.py`
- `frontend/src/__tests__/sentry.test.js`

**Modified files:**
- `backend/pyproject.toml` — add `sentry-sdk[fastapi]` dependency
- `backend/app/main.py` — import and call `init_sentry()`
- `backend/app/api/v1/process.py` — import `sentry_sdk`, add `_set_sentry_request_context()`, resolve TODOs with Sentry tag calls
- `backend/.env.example` — add `SENTRY_DSN`, `APP_VERSION`
- `frontend/package.json` — add `@sentry/react`
- `frontend/src/main.jsx` — import Sentry, add `initSentry()` call
- `frontend/src/App.jsx` — wrap with `ErrorBoundary`
- `frontend/.env.example` — add `VITE_SENTRY_DSN`, `VITE_APP_ENV`, `VITE_APP_VERSION`

**Files NOT to touch:**
- `backend/app/api/v1/router.py` — no changes
- `backend/app/schemas/` — no schema changes
- `backend/app/services/` — no service changes
- `backend/app/middleware/` — no middleware changes
- `backend/app/adapters/` — no adapter changes (telemetry_provider.py is a future concern)
- All existing test files — only adding new tests, not modifying existing ones
- `frontend/src/features/` — no feature component changes

### Previous Story Intelligence (3-3 → 3-4)

- **104 backend tests passing** after story 3-3. 36 frontend tests.
- **`backend/app/core/` directory** has one file: `metrics.py`. `sentry.py` will be the second.
- **process.py structure** is stable: `process_image()` → `_build_process_response()` + `_build_validation_error_response()`. All outcome paths are explicit. Sentry tags should be set at each return point in `_build_process_response` and in `_build_validation_error_response`.
- **Two TODO comments in process.py** explicitly point to story 3-4. These are in `_build_process_response`: the "no image bytes" early return and the `OcrServiceError` except block. Resolve both.
- **Frontend tests** use Vitest with jsdom environment. Tests are in `frontend/src/__tests__/`. Mocking with `vi.mock()` is standard.
- **`vite.config.js`** has `test: { environment: 'jsdom', setupFiles: './src/test/setup.js' }` — new test file in `__tests__/` will be picked up automatically.

### Git Intelligence

- `25d7d6e` (current HEAD): Story 3-3 — health and metrics endpoints. Established `backend/app/core/` with `metrics.py`, health/metrics routes, and `MetricsStore` singleton.
- `674f74a`: Course correction — confirmed Render + Sentry as platform. Story 3.4 explicitly changed from "Datadog telemetry" to "Sentry integration" per `sprint-change-proposal-2026-03-26.md`.
- **`backend/app/core/` pattern**: new core utilities go here as module-level singletons or helper functions. `sentry.py` follows the same pattern as `metrics.py`.
- **Frontend test pattern**: `vi.mock('module-name', () => ({...}))` at the top of test files for third-party dependencies. See `frontend/src/__tests__/features/process/upload-form.test.jsx` for existing mock patterns.

### Installation Notes

**Backend:**
```bash
cd backend
# After editing pyproject.toml to add sentry-sdk[fastapi]>=2.0,<3.0
./.venv/bin/pip install -e .
# Verify:
./.venv/bin/python -c "import sentry_sdk; print(sentry_sdk.VERSION)"
```

**Frontend:**
```bash
cd frontend
npm install
# Verify:
node -e "require('@sentry/react'); console.log('ok')" 2>/dev/null || npx --yes node -e "require('@sentry/react')"
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-3.4 — acceptance criteria, FR26]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-26.md — Sentry confirmed as monitoring stack]
- [Source: _bmad-output/planning-artifacts/architecture.md#Infrastructure-Deployment — Sentry as error tracking]
- [Source: backend/app/api/v1/process.py — two TODO comments pointing to story 3-4]
- [Source: backend/app/core/metrics.py — pattern for core utility module]
- [Source: backend/app/main.py — startup sequence; init_sentry() goes before FastAPI() instantiation]
- [Source: frontend/src/main.jsx — init location for Sentry (before createRoot)]
- [Source: frontend/src/App.jsx — ErrorBoundary wrapper location]
- [Source: backend/pyproject.toml — current dependencies; sentry-sdk not yet included]
- [Source: frontend/package.json — current deps; @sentry/react not yet included]
- [Source: backend/.env.example — APP_ENV=development already set; add SENTRY_DSN, APP_VERSION]
- [Source: frontend/.env.example — VITE_API_BASE_URL already set; add VITE_SENTRY_DSN, VITE_APP_ENV, VITE_APP_VERSION]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv sync` in `backend/` to install `sentry-sdk[fastapi]` and update `backend/uv.lock`
- `backend/.venv/bin/python -m pytest` → `108 passed`
- `backend/.venv/bin/ruff check .` → `All checks passed!`
- `npm install` in `frontend/` to add `@sentry/react` and update `frontend/package-lock.json`
- `npm test` in `frontend/` → `38 passed`

### Completion Notes List

- Added backend Sentry bootstrap in `backend/app/core/sentry.py` and initialized it during FastAPI startup using `SENTRY_DSN`, `APP_ENV`, and `APP_VERSION`.
- Tagged backend request flows with `request_id`, `outcome`, and `error_category` in `backend/app/api/v1/process.py` without adding explicit exception capture calls.
- Added frontend Sentry initialization in `frontend/src/main.jsx` and wrapped the app in a Sentry `ErrorBoundary` in `frontend/src/App.jsx`.
- Documented backend and frontend Sentry environment variables in the example env files.
- Added backend unit coverage for Sentry initialization safeguards and frontend coverage proving the app renders when Sentry is unset.
- Updated dependency lockfiles: `backend/uv.lock` and `frontend/package-lock.json`.

### File List

- `backend/.env.example`
- `backend/app/api/v1/process.py`
- `backend/app/core/sentry.py`
- `backend/app/main.py`
- `backend/pyproject.toml`
- `backend/tests/unit/core/test_sentry.py`
- `backend/uv.lock`
- `frontend/.env.example`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/src/App.jsx`
- `frontend/src/__tests__/sentry.test.jsx`
- `frontend/src/main.jsx`

### Change Log

- 2026-03-26: Implemented Story 3.4 Sentry backend/frontend monitoring integration, added tests, and verified backend/frontend suites before moving story to review.
