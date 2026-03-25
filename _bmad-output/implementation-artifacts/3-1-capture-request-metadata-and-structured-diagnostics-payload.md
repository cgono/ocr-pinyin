# Story 3.1: Capture Request Metadata and Structured Diagnostics Payload

Status: done

## Story

As Clint,
I want each processing request to capture metadata and diagnostics context,
So that I can troubleshoot quality issues and review runs later.

## Acceptance Criteria

1. **Given** a processing request is received, **When** request handling begins and ends, **Then** request metadata (including request correlation id and upload context) is captured **And** diagnostics payload sections are generated in a consistent structure.

2. **Given** processing succeeds, partially succeeds, or fails, **When** response is returned, **Then** diagnostics structure remains present/consistent per status policy **And** sensitive internals are not leaked in user-facing error text.

**Status policy:** Success and partial envelopes include `diagnostics`. Error envelope does not (consistent with architecture spec).

## Tasks / Subtasks

- [x] Create `backend/app/schemas/diagnostics.py` — DiagnosticsPayload and sub-schemas (AC: 1)
  - [x] Define `UploadContext(BaseModel)`: `content_type: str`, `file_size_bytes: int`
  - [x] Define `TimingInfo(BaseModel)`: `total_ms: float`, `ocr_ms: float | None = None`, `pinyin_ms: float | None = None`
  - [x] Define `TraceStep(BaseModel)`: `step: str`, `status: Literal["ok", "skipped", "failed"]`
  - [x] Define `TraceInfo(BaseModel)`: `steps: list[TraceStep]`
  - [x] Define `DiagnosticsPayload(BaseModel)`: `upload_context: UploadContext`, `timing: TimingInfo`, `trace: TraceInfo`

- [x] Create `backend/app/services/diagnostics_service.py` — build diagnostics payloads (AC: 1)
  - [x] Implement `build_diagnostics(*, upload_context: UploadContext, timing: TimingInfo, trace: TraceInfo) -> DiagnosticsPayload`

- [x] Create `backend/app/middleware/request_id.py` — request correlation middleware (AC: 1)
  - [x] Implement `RequestIdMiddleware(BaseHTTPMiddleware)`: generate `uuid4()`, attach to `request.state.request_id`, forward `X-Request-ID` response header

- [x] Register `RequestIdMiddleware` in `backend/app/main.py` (AC: 1)
  - [x] Add `app.add_middleware(RequestIdMiddleware)` after CORSMiddleware registration

- [x] Update `backend/app/schemas/process.py` — add diagnostics to ProcessResponse (AC: 1, 2)
  - [x] Import `DiagnosticsPayload` from `app.schemas.diagnostics`
  - [x] Add `diagnostics: DiagnosticsPayload | None = None` field to `ProcessResponse`
  - [x] Update `validate_status_envelope` validator: success requires `diagnostics is not None`; partial requires `diagnostics is not None`; error must NOT include `diagnostics`

- [x] Update `backend/app/api/v1/process.py` — wire timing + diagnostics into response (AC: 1, 2)
  - [x] Remove inline `request_id = str(uuid4())` — read from `request.state.request_id` instead
  - [x] Capture `start_time = time.monotonic()` at entry of `process_image`
  - [x] Pass `start_time` into `_build_process_response` (or restructure timing capture there)
  - [x] Capture per-phase timings: `ocr_start`/`ocr_end` around `extract_chinese_segments`, `pinyin_start`/`pinyin_end` around `generate_pinyin`
  - [x] Build `UploadContext`, `TimingInfo`, `TraceInfo`, then call `build_diagnostics()`
  - [x] Include `diagnostics=` in all success and partial `ProcessResponse` returns; leave out of error returns
  - [x] Import `time`, `UploadContext`, `TimingInfo`, `TraceInfo`, `TraceStep`, `build_diagnostics`

- [x] Add unit tests in `backend/tests/unit/services/test_diagnostics_service.py` (AC: 1)
  - [x] `test_build_diagnostics_returns_correct_structure`: asserts all fields present
  - [x] `test_build_diagnostics_timing_fields`: total_ms populated, optional phase fields pass through

- [x] Add integration tests in `backend/tests/integration/api_v1/test_process_route.py` (AC: 1, 2)
  - [x] `test_process_route_success_includes_diagnostics`: success response has `diagnostics.upload_context`, `diagnostics.timing.total_ms`
  - [x] `test_process_route_partial_includes_diagnostics`: partial (pinyin failure) has `diagnostics`
  - [x] `test_process_route_error_excludes_diagnostics`: validation error response has no `diagnostics` key

- [x] Update contract tests in `backend/tests/contract/response_envelopes/test_process_envelopes.py` (AC: 2)
  - [x] Update `assert_process_envelope` helper to accept (not require) `diagnostics` field on success/partial
  - [x] Add `test_process_endpoint_success_envelope_includes_diagnostics_contract`: success path has `diagnostics` with required sub-fields
  - [x] Verify existing error envelope contract test: error path has no `diagnostics`

- [x] Verify all backend tests pass and `ruff check .` is clean

## Dev Notes

### Story Foundation

- **Epic goal**: Epic 3 builds the diagnostics/observability layer. Story 3-1 is the backend foundation: establish the `diagnostics` schema and payload structure, capture timing/upload context, wire it into the process endpoint. Story 3-2 then exposes this in the frontend DiagnosticsPanel.
- **FRs covered**: FR4 (retain upload metadata for diagnostics/history)
- **Dependencies**: Epic 1 + Epic 2 complete. The process path (success/partial/error), `OcrSegment` confidence values, `ProcessWarning` categories, and all existing envelope shapes are already established.
- **No frontend changes in this story** — DiagnosticsPanel.jsx is Story 3-2.

### Current State — What Exists

**`backend/app/api/v1/process.py` (current `process_image` entry):**
```python
@router.post('/process', ...)
async def process_image(request: Request) -> ProcessResponse:
    request_id = str(uuid4())   # ← remove; read from request.state instead
    ...
    return await _build_process_response(file_bytes, content_type, request_id=request_id)
```

**`backend/app/schemas/process.py` — current `ProcessResponse`:**
```python
class ProcessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["success", "partial", "error"]
    request_id: str
    data: ProcessData | None = None
    warnings: list[ProcessWarning] | None = None
    error: ProcessError | None = None
    # ← diagnostics field does NOT exist yet
```

**`backend/app/middleware/`:** Exists but only has `__init__.py`. `request_id.py` does NOT exist.

**`backend/app/services/`:** Has `image_validation.py`, `ocr_service.py`, `pinyin_service.py`. `diagnostics_service.py` does NOT exist.

**`backend/app/schemas/`:** Has only `process.py`. `diagnostics.py` does NOT exist.

**`backend/app/core/`:** Directory exists but is empty. `errors.py` does NOT exist yet.

**`backend/app/main.py`:** Has `CORSMiddleware` registered. `RequestIdMiddleware` not yet registered.

**Test counts from Story 2-4:** 69 backend tests pass, 28 frontend tests pass.

### New File: `backend/app/schemas/diagnostics.py`

```python
from typing import Literal

from pydantic import BaseModel


class UploadContext(BaseModel):
    content_type: str
    file_size_bytes: int


class TimingInfo(BaseModel):
    total_ms: float
    ocr_ms: float | None = None
    pinyin_ms: float | None = None


class TraceStep(BaseModel):
    step: str
    status: Literal["ok", "skipped", "failed"]


class TraceInfo(BaseModel):
    steps: list[TraceStep]


class DiagnosticsPayload(BaseModel):
    upload_context: UploadContext
    timing: TimingInfo
    trace: TraceInfo
```

Key points:
- `TimingInfo.ocr_ms` / `pinyin_ms` are optional — error paths (where OCR/pinyin never ran) can omit them
- `TraceInfo.steps` is a list — Story 3-1 populates basic steps; Story 3-2 just reads them
- All field names `snake_case` per API conventions
- No `model_config = ConfigDict(extra="forbid")` needed — these are internal schemas, not API envelope roots

### New File: `backend/app/services/diagnostics_service.py`

```python
from app.schemas.diagnostics import DiagnosticsPayload, TimingInfo, TraceInfo, UploadContext


def build_diagnostics(
    *,
    upload_context: UploadContext,
    timing: TimingInfo,
    trace: TraceInfo,
) -> DiagnosticsPayload:
    return DiagnosticsPayload(
        upload_context=upload_context,
        timing=timing,
        trace=trace,
    )
```

Keep it thin for now — the value is in the schema + wiring, not complex service logic. Story 3-4 (Sentry) will extend this.

### New File: `backend/app/middleware/request_id.py`

```python
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

Key points:
- `request.state.request_id` is the canonical way to pass per-request state through FastAPI/Starlette
- `X-Request-ID` response header is a useful convention for client-side correlation
- `BaseHTTPMiddleware` is the correct base class for Starlette/FastAPI middleware (already available via `starlette.middleware.base`)

### Updated `backend/app/main.py`

```python
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.middleware.request_id import RequestIdMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)

app = FastAPI(...)

def _get_cors_origins() -> list[str]: ...

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)  # ← add after CORS

app.include_router(api_v1_router)
```

Middleware execution order in Starlette: added last runs first (outermost). `RequestIdMiddleware` added after CORS means it runs after CORS but before route handlers — `request.state.request_id` is available to all route handlers.

### Updated `backend/app/schemas/process.py`

Add import and field:
```python
from app.schemas.diagnostics import DiagnosticsPayload   # add to imports

class ProcessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["success", "partial", "error"]
    request_id: str
    data: ProcessData | None = None
    warnings: list[ProcessWarning] | None = None
    error: ProcessError | None = None
    diagnostics: DiagnosticsPayload | None = None   # add this field
```

Update `validate_status_envelope` validator:
```python
@model_validator(mode="after")
def validate_status_envelope(self) -> "ProcessResponse":
    if self.status == "success":
        if self.data is None:
            raise ValueError("success responses require data")
        if self.diagnostics is None:
            raise ValueError("success responses require diagnostics")
        if self.warnings is not None or self.error is not None:
            raise ValueError("success responses cannot include warnings or error")
    elif self.status == "partial":
        if self.data is None or self.warnings is None:
            raise ValueError("partial responses require data and warnings")
        if self.diagnostics is None:
            raise ValueError("partial responses require diagnostics")
        if self.error is not None:
            raise ValueError("partial responses cannot include error")
    elif self.status == "error":
        if self.error is None:
            raise ValueError("error responses require error")
        if self.data is not None or self.warnings is not None:
            raise ValueError("error responses cannot include data or warnings")
        if self.diagnostics is not None:
            raise ValueError("error responses cannot include diagnostics")
    return self
```

Key points:
- `diagnostics` required for `success` and `partial` — enforced at schema level
- `diagnostics` MUST NOT be present for `error` — `response_model_exclude_none=True` on route will exclude it if `None`, but validator also blocks passing it explicitly
- The `extra="forbid"` config already catches stray fields

### Updated `backend/app/api/v1/process.py`

Full refactored `_build_process_response` with diagnostics:

```python
import time
from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, Request, UploadFile

from app.schemas.diagnostics import DiagnosticsPayload, TimingInfo, TraceInfo, TraceStep, UploadContext
from app.schemas.process import OcrData, ProcessData, ProcessError, ProcessResponse, ProcessWarning
from app.services.diagnostics_service import build_diagnostics
from app.services.image_validation import (
    ALLOWED_IMAGE_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,
    ImageValidationError,
    validate_image_upload,
)
from app.services.ocr_service import OcrServiceError, extract_chinese_segments, is_low_confidence
from app.services.pinyin_service import PinyinServiceError, generate_pinyin

router = APIRouter()


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
    trace_steps: list[TraceStep] = []

    if not image_bytes:
        return ProcessResponse(
            status="error",
            request_id=request_id,
            error=ProcessError(
                category="ocr",
                code="ocr_no_text_detected",
                message="No readable Chinese text was detected. Retake the photo and try again.",
            ),
        )

    ocr_start = time.monotonic()
    try:
        segments = await extract_chinese_segments(image_bytes, content_type)
        ocr_ms = (time.monotonic() - ocr_start) * 1000
        trace_steps.append(TraceStep(step="ocr", status="ok"))
    except OcrServiceError as error:
        ocr_ms = (time.monotonic() - ocr_start) * 1000
        trace_steps.append(TraceStep(step="ocr", status="failed"))
        return ProcessResponse(
            status="error",
            request_id=request_id,
            error=ProcessError(category=error.category, code=error.code, message=error.message),
        )

    pinyin_start = time.monotonic()
    try:
        pinyin_data = await generate_pinyin(segments)
        pinyin_ms = (time.monotonic() - pinyin_start) * 1000
        trace_steps.append(TraceStep(step="pinyin", status="ok"))
    except PinyinServiceError as error:
        pinyin_ms = (time.monotonic() - pinyin_start) * 1000
        trace_steps.append(TraceStep(step="pinyin", status="failed"))
        total_ms = (time.monotonic() - start_time) * 1000
        diagnostics = build_diagnostics(
            upload_context=upload_context,
            timing=TimingInfo(total_ms=total_ms, ocr_ms=ocr_ms, pinyin_ms=pinyin_ms),
            trace=TraceInfo(steps=trace_steps),
        )
        return ProcessResponse(
            status="partial",
            request_id=request_id,
            data=ProcessData(ocr=OcrData(segments=segments), job_id=None),
            warnings=[ProcessWarning(category=error.category, code=error.code, message=error.message)],
            diagnostics=diagnostics,
        )

    if is_low_confidence(segments):
        trace_steps.append(TraceStep(step="confidence_check", status="ok"))
        total_ms = (time.monotonic() - start_time) * 1000
        diagnostics = build_diagnostics(
            upload_context=upload_context,
            timing=TimingInfo(total_ms=total_ms, ocr_ms=ocr_ms, pinyin_ms=pinyin_ms),
            trace=TraceInfo(steps=trace_steps),
        )
        return ProcessResponse(
            status="partial",
            request_id=request_id,
            data=ProcessData(ocr=OcrData(segments=segments), pinyin=pinyin_data, job_id=None),
            warnings=[ProcessWarning(
                category="ocr",
                code="ocr_low_confidence",
                message="OCR confidence is low. Consider retaking the photo for better results.",
            )],
            diagnostics=diagnostics,
        )

    trace_steps.append(TraceStep(step="confidence_check", status="ok"))
    total_ms = (time.monotonic() - start_time) * 1000
    diagnostics = build_diagnostics(
        upload_context=upload_context,
        timing=TimingInfo(total_ms=total_ms, ocr_ms=ocr_ms, pinyin_ms=pinyin_ms),
        trace=TraceInfo(steps=trace_steps),
    )
    return ProcessResponse(
        status='success',
        request_id=request_id,
        data=ProcessData(ocr=OcrData(segments=segments), pinyin=pinyin_data, job_id=None),
        diagnostics=diagnostics,
    )


@router.post('/process', response_model=ProcessResponse, response_model_exclude_none=True, ...)
async def process_image(request: Request) -> ProcessResponse:
    start_time = time.monotonic()                          # ← capture before anything else
    request_id = request.state.request_id                 # ← read from middleware state (not uuid4())
    ...
    return await _build_process_response(
        file_bytes, content_type, request_id=request_id, start_time=start_time
    )
```

Key points:
- **Remove** `from uuid import uuid4` import if no longer used elsewhere in the file
- `start_time = time.monotonic()` captured at `process_image` entry (before body read) for accurate total_ms
- `time.monotonic()` is preferred over `time.time()` for elapsed durations (no clock drift)
- Error paths (validation errors, `OcrServiceError`) do NOT get diagnostics — they return early before timing capture completes, and architecture error envelope has no `diagnostics` field
- `ocr_ms` and `pinyin_ms` are passed as floats (milliseconds) — consistent with FR24

**IMPORTANT — existing tests:** All existing integration and contract tests construct `ProcessResponse` objects directly. After adding `diagnostics` as **required** for success/partial responses, any test that builds a success or partial `ProcessResponse` without `diagnostics` will fail the model validator. Tests MUST be updated to pass a `diagnostics` argument.

### Test Updates Required

#### Unit tests — new file: `backend/tests/unit/services/test_diagnostics_service.py`

```python
from app.schemas.diagnostics import TimingInfo, TraceInfo, TraceStep, UploadContext
from app.services.diagnostics_service import build_diagnostics


def test_build_diagnostics_returns_correct_structure() -> None:
    upload_context = UploadContext(content_type="image/jpeg", file_size_bytes=5000)
    timing = TimingInfo(total_ms=500.0, ocr_ms=300.0, pinyin_ms=150.0)
    trace = TraceInfo(steps=[TraceStep(step="ocr", status="ok")])

    result = build_diagnostics(upload_context=upload_context, timing=timing, trace=trace)

    assert result.upload_context.content_type == "image/jpeg"
    assert result.upload_context.file_size_bytes == 5000
    assert result.timing.total_ms == 500.0
    assert result.timing.ocr_ms == 300.0
    assert result.timing.pinyin_ms == 150.0
    assert len(result.trace.steps) == 1
    assert result.trace.steps[0].step == "ocr"
    assert result.trace.steps[0].status == "ok"


def test_build_diagnostics_optional_timing_fields() -> None:
    """Error paths can omit per-phase timing."""
    upload_context = UploadContext(content_type="image/png", file_size_bytes=1)
    timing = TimingInfo(total_ms=12.5)  # ocr_ms and pinyin_ms omitted
    trace = TraceInfo(steps=[])

    result = build_diagnostics(upload_context=upload_context, timing=timing, trace=trace)

    assert result.timing.total_ms == 12.5
    assert result.timing.ocr_ms is None
    assert result.timing.pinyin_ms is None
```

#### Integration tests — updates to `backend/tests/integration/api_v1/test_process_route.py`

**Add new tests:**

```python
def test_process_route_success_includes_diagnostics() -> None:
    """Success response includes diagnostics with upload_context and timing."""
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider([RawOcrSegment(text="你好", language="zh", confidence=0.95)]),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider([RawPinyinSegment(hanzi="你", pinyin="nǐ"), RawPinyinSegment(hanzi="好", pinyin="hǎo")]),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "success"
    assert response.diagnostics is not None
    assert response.diagnostics.upload_context.content_type == "image/png"
    assert response.diagnostics.upload_context.file_size_bytes == len(PNG_1X1_BYTES)
    assert response.diagnostics.timing.total_ms >= 0.0
    assert response.diagnostics.timing.ocr_ms is not None
    assert response.diagnostics.timing.pinyin_ms is not None
    assert len(response.diagnostics.trace.steps) >= 1


def test_process_route_partial_includes_diagnostics() -> None:
    """Partial (pinyin failure) response includes diagnostics."""
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider([RawOcrSegment(text="你好", language="zh", confidence=0.95)]),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=FailingPinyinProvider(),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "partial"
    assert response.diagnostics is not None
    assert response.diagnostics.upload_context is not None
    assert response.diagnostics.timing.total_ms >= 0.0


def test_process_route_error_excludes_diagnostics() -> None:
    """Validation error response has no diagnostics field."""
    request = _request_with_body(b"", "image/jpeg")  # empty body → error path
    response = asyncio.run(process_image(request))

    assert response.status == "error"
    assert response.diagnostics is None
```

**CRITICAL — update existing tests that construct `ProcessResponse` directly:**

After adding `diagnostics` as required for success/partial, any test that builds `ProcessResponse(status="success", ...)` or `ProcessResponse(status="partial", ...)` without `diagnostics` will now fail the model validator. Search for `ProcessResponse(` in existing test files and add minimal valid diagnostics:

```python
# Helper for tests that need a minimal valid DiagnosticsPayload:
def _minimal_diagnostics() -> DiagnosticsPayload:
    from app.schemas.diagnostics import DiagnosticsPayload, TimingInfo, TraceInfo, UploadContext
    return DiagnosticsPayload(
        upload_context=UploadContext(content_type="image/png", file_size_bytes=1),
        timing=TimingInfo(total_ms=0.0),
        trace=TraceInfo(steps=[]),
    )
```

The existing integration tests that call `process_image()` (not constructing `ProcessResponse` directly) will pass automatically once the route wires in diagnostics.

#### Contract tests — updates to `backend/tests/contract/response_envelopes/test_process_envelopes.py`

Update `assert_process_envelope` to check diagnostics field for success/partial paths:

```python
def test_process_endpoint_success_envelope_includes_diagnostics_contract() -> None:
    """Success envelope must include diagnostics with required sub-structure."""
    with patch(...):  # standard success stubs
        response = asyncio.run(process_image(_request_with_body(PNG_1X1_BYTES, "image/png")))
    payload = response.model_dump(exclude_none=True)

    assert_process_envelope(payload)
    assert "diagnostics" in payload
    assert "upload_context" in payload["diagnostics"]
    assert "timing" in payload["diagnostics"]
    assert "total_ms" in payload["diagnostics"]["timing"]
    assert "trace" in payload["diagnostics"]
    assert "steps" in payload["diagnostics"]["trace"]
```

### Architecture Compliance

- **Response envelope**: `diagnostics` added to success/partial per architecture spec (`{ "status": "success", "request_id": "...", "data": {...}, "diagnostics": {...} }`). Error envelope intentionally has no `diagnostics` field.
- **`response_model_exclude_none=True`**: Since `diagnostics` is `None` on error responses, it will be excluded from serialized output automatically. On success/partial, it will always be present (enforced by validator).
- **snake_case**: All new field names follow `snake_case` convention.
- **Middleware pattern**: `BaseHTTPMiddleware` is the correct FastAPI/Starlette extension point for request-scoped state injection.
- **Timing**: `time.monotonic()` for elapsed measurement — no clock drift.
- **No sensitive leak**: `diagnostics` contains only upload context (content_type, file_size_bytes) and timing/trace data. No OCR provider credentials, internal stack traces, or provider-specific error details.

### File Structure Requirements

**New files:**
- `backend/app/schemas/diagnostics.py`
- `backend/app/services/diagnostics_service.py`
- `backend/app/middleware/request_id.py`
- `backend/tests/unit/services/test_diagnostics_service.py`

**Modified files:**
- `backend/app/main.py` — add `RequestIdMiddleware`
- `backend/app/schemas/process.py` — add `diagnostics` field + validator updates
- `backend/app/api/v1/process.py` — remove inline `uuid4()`, add timing, build + attach diagnostics
- `backend/tests/integration/api_v1/test_process_route.py` — add 3 new tests; update existing direct ProcessResponse constructions
- `backend/tests/contract/response_envelopes/test_process_envelopes.py` — add diagnostics contract test

**Files NOT to touch:**
- `frontend/` — DiagnosticsPanel is Story 3-2
- `backend/app/services/ocr_service.py` — no changes
- `backend/app/services/pinyin_service.py` — no changes
- `backend/app/services/image_validation.py` — no changes
- `backend/app/schemas/process.py` validators for success/partial (other than adding `diagnostics` requirement)

### Previous Story Intelligence (2.4 → 3.1)

- **69 backend tests passing** at story 2-4 completion. Expect ~74 after 3-1 (+2 unit, +3 integration, +1 contract; existing tests may need minor fixes for `diagnostics` field on direct `ProcessResponse` constructions).
- **28 frontend tests passing** — no frontend changes in story 3-1.
- **`ProcessWarning.category` is typed** (`ErrorCategory`) — no changes needed to warning handling.
- **`response_model_exclude_none=True`** on `/v1/process` route: `diagnostics=None` on error responses is excluded from JSON output automatically. No manual exclusion needed.
- **`ProcessResponse` has `extra="forbid"`**: Must add `diagnostics` to the model definition before any code passes it.
- **`FailingPinyinProvider`** already in `test_process_route.py` (lines 25-28) — reuse in new partial+diagnostics test.
- **`StubOcrProvider` and `StubPinyinProvider`** already defined — reuse for new success+diagnostics test.
- **`_request_with_body`** helper already exists in integration test file — use it.

### Git Intelligence

- `674f74a` (current): Course correction — sprint change proposals applied (target platform: Render, observability: Sentry). Epic 2 work merged.
- `3f51fe1`: Epic 2 — confidence threshold, partial responses, low-confidence guidance.
- `2d1d533`: Epic 1 — full process pipeline, OCR, pinyin, contract tests, Bruno collection.
- Key pattern: existing stories created comprehensive unit + integration + contract tests. Follow this three-layer test pattern.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-3.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#API-Response-Formats — diagnostics in success/partial envelopes]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project-Directory-Structure — middleware/request_id.py, services/diagnostics_service.py, schemas/diagnostics.py]
- [Source: _bmad-output/planning-artifacts/architecture.md#Cross-Cutting-Concerns — request correlation via middleware]
- [Source: backend/app/api/v1/process.py — current _build_process_response, request_id generation pattern]
- [Source: backend/app/schemas/process.py — ProcessResponse model, existing validator pattern]
- [Source: backend/app/main.py — current middleware registration pattern]
- [Source: backend/tests/integration/api_v1/test_process_route.py — StubOcrProvider, StubPinyinProvider, FailingPinyinProvider, _request_with_body patterns]
- [Source: _bmad-output/implementation-artifacts/2-4-add-low-confidence-guidance-and-in-flow-retry.md — Dev Notes, test count baselines]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest tests/unit/services/test_diagnostics_service.py tests/unit/schemas/test_process_response_contract.py tests/integration/api_v1/test_process_route.py tests/contract/response_envelopes/test_process_envelopes.py`
- `uv run pytest`
- `uv run ruff check .`

### Completion Notes List

- Added diagnostics schemas, a thin diagnostics service, and request ID middleware for per-request correlation plus `X-Request-ID` response headers.
- Wired upload context, total/phase timings, and trace steps into success and partial `/v1/process` responses while keeping error envelopes free of diagnostics.
- Updated envelope validation and backend tests to require diagnostics on success/partial, exclude them on error, and keep direct route tests middleware-compatible.
- Hardened the legacy smoke test so it checks current wiring markers instead of stale scaffold literals.

### File List

- `backend/app/schemas/diagnostics.py`
- `backend/app/services/diagnostics_service.py`
- `backend/app/middleware/request_id.py`
- `backend/app/main.py`
- `backend/app/schemas/process.py`
- `backend/app/api/v1/process.py`
- `backend/tests/unit/services/test_diagnostics_service.py`
- `backend/tests/integration/api_v1/test_process_route.py`
- `backend/tests/contract/response_envelopes/test_process_envelopes.py`
- `backend/tests/helpers.py`
- `backend/tests/unit/schemas/test_process_response_contract.py`
- `backend/tests/test_story1_smoke.py`

## Change Log

- 2026-03-26: Story 3-1 created — capture request metadata and structured diagnostics payload; establishes DiagnosticsPayload schema, diagnostics_service, RequestIdMiddleware, wires timing/upload context into success+partial envelopes
- 2026-03-26: Story 3-1 implemented and validated; backend diagnostics payloads, request correlation middleware, route/test updates, full backend pytest, and ruff all passing
- 2026-03-26: Code review completed; schema hardening applied — TimingInfo.ocr_ms/pinyin_ms made required, ge=0 constraints added, TraceStep.step constrained to Literal, confidence_check trace status corrected to "failed" on low-confidence path, request_id fallback guard added, X-Request-ID header guaranteed on error responses, _make_diagnostics helper extracted, middleware end-to-end tests added (96 tests passing)
