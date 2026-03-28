# Story 4.6: Restrict Oversized or High-Cost Inputs

Status: done

## Story

As Clint,
I want oversized or risky uploads constrained up front,
so that accidental high-cost requests are prevented.

## Acceptance Criteria

1. **Given** an upload file size exceeds the configured limit (default 8 MB, overridable via `MAX_UPLOAD_BYTES` env var), **When** request intake validation runs, **Then** the request is rejected with `status="error"`, `category="validation"`, `code="file_too_large"`, and a message with concrete corrective guidance **And** no OCR call is made.

2. **Given** an upload's decoded pixel count exceeds the configured limit (default 25 000 000 px, overridable via `MAX_UPLOAD_PIXELS` env var), **When** request intake validation runs, **Then** the request is rejected with `status="error"`, `category="validation"`, `code="image_too_large_pixels"`, and a message with concrete corrective guidance **And** no OCR call is made.

3. **Given** an upload passes all guardrail checks (MIME type, file size, pixel count), **When** validation succeeds, **Then** the request proceeds to processing **And** a structured INFO log entry is emitted containing `file_size_bytes` and `content_type` for audit/diagnostic context.

4. **Given** `MAX_UPLOAD_BYTES` env var is absent or non-integer, **When** the limit is evaluated, **Then** the default 8 MB is used.

5. **Given** `MAX_UPLOAD_PIXELS` env var is absent or non-integer, **When** the limit is evaluated, **Then** the default 25 000 000 px is used.

6. **Given** all existing backend tests run, **When** this story's changes are applied, **Then** all existing tests continue to pass.

## Tasks / Subtasks

- [x] Add `get_configured_max_upload_bytes()` and `get_configured_max_image_pixels()` to `backend/app/services/image_validation.py` (AC: 1–2, 4–5)
  - [x] Add `import os` (if not already present — it is not currently imported in image_validation.py)
  - [x] Add `def get_configured_max_upload_bytes() -> int` — reads `MAX_UPLOAD_BYTES` env var, falls back to `MAX_FILE_SIZE_BYTES` constant on missing/invalid value
  - [x] Add `def get_configured_max_image_pixels() -> int` — reads `MAX_UPLOAD_PIXELS` env var, falls back to `MAX_IMAGE_PIXELS` constant on missing/invalid value
  - [x] Update `validate_image_upload()` to call these functions instead of referencing the module constants directly

- [x] Update `backend/app/api/v1/process.py` to use configurable limits and emit guardrail audit log (AC: 1–3, 6)
  - [x] Add `import logging; logger = logging.getLogger(__name__)` near the top of the file (after stdlib imports)
  - [x] Import `get_configured_max_upload_bytes` from `app.services.image_validation` (in addition to existing imports)
  - [x] In `process_image`, compute `max_bytes = get_configured_max_upload_bytes()` once at the top of the handler
  - [x] Replace `MAX_FILE_SIZE_BYTES` in the Content-Length pre-check and in the `_read_request_body_with_limit` call with `max_bytes`
  - [x] After `validate_image_upload(file)` succeeds, emit: `logger.info("input_guardrail_pass file_size_bytes=%d content_type=%s", len(file_bytes), content_type)`

- [x] Write unit tests in `backend/tests/unit/services/test_image_validation.py` (AC: 1–2, 4–5)
  - [x] `test_get_configured_max_upload_bytes_returns_default` — no env var set → returns `MAX_FILE_SIZE_BYTES`
  - [x] `test_get_configured_max_upload_bytes_reads_env_var` — `MAX_UPLOAD_BYTES=4194304` → returns 4 194 304
  - [x] `test_get_configured_max_upload_bytes_invalid_env_var_uses_default` — `MAX_UPLOAD_BYTES=bad` → returns `MAX_FILE_SIZE_BYTES`
  - [x] `test_get_configured_max_image_pixels_returns_default` — no env var set → returns `MAX_IMAGE_PIXELS`
  - [x] `test_get_configured_max_image_pixels_reads_env_var` — `MAX_UPLOAD_PIXELS=1000000` → returns 1 000 000
  - [x] `test_get_configured_max_image_pixels_invalid_env_var_uses_default` — `MAX_UPLOAD_PIXELS=bad` → returns `MAX_IMAGE_PIXELS`
  - [x] `test_validate_image_upload_respects_env_var_size_limit` — set `MAX_UPLOAD_BYTES=4`, upload 5-byte PNG → `code="file_too_large"`
  - [x] `test_validate_image_upload_respects_env_var_pixel_limit` — set `MAX_UPLOAD_PIXELS=0` → `code="image_too_large_pixels"`

- [x] Write integration test in `backend/tests/integration/api_v1/test_process_route.py` (AC: 3, 6)
  - [x] `test_upload_within_limits_emits_guardrail_log` — valid PNG upload with OCR stub → assert `caplog` contains `"input_guardrail_pass"` at INFO level

## Dev Notes

### New functions in `backend/app/services/image_validation.py`

Add `import os` at the top of the file (currently absent). Then add after the existing constants:

```python
import os  # add to imports


def get_configured_max_upload_bytes() -> int:
    """Return the effective file-size ceiling, preferring MAX_UPLOAD_BYTES env var."""
    try:
        return int(os.environ.get("MAX_UPLOAD_BYTES", ""))
    except (ValueError, TypeError):
        return MAX_FILE_SIZE_BYTES


def get_configured_max_image_pixels() -> int:
    """Return the effective pixel-count ceiling, preferring MAX_UPLOAD_PIXELS env var."""
    try:
        return int(os.environ.get("MAX_UPLOAD_PIXELS", ""))
    except (ValueError, TypeError):
        return MAX_IMAGE_PIXELS
```

Then update `validate_image_upload()`:
- Replace `if size_bytes > MAX_FILE_SIZE_BYTES:` with `if size_bytes > get_configured_max_upload_bytes():`
- Replace `if width * height > MAX_IMAGE_PIXELS:` with `if width * height > get_configured_max_image_pixels():`

**Why keep the constants as-is:** Existing tests use `monkeypatch.setattr(image_validation, "MAX_FILE_SIZE_BYTES", 4)` to patch the constants directly — this still works because the new helper functions fall back to those constants when the env var is absent or empty. No existing test changes needed.

### Changes to `backend/app/api/v1/process.py`

Add near the top of the file (after `import time`):

```python
import logging

logger = logging.getLogger(__name__)
```

Add to the `from app.services.image_validation import ...` block:

```python
from app.services.image_validation import (
    ALLOWED_IMAGE_MIME_TYPES,
    MAX_FILE_SIZE_BYTES,       # keep for backward compatibility in any other references
    ImageValidationError,
    get_configured_max_upload_bytes,
    validate_image_upload,
)
```

In `process_image()`, add this near the top (right after `_set_sentry_request_context(request_id)`):

```python
max_bytes = get_configured_max_upload_bytes()
```

Then replace the two existing uses of `MAX_FILE_SIZE_BYTES` in that function with `max_bytes`:

```python
# Content-Length pre-check (was MAX_FILE_SIZE_BYTES):
if int(content_length) > max_bytes:
    ...

# Body read (was MAX_FILE_SIZE_BYTES):
file_bytes = await _read_request_body_with_limit(request, max_bytes=max_bytes)
```

And after `validate_image_upload(file)` succeeds (right before the budget check):

```python
logger.info(
    "input_guardrail_pass file_size_bytes=%d content_type=%s",
    len(file_bytes),
    content_type,
)
```

**Why call `get_configured_max_upload_bytes()` once in `process_image` rather than in each sub-call:** The env var is read once per request to avoid multiple `os.environ` lookups; result is passed as `max_bytes`. This also makes it easy to test the routing behavior with `monkeypatch.setenv`.

**`MAX_FILE_SIZE_BYTES` import note:** It can be removed from the `process.py` import block once all usages are replaced with `max_bytes`. The only remaining reference would be the OpenAPI helper function — check if `_binary_openapi_content` or any other function still references `MAX_FILE_SIZE_BYTES`; if not, remove the import.

### Integration test helper pattern

```python
def test_upload_within_limits_emits_guardrail_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.delenv("OCR_PROVIDER", raising=False)
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider([RawOcrSegment(text="你好", language="zh", confidence=0.9)]),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider([RawPinyinSegment(hanzi="你", pinyin="nǐ")]),
    ), caplog.at_level(logging.INFO, logger="app.api.v1.process"):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        asyncio.run(process_image(request))

    assert any("input_guardrail_pass" in record.message for record in caplog.records)
```

Note: `StubPinyinProvider` is already defined in `test_process_route.py`. Import `logging` in the test file.

### Architecture Compliance

- **`image_validation.py` location:** `backend/app/services/image_validation.py` — correct per architecture file tree
- **Env var naming:** `MAX_UPLOAD_BYTES`, `MAX_UPLOAD_PIXELS` — consistent with SCREAMING_SNAKE_CASE convention (same as `DAILY_BUDGET_SGD`, `BUDGET_ENFORCE_MODE`)
- **No new dependencies** — stdlib only (`os`, `logging`)
- **Error category stays `"validation"`** — oversized input is an input validity check, not a budget category. The budget-safety motivation is captured in the guardrail log.
- **Logging uses stdlib `logging`** — consistent with FastAPI + Uvicorn conventions; Sentry breadcrumbs not needed for pass events

### What Already Exists (Do Not Reinvent)

- `MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024` — the default constant in `image_validation.py`
- `MAX_IMAGE_PIXELS = 25_000_000` — the default constant in `image_validation.py`
- `_read_request_body_with_limit()` — streaming body reader with byte ceiling, already in `process.py`
- `validate_image_upload()` — MIME/size/pixel validation, already in `image_validation.py`
- `_build_validation_error_response()` — error envelope builder for validation failures, already in `process.py`
- All existing validation error codes (`file_too_large`, `image_too_large_pixels`, `invalid_mime_type`, `missing_file`, `image_decode_failed`) — already defined and tested

Story 4.6 only **adds** configurability and an audit log line on top of the existing validation path. It does NOT modify the error codes, messages, or envelope shapes.

### Critical Files to Touch

| File | Action | Reason |
|------|--------|--------|
| `backend/app/services/image_validation.py` | Modify | Add `get_configured_max_upload_bytes()`, `get_configured_max_image_pixels()`; update validation to call them |
| `backend/app/api/v1/process.py` | Modify | Import helpers; use `max_bytes` local from env-aware helper; emit guardrail pass log |
| `backend/tests/unit/services/test_image_validation.py` | Modify | Add 8 unit tests for the two new helper functions and env-var respecting validation |
| `backend/tests/integration/api_v1/test_process_route.py` | Modify | Add 1 integration test for guardrail pass log emission |

**Files NOT to touch:**
- `backend/app/schemas/process.py` — no schema changes needed; existing `ErrorCategory` and error envelopes are sufficient
- `backend/app/services/budget_service.py` — budget threshold is separate from input guardrails
- `backend/app/core/metrics.py` — no new metrics counter needed for guardrail events (log is sufficient)
- All frontend files — backend-only story
- `backend/.env.example` — optional: may add commented `# MAX_UPLOAD_BYTES=8388608` and `# MAX_UPLOAD_PIXELS=25000000` for discoverability, but not required for AC

### Learnings from Stories 4.3–4.5

- Env var pattern: `int(os.environ.get("ENV_VAR", ""))` with try/except ValueError — matches `estimate_request_cost` and `check_budget_threshold` patterns in `budget_service.py`
- Ruff lint must pass: `cd backend && ./.venv/bin/python -m ruff check .`
- Run all backend tests from `backend/`: `./.venv/bin/python -m pytest`
- Integration tests use `asyncio.run(process_image(request))` with `_request_with_body(body_bytes, content_type)` helper from `helpers.py`
- `StubOcrProvider` and `PNG_1X1_BYTES` are imported from `helpers` in the integration test file
- Monkeypatching env vars uses `monkeypatch.setenv("VAR", "value")` / `monkeypatch.delenv("VAR", raising=False)`
- Unit tests for image_validation already use `monkeypatch.setattr(image_validation, "MAX_FILE_SIZE_BYTES", 4)` — keep existing tests intact; new tests use `monkeypatch.setenv` to exercise the env-var path

### Git Intelligence

- `4678c3f` — Story 4-5: budget threshold check and enforcement in `process.py`; pattern for env-var-driven behavior at request time
- `9c82a15` — Story 4-4: `DailyCostStore`, `daily_cost_store` singleton, `record_request_cost()` in `budget_service.py`
- `3b6a8ac` — Story 4-3: `estimate_request_cost()`, env-var pattern for `OCR_PROVIDER`
- The validation pipeline (Story 1.3 baseline) was established very early; all existing tests must remain green

### References

- Epic spec: `_bmad-output/planning-artifacts/epics.md` — Epic 4, Story 4.6
- Architecture: `_bmad-output/planning-artifacts/architecture.md` — security baseline section ("request-size limits, MIME/type validation"); budget guardrail component in file tree
- FR32: System can restrict oversized or potentially expensive inputs
- Architecture security baseline: "request-size limits, MIME/type validation" explicitly called out under Authentication & Security
- Image validation service: `backend/app/services/image_validation.py`
- Process route: `backend/app/api/v1/process.py`
- Existing image validation tests: `backend/tests/unit/services/test_image_validation.py`
- Previous story: `_bmad-output/implementation-artifacts/4-5-enforce-or-warn-on-daily-budget-threshold.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `cd backend && ./.venv/bin/python -m pytest tests/unit/services/test_image_validation.py tests/integration/api_v1/test_process_route.py`
- `cd backend && ./.venv/bin/python -m ruff check .`
- `cd backend && ./.venv/bin/python -m pytest`

### Implementation Plan

- Add env-aware upload byte and pixel ceiling helpers in `backend/app/services/image_validation.py` and route validation through them without changing existing error envelopes.
- Update `backend/app/api/v1/process.py` to compute the effective byte limit once per request, apply it in the header/body guards, and log successful guardrail validation with file size and content type.
- Add unit coverage for default/env/invalid env behavior plus validation enforcement, then add an integration test covering the INFO guardrail log on a successful upload.

### Completion Notes List

- Added env-aware upload byte and pixel guardrail helpers while preserving existing fallback constants and validation error contracts.
- Updated the process route to resolve the effective request byte limit once per request, apply it to both header and streamed body checks, and emit an INFO audit log for successful guardrail validation.
- Added targeted unit and integration coverage for env-var defaults, overrides, invalid env fallback behavior, and the successful guardrail log path.
- Verified with `cd backend && ./.venv/bin/python -m ruff check .` and `cd backend && ./.venv/bin/python -m pytest` (164 passed).

### File List

- backend/app/services/image_validation.py
- backend/app/api/v1/process.py
- backend/tests/unit/services/test_image_validation.py
- backend/tests/integration/api_v1/test_process_route.py

### Change Log

- 2026-03-28: Story created, status set to ready-for-dev
- 2026-03-28: Implemented configurable upload byte/pixel guardrails, added successful guardrail audit logging, and expanded backend test coverage; status set to review
