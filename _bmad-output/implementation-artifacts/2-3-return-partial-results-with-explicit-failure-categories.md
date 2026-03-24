# Story 2.3: Return Partial Results with Explicit Failure Categories

Status: done

## Story

As Clint,
I want the system to return partial outcomes when full processing is not possible,
So that I still get usable reading help instead of a hard failure.

## Acceptance Criteria

1. **Given** processing fails in one stage after earlier stages succeed, **When** /v1/process completes, **Then** response uses `status="partial"` when at least one stage succeeds and one stage fails **And** `warnings[].category` and `warnings[].code` are populated with typed values from the shared taxonomy.

2. **Given** a fully unrecoverable error occurs, **When** response is returned, **Then** error envelope uses defined reason categories **And** user-facing messaging remains actionable and concise.

## Tasks / Subtasks

- [x] Add `category` field to `ProcessWarning` in `backend/app/schemas/process.py` (AC: 1)
  - [x] Require `category` and constrain it to the shared warning/error taxonomy
- [x] Change pinyin failure path in `backend/app/api/v1/process.py` to return `partial` instead of `error` (AC: 1)
  - [x] Catch `PinyinServiceError` and return `status="partial"` with OCR data + warning
  - [x] Warning must have `category=error.category`, `code=error.code`, `message=error.message`
  - [x] `data.pinyin` is absent (None) in the partial response — OCR data is the partial result
- [x] Add warnings display to `frontend/src/features/process/components/UploadForm.jsx` (AC: 1)
  - [x] Show each `mutation.data.warnings[]` entry when `status="partial"`, using `recoveryGuidanceByCode[w.code] || w.message`
  - [x] Use `role="status"` and `className="status-panel__warning"` on warning paragraph
- [x] Update contract tests in `backend/tests/contract/response_envelopes/test_process_envelopes.py` (AC: 1, 2)
  - [x] Update `assert_process_envelope` partial branch: add check that each warning has `category` and `code` keys
  - [x] Update `test_process_endpoint_partial_envelope_contract`: add `category` to `ProcessWarning` construction
  - [x] Update `test_process_endpoint_pinyin_error_envelope_contract`: now expects `status="partial"`, not `error`
- [x] Update integration tests in `backend/tests/integration/api_v1/test_process_route.py` (AC: 1, 2)
  - [x] Update `test_process_route_pinyin_failure_returns_typed_pinyin_error`: expects `status="partial"` with OCR data and `warnings[0].category="pinyin"`
  - [x] Add `test_process_route_pinyin_failure_partial_includes_ocr_data`: validates OCR segments are preserved in partial response
- [x] Add frontend tests in `frontend/src/__tests__/features/process/upload-form.test.jsx` (AC: 1)
  - [x] Add test: `partial` response with `pinyin_provider_unavailable` warning → warning guidance text rendered
  - [x] Update `DEFAULT_PARTIAL_RESPONSE` fixture to include `warnings` array (category + code + message)
- [x] Verify all backend tests pass and `ruff check .` is clean (AC: 1, 2)
- [x] Verify all frontend tests pass (AC: 1)

## Dev Notes

### Story Foundation

- **Epic goal**: Epic 2 improves output trust. Story 2-3 makes the partial result path real — when OCR succeeds but pinyin fails, the user gets their OCR data and a clear explanation instead of a hard error.
- **Dependencies**: Requires Stories 2-1 and 2-2 complete. OCR segments already filtered (2-1) and aligned (2-2). This story changes what happens when `PinyinServiceError` propagates out of `generate_pinyin()`.
- **FRs covered**: FR16 (explicit failure reason categories), FR19 (partial results when full extraction not possible).

### Current State — What Exists

**`ProcessWarning` (current — `backend/app/schemas/process.py`):**
```python
class ProcessWarning(BaseModel):
    category: ErrorCategory
    code: str
    message: str
```
Story 2-3 adds `category` matching the error taxonomy.

**`ProcessError` (for reference — same file):**
```python
class ProcessError(BaseModel):
    category: str = "processing"
    code: str
    message: str
```
`ProcessWarning` should mirror this pattern with `category`.

**`_build_process_response` (current — `backend/app/api/v1/process.py` lines 67-74):**
```python
try:
    pinyin_data = await generate_pinyin(segments)
except PinyinServiceError as error:
    return ProcessResponse(
        status="error",
        request_id=request_id,
        error=ProcessError(category=error.category, code=error.code, message=error.message),
    )
```
This must change to return `partial`. The OCR data (`segments`) is already in scope — use it.

**`PinyinServiceError` (current — `backend/app/services/pinyin_service.py`):**
```python
class PinyinServiceError(Exception):
    def __init__(self, *, code: str, message: str, category: str = PINYIN_ERROR_CATEGORY):
        # PINYIN_ERROR_CATEGORY = "pinyin"
```
`error.category` will always be `"pinyin"` for these failures. `error.code` is `"pinyin_provider_unavailable"` or similar.

**Schema model validator for `partial` (current — `process.py`):**
```python
elif self.status == "partial":
    if self.data is None or self.warnings is None:
        raise ValueError("partial responses require data and warnings")
    if self.error is not None:
        raise ValueError("partial responses cannot include error")
```
`partial` requires both `data` AND `warnings`, and cannot include `error`. The new path must supply both.

**Current test (integration — `test_process_route.py` lines 121-137):**
```python
def test_process_route_pinyin_failure_returns_typed_pinyin_error() -> None:
    ...
    assert response.status == "error"
    assert response.error.category == "pinyin"
    assert response.error.code == "pinyin_provider_unavailable"
```
This test must be updated to expect `status="partial"`.

**Current contract test (`test_process_envelopes.py` lines 142-162):**
```python
def test_process_endpoint_pinyin_error_envelope_contract() -> None:
    ...
    assert payload["status"] == "error"
    assert payload["error"]["category"] == "pinyin"
```
This test must be updated: pinyin failure now returns `partial`, not `error`.

**Frontend test (current — `upload-form.test.jsx` lines 208-224):**
```javascript
it('shows pinyin retry guidance when pinyin fails', async () => {
    submitProcessRequest.mockRejectedValueOnce(
      Object.assign(new Error('pinyin unavailable'), { code: 'pinyin_provider_unavailable' })
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(...)
})
```
This test simulates the api-client throwing (e.g., HTTP-level failure). It remains valid — keep it. Add a new test for the actual partial response path.

**`DEFAULT_PARTIAL_RESPONSE` (frontend test — lines 28-46):**
```javascript
const DEFAULT_PARTIAL_RESPONSE = {
  status: 'partial',
  request_id: 'req_partial',
  data: { ocr: {...}, pinyin: {...} },
}
```
This fixture has no `warnings` array. Update it to include `warnings` so it represents a realistic partial response for story 2-3.

### Schema Change — `ProcessWarning` Gets `category`

In `backend/app/schemas/process.py`, add `category` to `ProcessWarning`:

```python
class ProcessWarning(BaseModel):
    category: ErrorCategory
    code: str
    message: str
```

`category` should be explicit and limited to the shared taxonomy so warning producers cannot silently emit invalid categories.

**Taxonomy values for `category`:** Use the shared error taxonomy: `"validation"`, `"ocr"`, `"pinyin"`, `"system"`, `"budget"`, `"upstream"`. For pinyin failures, `category="pinyin"`.

### Route Handler Change — Partial Instead of Error

Replace the `PinyinServiceError` catch in `_build_process_response` (`backend/app/api/v1/process.py`):

```python
try:
    pinyin_data = await generate_pinyin(segments)
except PinyinServiceError as error:
    return ProcessResponse(
        status="partial",
        request_id=request_id,
        data=ProcessData(
            ocr=OcrData(segments=segments),
            job_id=None,
        ),
        warnings=[
            ProcessWarning(
                category=error.category,
                code=error.code,
                message=error.message,
            )
        ],
    )
```

Key points:
- `segments` is already in scope (from `extract_chinese_segments` call above)
- `data.pinyin` is absent (None) — no pinyin was produced
- `warnings` has exactly one entry: the typed pinyin failure
- Import: `ProcessWarning` is already imported in `process.py` (it's in the `from app.schemas.process import ...` line — verify it's included)

**Check the import line in `process.py` (line 6):**
```python
from app.schemas.process import OcrData, ProcessData, ProcessError, ProcessResponse
```
`ProcessWarning` is NOT currently imported. Add it:
```python
from app.schemas.process import OcrData, ProcessData, ProcessError, ProcessResponse, ProcessWarning
```

### Frontend Change — Display Warnings

In `UploadForm.jsx`, add warnings display inside the `{mutation.data && (...)}` block, after the partial note and before the result view:

```jsx
{mutation.data.status === 'partial' && mutation.data.warnings?.length > 0 && (
  <div aria-label="processing-warnings">
    {mutation.data.warnings.map((w, i) => (
      <p
        key={`${w.code}-${i}`}
        className="status-panel__warning"
        role="status"
      >
        {recoveryGuidanceByCode[w.code] || w.message}
      </p>
    ))}
  </div>
)}
```

Place this AFTER the existing partial note paragraph and BEFORE the result-view block.

The `recoveryGuidanceByCode` map already contains `pinyin_provider_unavailable`. When OCR succeeds and pinyin fails, the user sees:
- "Partial result available" (existing partial note)
- "Pinyin generation is temporarily unavailable. Tap Submit to retry." (warning from map)
- OCR data in the collapsed details section (already working)

### Test Updates Required

#### Contract tests (`backend/tests/contract/response_envelopes/test_process_envelopes.py`)

**`assert_process_envelope` partial branch (lines 56-61):** Add category/code check on each warning:
```python
elif status == "partial":
    assert "data" in envelope
    assert isinstance(envelope["data"], Mapping)
    assert "warnings" in envelope
    assert isinstance(envelope["warnings"], list)
    for w in envelope["warnings"]:
        assert "category" in w, f"warning missing category: {w}"
        assert "code" in w, f"warning missing code: {w}"
    assert "error" not in envelope
```

**`test_process_endpoint_partial_envelope_contract`:** Add `category` to `ProcessWarning`:
```python
warnings=[ProcessWarning(category="ocr", code="ocr-low-confidence", message="Low confidence score")],
```

**`test_process_endpoint_pinyin_error_envelope_contract`:** Pinyin failure now returns `partial`:
```python
def test_process_endpoint_pinyin_error_envelope_contract() -> None:
    """Pinyin provider failure must return a valid partial envelope with a typed warning."""
    class FailingPinyinProvider:
        def generate(self, *, text: str) -> list[RawPinyinSegment]:
            raise PinyinProviderUnavailableError("down")

    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider([RawOcrSegment(text="你好", language="zh", confidence=0.91)]),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=FailingPinyinProvider(),
    ):
        response = asyncio.run(process_image(_request_with_body(PNG_1X1_BYTES, "image/png")))
    payload = response.model_dump(exclude_none=True)
    assert_process_envelope(payload)
    assert payload["status"] == "partial"
    assert len(payload["warnings"]) == 1
    assert payload["warnings"][0]["category"] == "pinyin"
    assert payload["warnings"][0]["code"] == "pinyin_provider_unavailable"
```

Note: remove the `from app.adapters.pinyin_provider import PinyinProviderUnavailableError` inline import from the old test and add it at the top of the file (or keep inline — follow existing pattern in the file).

#### Integration tests (`backend/tests/integration/api_v1/test_process_route.py`)

**`test_process_route_pinyin_failure_returns_typed_pinyin_error`:** Update expectations:
```python
def test_process_route_pinyin_failure_returns_typed_pinyin_error() -> None:
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [RawOcrSegment(text="你好", language="zh", confidence=0.95)]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=FailingPinyinProvider(),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "partial"
    assert response.error is None
    assert response.data is not None
    assert response.data.ocr is not None
    assert len(response.data.ocr.segments) == 1
    assert response.warnings is not None
    assert len(response.warnings) == 1
    assert response.warnings[0].category == "pinyin"
    assert response.warnings[0].code == "pinyin_provider_unavailable"
```

**Add new test `test_process_route_pinyin_failure_partial_preserves_ocr`:**
```python
def test_process_route_pinyin_failure_partial_preserves_ocr() -> None:
    """When OCR succeeds but pinyin fails, partial response includes OCR data and no pinyin."""
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [RawOcrSegment(text="你好", language="zh", confidence=0.95)]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=FailingPinyinProvider(),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "partial"
    # OCR data preserved
    assert response.data is not None
    assert response.data.ocr is not None
    assert response.data.ocr.segments[0].text == "你好"
    # No pinyin in partial result
    assert response.data.pinyin is None
    # Warning carries the failure details
    assert response.warnings[0].category == "pinyin"
    assert isinstance(response.warnings[0].message, str)
    assert response.warnings[0].message
```

#### Frontend tests (`frontend/src/__tests__/features/process/upload-form.test.jsx`)

**Update `DEFAULT_PARTIAL_RESPONSE` fixture** to include warnings:
```javascript
const DEFAULT_PARTIAL_RESPONSE = {
  status: 'partial',
  request_id: 'req_partial',
  data: {
    ocr: {
      segments: [{ text: '你好', language: 'zh', confidence: 0.72 }]
    },
  },
  warnings: [
    {
      category: 'pinyin',
      code: 'pinyin_provider_unavailable',
      message: 'Pinyin generation is temporarily unavailable. Please try again.'
    }
  ]
}
```

Note: `data.pinyin` is removed from the fixture — a partial response from a pinyin failure has no pinyin data. Update the `applies partial state class when processing returns a partial result` test in the styling section — it uses `DEFAULT_PARTIAL_RESPONSE` and calls `screen.findByLabelText(/processing-partial/i)` which should still work.

**Add new test** (in the main `UploadForm` describe block):
```javascript
it('shows warning guidance when partial response includes pinyin failure warning', async () => {
  submitProcessRequest.mockResolvedValueOnce(DEFAULT_PARTIAL_RESPONSE)

  const user = userEvent.setup()
  renderWithClient(<UploadForm />)
  const form = screen.getByRole('form', { name: /process-upload-form/i })

  const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
  await user.upload(screen.getByLabelText(/upload image/i), file)
  await user.click(within(form).getByRole('button', { name: /submit/i }))

  expect(await screen.findByLabelText(/processing-partial/i)).toBeInTheDocument()
  expect(screen.getByLabelText(/processing-warnings/i)).toBeInTheDocument()
  expect(screen.getByText(/pinyin generation is temporarily unavailable/i)).toBeInTheDocument()
})
```

**Keep existing test `shows pinyin retry guidance when pinyin fails`** — it tests the error thrown path (HTTP errors, etc.) and remains valid.

### Architecture Compliance

- **Response envelope**: `status="partial"` with `data` + `warnings` conforms exactly to the architecture-defined partial envelope shape. No contract violation.
- **Error taxonomy**: `category="pinyin"` uses the shared taxonomy. `ProcessWarning.category` mirrors `ProcessError.category` — same field name, same taxonomy values.
- **Schema model validator**: `partial` requires `data` AND `warnings`, rejects `error`. New path satisfies all three constraints.
- **`response_model_exclude_none=True`** on the route: `data.pinyin=None` is excluded from serialized output. Client sees `data.ocr` but no `data.pinyin` key.
- **Service layer unchanged**: `pinyin_service.py` still raises `PinyinServiceError`. Only the route handler changes how it handles that error.
- **`snake_case`**: All fields (`category`, `code`, `message`) follow convention.

### File Structure Requirements

**Modified files:**
- `backend/app/schemas/process.py` — add `category` to `ProcessWarning`
- `backend/app/api/v1/process.py` — change `PinyinServiceError` handler to return `partial`; add `ProcessWarning` to import
- `backend/tests/contract/response_envelopes/test_process_envelopes.py` — update `assert_process_envelope`, `test_process_endpoint_partial_envelope_contract`, `test_process_endpoint_pinyin_error_envelope_contract`
- `backend/tests/integration/api_v1/test_process_route.py` — update `test_process_route_pinyin_failure_returns_typed_pinyin_error`; add `test_process_route_pinyin_failure_partial_preserves_ocr`
- `frontend/src/features/process/components/UploadForm.jsx` — add warnings display block
- `frontend/src/__tests__/features/process/upload-form.test.jsx` — update `DEFAULT_PARTIAL_RESPONSE`; add `shows warning guidance when partial response includes pinyin failure warning`

**Files NOT to touch:**
- `backend/app/services/pinyin_service.py` — `PinyinServiceError` raised the same way; no changes
- `backend/app/services/ocr_service.py` — no changes
- `backend/app/adapters/*` — no changes
- `backend/tests/unit/schemas/test_process_response_contract.py` — all existing `ProcessWarning` constructions work unchanged (default `category` kicks in); no breakage
- `backend/tests/unit/services/test_pinyin_service.py` — pinyin service behavior unchanged
- `frontend/src/lib/api-client.js` — `partial` already returned without throwing; no changes

### Previous Story Intelligence (2.2)

- **64 tests currently passing**: After story 2-3, expect ~67 backend tests (+1 updated existing, +2 new) and ~17 frontend tests (+1 new).
- **`logger.debug` for operational detail**: If adding debug logging for the partial path, use `logger.debug` pattern consistent with `ocr_service.py`.
- **`response_model_exclude_none=True`** on the route (confirmed in `process.py` line 103): `ProcessWarning.reason_code` would be excluded if None — but `ProcessWarning` doesn't have `reason_code`. Only `ProcessData.pinyin=None` is excluded in the partial response.
- **Import pattern in `process.py`**: The import line currently reads `from app.schemas.process import OcrData, ProcessData, ProcessError, ProcessResponse`. Add `ProcessWarning` to this import.
- **Contract test `assert_process_envelope`**: Already handles `partial` branch. Extending it to check warning fields is backward compatible since all existing partial tests pass a warnings list.

### Git Intelligence

- `48bf6a1` (latest): Story 2-2 complete — per-segment alignment in `pinyin_service.py`, `PinyinExecutionError` marks uncertain.
- `ab3e1d8`: Story 2-1 — OCR filtering with `ocr_no_chinese_text` vs `ocr_no_text_detected`.
- 64 tests baseline from Story 2-2.
- The `FailingPinyinProvider` class already exists in `test_process_route.py` (lines 25-27) — reuse it.

### Project Structure Notes

```
backend/
  app/
    schemas/
      process.py              ← MODIFY: add category to ProcessWarning; add ProcessWarning import in process.py
    api/
      v1/
        process.py            ← MODIFY: PinyinServiceError → partial; add ProcessWarning to import
  tests/
    contract/response_envelopes/
      test_process_envelopes.py  ← MODIFY: update assert_process_envelope, 2 test functions
    integration/api_v1/
      test_process_route.py      ← MODIFY: update 1 test, add 1 test

frontend/
  src/
    features/process/components/
      UploadForm.jsx             ← MODIFY: add warnings display block
    __tests__/features/process/
      upload-form.test.jsx       ← MODIFY: update DEFAULT_PARTIAL_RESPONSE, add 1 test
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-2.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#API-Response-Formats — partial envelope shape]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error-Handling-Patterns — category taxonomy]
- [Source: backend/app/schemas/process.py — ProcessWarning, ProcessError, ProcessResponse model validator]
- [Source: backend/app/api/v1/process.py — _build_process_response, current PinyinServiceError handler]
- [Source: backend/app/services/pinyin_service.py — PinyinServiceError definition]
- [Source: backend/tests/integration/api_v1/test_process_route.py — FailingPinyinProvider, existing pinyin failure test]
- [Source: backend/tests/contract/response_envelopes/test_process_envelopes.py — assert_process_envelope]
- [Source: frontend/src/features/process/components/UploadForm.jsx — recoveryGuidanceByCode, partial state handling]
- [Source: _bmad-output/implementation-artifacts/2-2-align-pinyin-output-with-source-text-segments.md — Dev Notes]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — all changes implemented cleanly on first pass per story spec.

### Completion Notes List

- Added `category: str = "processing"` to `ProcessWarning` (mirrors `ProcessError.category` pattern; default preserves backward compatibility)
- Changed `PinyinServiceError` handler in `_build_process_response` from `status="error"` to `status="partial"` — OCR segments passed as `data.ocr`, `data.pinyin=None`, warning carries typed error details
- Added `ProcessWarning` to import in `backend/app/api/v1/process.py`
- Added warnings display block in `UploadForm.jsx` after partial note, uses `recoveryGuidanceByCode` map for user-facing text
- Updated contract test `assert_process_envelope` partial branch to verify each warning has `category` and `code` keys
- Updated `test_process_endpoint_pinyin_error_envelope_contract` to expect `status="partial"` with `warnings[0].category="pinyin"`
- Updated `test_process_route_pinyin_failure_returns_typed_pinyin_error` to expect `status="partial"` with OCR data and no error
- Added `test_process_route_pinyin_failure_partial_preserves_ocr` verifying OCR preserved, pinyin absent, warning populated
- Updated `DEFAULT_PARTIAL_RESPONSE` fixture: removed `data.pinyin`, added `warnings` array with category/code/message
- Added frontend test `shows warning guidance when partial response includes pinyin failure warning`
- All 65 backend tests pass; `ruff check .` clean; all 26 frontend tests pass

### File List

- `backend/app/schemas/process.py`
- `backend/app/api/v1/process.py`
- `backend/tests/contract/response_envelopes/test_process_envelopes.py`
- `backend/tests/integration/api_v1/test_process_route.py`
- `frontend/src/features/process/components/UploadForm.jsx`
- `frontend/src/__tests__/features/process/upload-form.test.jsx`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-03-24: Story 2-3 created — partial result path when OCR succeeds but pinyin fails; typed warning category on ProcessWarning
- 2026-03-24: Story 2-3 implemented — ProcessWarning gains typed `category`; PinyinServiceError now returns partial+warnings instead of error; frontend displays warnings; focused backend and frontend tests pass
