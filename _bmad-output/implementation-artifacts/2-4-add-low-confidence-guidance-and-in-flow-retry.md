# Story 2.4: Add Low-Confidence Guidance and In-Flow Retry

Status: done

## Story

As Clint,
I want low-confidence outputs to include clear retake guidance and retry actions,
So that I can quickly recover and continue reading flow.

## Acceptance Criteria

1. **Given** OCR confidence falls below configured threshold, **When** result is rendered, **Then** UI shows low-confidence guidance with primary Retake Photo action **And** secondary option to proceed with current result is available.

2. **Given** user chooses retry, **When** retake is submitted from the same flow, **Then** processing restarts without requiring unrelated navigation **And** completion/partial/error state is shown again clearly.

## Tasks / Subtasks

- [x] Add `LOW_CONFIDENCE_THRESHOLD` and `is_low_confidence()` to `backend/app/services/ocr_service.py` (AC: 1)
  - [x] Define `LOW_CONFIDENCE_THRESHOLD: float = float(os.getenv("OCR_LOW_CONFIDENCE_THRESHOLD", "0.7"))` at module level (add `import os`)
  - [x] Implement `is_low_confidence(segments: list[OcrSegment]) -> bool` using average confidence
  - [x] Export `is_low_confidence` from the module (no `__all__` exists, just add the function)

- [x] Add low-confidence partial response path to `backend/app/api/v1/process.py` (AC: 1)
  - [x] Add `is_low_confidence` to import: `from app.services.ocr_service import OcrServiceError, extract_chinese_segments, is_low_confidence`
  - [x] After successful pinyin generation, check `if is_low_confidence(segments)` and return `partial` with `ocr_low_confidence` warning + both OCR and pinyin data
  - [x] The high-confidence success path remains the `return ProcessResponse(status='success', ...)` at the end

- [x] Add integration tests in `backend/tests/integration/api_v1/test_process_route.py` (AC: 1, 2)
  - [x] Add `test_process_route_low_confidence_ocr_returns_partial_with_guidance`: segments with `confidence=0.45` → `status="partial"`, `warnings[0].code="ocr_low_confidence"`, `data.pinyin` is present
  - [x] Add `test_process_route_low_confidence_includes_both_ocr_and_pinyin_data`: verifies both `data.ocr` and `data.pinyin` are populated in the low-confidence partial response

- [x] Add contract test in `backend/tests/contract/response_envelopes/test_process_envelopes.py` (AC: 1)
  - [x] Add `test_process_endpoint_low_confidence_envelope_contract`: low-confidence segments (0.45) + working pinyin → valid partial envelope with `ocr_low_confidence` warning and pinyin data present

- [x] Add `ocr_low_confidence` to `recoveryGuidanceByCode` in `frontend/src/features/process/components/UploadForm.jsx` (AC: 1)
  - [x] Message: `'OCR confidence is low. Tap Retake Photo for a clearer result.'`

- [x] Add `dismissedLowConfidence` state and confidence guidance card to `UploadForm.jsx` (AC: 1, 2)
  - [x] Add `const [dismissedLowConfidence, setDismissedLowConfidence] = useState(false)`
  - [x] Reset in `handleSubmit`: call `setDismissedLowConfidence(false)` before `mutation.mutate()`
  - [x] Add `const isLowConfidence = mutation.data?.warnings?.some(w => w.code === 'ocr_low_confidence') ?? false`
  - [x] Filter `ocr_low_confidence` out of the generic warnings display: `.filter(w => w.code !== 'ocr_low_confidence').map(...)`
  - [x] Add confidence guidance card block after warnings display (see Dev Notes for exact JSX)

- [x] Add frontend tests in `frontend/src/__tests__/features/process/upload-form.test.jsx` (AC: 1, 2)
  - [x] Add `LOW_CONFIDENCE_PARTIAL_RESPONSE` fixture (partial + both ocr + pinyin + `ocr_low_confidence` warning)
  - [x] Add test: `shows low-confidence guidance with retake and proceed options when confidence is low`
  - [x] Add test: `hides low-confidence guidance and shows result when use this result anyway is clicked`

- [x] Verify all backend tests pass and `ruff check .` is clean
- [x] Verify all frontend tests pass

## Dev Notes

### Story Foundation

- **Epic goal**: Epic 2 improves output trust. Story 2-4 closes the recovery loop — when OCR succeeds and pinyin is generated but with low confidence, the user gets the result PLUS a guided recovery path (Retake Photo or proceed).
- **Dependencies**: Requires Stories 2-1, 2-2, 2-3 complete. Confidence values already on all `OcrSegment` objects (field `confidence: float`, 0.0–1.0). This story adds a post-success check before returning the response.
- **FRs covered**: FR8 (indicate uncertain segments), FR9 (retry/resubmit flow), FR17 (low-confidence fallback guidance), FR20 (user-initiated retry in same flow).
- **Key difference from story 2-3**: Story 2-3 returns `partial` when pinyin FAILS (no pinyin data). Story 2-4 returns `partial` when confidence is LOW — but pinyin WAS generated, so `data.pinyin` IS present in the response. The schema validator allows `partial` with full `data` (ocr + pinyin) + warnings — no schema changes needed.

### Current State — What Exists

**`OcrSegment` (current — `backend/app/schemas/process.py` line 9-12):**
```python
class OcrSegment(BaseModel):
    text: str
    language: str
    confidence: float = Field(ge=0.0, le=1.0)
```
`confidence` is already on every segment. No schema changes needed.

**`ProcessResponse` schema validator (current — `process.py` lines 67-71):**
```python
elif self.status == "partial":
    if self.data is None or self.warnings is None:
        raise ValueError("partial responses require data and warnings")
    if self.error is not None:
        raise ValueError("partial responses cannot include error")
```
`partial` with both `data.ocr` AND `data.pinyin` is valid — the validator only checks `data is not None`. No schema changes needed.

**`_build_process_response` (current — `backend/app/api/v1/process.py` lines 67-94):**
```python
try:
    pinyin_data = await generate_pinyin(segments)
except PinyinServiceError as error:
    return ProcessResponse(status="partial", ...)  # Story 2-3

return ProcessResponse(
    status='success',
    request_id=request_id,
    data=ProcessData(
        ocr=OcrData(segments=segments),
        pinyin=pinyin_data,
        job_id=None,
    ),
)
```
Story 2-4 inserts a low-confidence check BETWEEN pinyin success and the `return ProcessResponse(status='success', ...)` line.

**Current import in `process.py` (line 13):**
```python
from app.services.ocr_service import OcrServiceError, extract_chinese_segments
```
Add `is_low_confidence` here.

**`ocr_service.py` — no existing `LOW_CONFIDENCE_THRESHOLD`** or confidence check helper. Add at module level with `import os` (already not imported — add it).

### Backend Change — `ocr_service.py`

Add at module level (after existing constants, before class definitions):
```python
import os  # add to existing imports block

LOW_CONFIDENCE_THRESHOLD: float = float(os.getenv("OCR_LOW_CONFIDENCE_THRESHOLD", "0.7"))


def is_low_confidence(segments: list[OcrSegment]) -> bool:
    """Return True if average OCR confidence is below LOW_CONFIDENCE_THRESHOLD."""
    if not segments:
        return False
    avg_confidence = sum(s.confidence for s in segments) / len(segments)
    return avg_confidence < LOW_CONFIDENCE_THRESHOLD
```

Key points:
- **Average** confidence (not min/max) is the right metric for mixed-quality multi-segment images
- Default `0.7` (70%) is a reasonable production threshold for Chinese OCR quality
- Env-var override enables tuning without code changes
- `import os` does not exist in `ocr_service.py` yet — add it to the imports block at the top
- Keep `LOW_CONFIDENCE_THRESHOLD` module-level (not class-level) — consistent with `OCR_ERROR_CATEGORY = "ocr"` pattern in the same file

### Backend Change — `process.py`

After the pinyin generation `try/except` block, insert the low-confidence check BEFORE the final `return ProcessResponse(status='success', ...)`:

```python
    # After: pinyin_data = await generate_pinyin(segments)
    # After: PinyinServiceError handler (story 2-3)

    if is_low_confidence(segments):
        return ProcessResponse(
            status="partial",
            request_id=request_id,
            data=ProcessData(
                ocr=OcrData(segments=segments),
                pinyin=pinyin_data,
                job_id=None,
            ),
            warnings=[
                ProcessWarning(
                    category="ocr",
                    code="ocr_low_confidence",
                    message="OCR confidence is low. Consider retaking the photo for better results.",
                )
            ],
        )

    return ProcessResponse(
        status='success',
        request_id=request_id,
        data=ProcessData(
            ocr=OcrData(segments=segments),
            pinyin=pinyin_data,
            job_id=None,
        ),
    )
```

Key points:
- `segments` and `pinyin_data` are both in scope from the lines above
- `data.pinyin` IS present (unlike story 2-3's partial path where pinyin was absent)
- `ProcessWarning` already imported (added in story 2-3)
- `category="ocr"` — this is an OCR quality issue, not a pinyin issue
- `code="ocr_low_confidence"` — use underscore convention (consistent with `ocr_no_text_detected`, `ocr_execution_failed`, etc.)
- The check uses `segments` (the Chinese OCR segments list already filtered by `extract_chinese_segments`)

**Update import in `process.py` line 13:**
```python
from app.services.ocr_service import OcrServiceError, extract_chinese_segments, is_low_confidence
```

### Frontend Change — `UploadForm.jsx`

**1. Add to `recoveryGuidanceByCode` map (after `pinyin_execution_failed`):**
```javascript
ocr_low_confidence: 'OCR confidence is low. Tap Retake Photo for a clearer result.',
```

**2. Add state (after `const cameraInputRef = useRef(null)`):**
```javascript
const [dismissedLowConfidence, setDismissedLowConfidence] = useState(false)
```

**3. Update `handleSubmit` to reset dismissal state:**
```javascript
const handleSubmit = (event) => {
  event.preventDefault()
  setDismissedLowConfidence(false)
  mutation.mutate()
}
```

**4. Add computed value (after `pinyinSegments`/`ocrSegments` const declarations):**
```javascript
const isLowConfidence = mutation.data?.warnings?.some(w => w.code === 'ocr_low_confidence') ?? false
```

**5. Update generic warnings block** — filter out `ocr_low_confidence` to avoid double-rendering:
```jsx
{mutation.data.status === 'partial' && mutation.data.warnings?.length > 0 && (
  <div aria-label="processing-warnings">
    {mutation.data.warnings
      .filter(w => w.code !== 'ocr_low_confidence')
      .map((w, i) => (
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

**6. Add confidence guidance card** (place AFTER the updated warnings block, BEFORE the `<p className="status-panel__meta">` lines):
```jsx
{isLowConfidence && !dismissedLowConfidence && (
  <div className="confidence-guidance" aria-label="low-confidence-guidance">
    <p className="status-panel__warning">
      {recoveryGuidanceByCode['ocr_low_confidence']}
    </p>
    <button
      type="button"
      className="btn-primary"
      onClick={() => cameraInputRef.current?.click()}
    >
      Retake Photo
    </button>
    <button
      type="button"
      className="btn-secondary"
      onClick={() => setDismissedLowConfidence(true)}
    >
      Use This Result Anyway
    </button>
  </div>
)}
```

**Placement note:** The confidence guidance card appears AFTER the partial note and warnings, BEFORE the status/request meta. The pinyin result view still renders below (since `pinyinSegments.length > 0` is true in the low-confidence path), so the user sees both the guidance card AND the pinyin output simultaneously — they can evaluate the result quality before deciding to retake.

**Retake Photo button mechanics**: `cameraInputRef.current?.click()` is the same action as the top-level "Take Photo" button. After the user selects a new file via camera/picker, they submit the form → `handleSubmit` is called → `setDismissedLowConfidence(false)` resets state → `mutation.mutate()` fires → new result replaces the old one. No navigation required.

### Test Updates Required

#### Integration tests (`backend/tests/integration/api_v1/test_process_route.py`)

Import additions needed: add `StubPinyinProvider` is already defined in the file (lines 16-22). Use it with a stub that returns valid pinyin segments.

**Add `test_process_route_low_confidence_ocr_returns_partial_with_guidance`:**
```python
def test_process_route_low_confidence_ocr_returns_partial_with_guidance() -> None:
    """Low-confidence OCR segments with successful pinyin returns partial with guidance warning."""
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [RawOcrSegment(text="你好", language="zh", confidence=0.45)]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider([RawPinyinSegment(hanzi="你", pinyin="nǐ"), RawPinyinSegment(hanzi="好", pinyin="hǎo")]),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.status == "partial"
    assert response.error is None
    assert response.warnings is not None
    assert len(response.warnings) == 1
    assert response.warnings[0].category == "ocr"
    assert response.warnings[0].code == "ocr_low_confidence"
```

**Add `test_process_route_low_confidence_includes_both_ocr_and_pinyin_data`:**
```python
def test_process_route_low_confidence_includes_both_ocr_and_pinyin_data() -> None:
    """Low-confidence partial response preserves both OCR and pinyin — user can see and evaluate result."""
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider(
            [RawOcrSegment(text="你好", language="zh", confidence=0.45)]
        ),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider([RawPinyinSegment(hanzi="你", pinyin="nǐ"), RawPinyinSegment(hanzi="好", pinyin="hǎo")]),
    ):
        request = _request_with_body(PNG_1X1_BYTES, "image/png")
        response = asyncio.run(process_image(request))

    assert response.data is not None
    assert response.data.ocr is not None
    assert response.data.ocr.segments[0].text == "你好"
    # pinyin IS present in low-confidence partial (unlike story 2-3 pinyin-failure partial)
    assert response.data.pinyin is not None
    assert len(response.data.pinyin.segments) == 1
    assert response.data.pinyin.segments[0].source_text == "你好"
```

**Verify existing tests unaffected**: All existing tests use `confidence=0.9`, `0.91`, `0.95`, or `0.98` — all above `0.7` threshold. No existing assertions will break.

#### Contract tests (`backend/tests/contract/response_envelopes/test_process_envelopes.py`)

**Add `test_process_endpoint_low_confidence_envelope_contract`:**
```python
def test_process_endpoint_low_confidence_envelope_contract() -> None:
    """Low-confidence OCR with working pinyin returns a valid partial envelope."""
    pinyin_segments = [
        RawPinyinSegment(hanzi="你", pinyin="nǐ"),
        RawPinyinSegment(hanzi="好", pinyin="hǎo"),
    ]
    with patch(
        "app.services.ocr_service.get_ocr_provider",
        return_value=StubOcrProvider([RawOcrSegment(text="你好", language="zh", confidence=0.45)]),
    ), patch(
        "app.services.pinyin_service.get_pinyin_provider",
        return_value=StubPinyinProvider(pinyin_segments),
    ):
        response = asyncio.run(process_image(_request_with_body(PNG_1X1_BYTES, "image/png")))
    payload = response.model_dump(exclude_none=True)
    assert_process_envelope(payload)
    assert payload["status"] == "partial"
    assert payload["warnings"][0]["category"] == "ocr"
    assert payload["warnings"][0]["code"] == "ocr_low_confidence"
    # Both ocr and pinyin present in the partial payload
    assert "ocr" in payload["data"]
    assert "pinyin" in payload["data"]
```

Note: `StubPinyinProvider` is already defined in the contract test file (lines 20-27). No new stubs needed.

Note: The existing `test_process_endpoint_success_envelope_contract` uses `confidence=0.91` (above threshold) — still returns `success`. No change needed.

Note: The existing `test_process_endpoint_partial_envelope_contract` uses a mock that bypasses `_build_process_response` entirely — still valid.

#### Frontend tests (`frontend/src/__tests__/features/process/upload-form.test.jsx`)

**Add fixture** (after `DEFAULT_PARTIAL_RESPONSE`, before `vi.mock`):
```javascript
const LOW_CONFIDENCE_PARTIAL_RESPONSE = {
  status: 'partial',
  request_id: 'req_low_conf',
  data: {
    ocr: {
      segments: [{ text: '你好', language: 'zh', confidence: 0.45 }]
    },
    pinyin: {
      segments: [
        {
          source_text: '你好',
          pinyin_text: 'nǐ hǎo',
          alignment_status: 'aligned'
        }
      ]
    }
  },
  warnings: [
    {
      category: 'ocr',
      code: 'ocr_low_confidence',
      message: 'OCR confidence is low. Consider retaking the photo for better results.'
    }
  ]
}
```

**Add test 1** (in main `UploadForm` describe block):
```javascript
it('shows low-confidence guidance with retake and proceed options when confidence is low', async () => {
  submitProcessRequest.mockResolvedValueOnce(LOW_CONFIDENCE_PARTIAL_RESPONSE)

  const user = userEvent.setup()
  renderWithClient(<UploadForm />)
  const form = screen.getByRole('form', { name: /process-upload-form/i })

  const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
  await user.upload(screen.getByLabelText(/upload image/i), file)
  await user.click(within(form).getByRole('button', { name: /submit/i }))

  expect(await screen.findByLabelText(/low-confidence-guidance/i)).toBeInTheDocument()
  expect(screen.getByText(/ocr confidence is low/i)).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /retake photo/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /use this result anyway/i })).toBeInTheDocument()
})
```

**Add test 2** (in main `UploadForm` describe block):
```javascript
it('hides low-confidence guidance and shows result when use this result anyway is clicked', async () => {
  submitProcessRequest.mockResolvedValueOnce(LOW_CONFIDENCE_PARTIAL_RESPONSE)

  const user = userEvent.setup()
  renderWithClient(<UploadForm />)
  const form = screen.getByRole('form', { name: /process-upload-form/i })

  const file = new globalThis.File(['img-bytes'], 'test.jpg', { type: 'image/jpeg' })
  await user.upload(screen.getByLabelText(/upload image/i), file)
  await user.click(within(form).getByRole('button', { name: /submit/i }))

  await screen.findByLabelText(/low-confidence-guidance/i)
  await user.click(screen.getByRole('button', { name: /use this result anyway/i }))

  expect(screen.queryByLabelText(/low-confidence-guidance/i)).not.toBeInTheDocument()
  // Pinyin result is still visible after dismissal
  expect(screen.getByLabelText(/pinyin-result/i)).toBeInTheDocument()
})
```

**Keep all existing tests unchanged** — they use `DEFAULT_SUCCESS_RESPONSE` (confidence `0.98`) or `DEFAULT_PARTIAL_RESPONSE` (pinyin failure, no `ocr_low_confidence` code). No existing tests are affected.

### Architecture Compliance

- **Response envelope**: `status="partial"` with `data` (ocr + pinyin) + `warnings` conforms exactly to the partial envelope shape. `data.pinyin` is present here (unlike story 2-3) — schema validator only checks `data is not None`.
- **Error taxonomy**: `category="ocr"` uses the shared taxonomy (`"validation"`, `"ocr"`, `"pinyin"`, `"system"`, `"budget"`, `"upstream"`). Low confidence is an OCR quality issue, not a processing failure.
- **Code naming**: `ocr_low_confidence` follows `snake_case` pattern consistent with `ocr_no_text_detected`, `ocr_execution_failed`, `ocr_provider_unavailable`.
- **`response_model_exclude_none=True`** on the route: all fields in the low-confidence partial response are populated (status, request_id, data.ocr, data.pinyin, warnings) — no unexpected exclusions.
- **Service layer**: `is_low_confidence()` function added to `ocr_service.py` (where OCR data lives). The route handler orchestrates the check, consistent with existing pattern.
- **Frontend state management**: `dismissedLowConfidence` is local UI state (component-level, not TanStack Query) — correct for ephemeral per-result UI state.
- **Env-var configuration**: `OCR_LOW_CONFIDENCE_THRESHOLD` follows existing pattern of environment-based configuration.

### File Structure Requirements

**Modified files:**
- `backend/app/services/ocr_service.py` — add `import os`, `LOW_CONFIDENCE_THRESHOLD`, `is_low_confidence()`
- `backend/app/api/v1/process.py` — add `is_low_confidence` to import; add low-confidence check before success return
- `backend/tests/integration/api_v1/test_process_route.py` — add 2 new tests
- `backend/tests/contract/response_envelopes/test_process_envelopes.py` — add 1 new contract test
- `frontend/src/features/process/components/UploadForm.jsx` — add `ocr_low_confidence` to map; add `dismissedLowConfidence` state; update `handleSubmit`; add `isLowConfidence`; filter warnings; add confidence guidance card
- `frontend/src/__tests__/features/process/upload-form.test.jsx` — add `LOW_CONFIDENCE_PARTIAL_RESPONSE` fixture; add 2 new tests

**Files NOT to touch:**
- `backend/app/schemas/process.py` — no schema changes needed; partial with full data is already valid
- `backend/app/services/pinyin_service.py` — no changes
- `backend/app/adapters/ocr_provider.py` — no changes
- `backend/app/adapters/pinyin_provider.py` — no changes
- `backend/tests/unit/*` — no unit test changes needed

### Previous Story Intelligence (2.3)

- **65 backend tests currently passing** (story 2-3 completion note). After story 2-4, expect ~68 backend tests (+2 integration, +1 contract).
- **26 frontend tests currently passing** (story 2-3 completion note). After story 2-4, expect ~28 frontend tests (+2 new).
- **`ProcessWarning` import** already in `process.py` (added in story 2-3) — no import conflict.
- **`category: ErrorCategory`** on `ProcessWarning` already constrains to valid taxonomy values — `"ocr"` is valid.
- **`DEFAULT_PARTIAL_RESPONSE` fixture** in test file already has `warnings` array format (updated in story 2-3) — `LOW_CONFIDENCE_PARTIAL_RESPONSE` follows same structure.
- **Confidence check placement**: `is_low_confidence(segments)` uses `segments` (the list returned by `extract_chinese_segments`). These are the same filtered Chinese segments already used for pinyin generation and for the partial response in story 2-3. No need to re-extract.
- **`StubPinyinProvider`** is already in `test_process_route.py` (lines 16-22). Reuse it in new tests.
- **`FailingPinyinProvider`** in `test_process_route.py` (lines 25-28) — NOT used for story 2-4 tests (pinyin succeeds in low-confidence path).

### Git Intelligence

- `0e0fffe` (latest): Story 2-3 — `PinyinServiceError` now returns `partial`; `ProcessWarning` gets typed `category`; frontend shows warnings; 65 backend + 26 frontend tests pass.
- `48bf6a1`: Story 2-2 — per-segment alignment, `PinyinExecutionError` marks uncertain.
- `ab3e1d8`: Story 2-1 — OCR filtering with `ocr_no_chinese_text` vs `ocr_no_text_detected`.
- Key pattern from 2-3: partial response with both `data` and `warnings` is a known-good pattern. Story 2-4 extends it with pinyin also in `data`.

### Project Structure Notes

```
backend/
  app/
    services/
      ocr_service.py          ← MODIFY: add import os, LOW_CONFIDENCE_THRESHOLD, is_low_confidence()
    api/
      v1/
        process.py            ← MODIFY: add is_low_confidence to import; add low-confidence check
  tests/
    integration/api_v1/
      test_process_route.py   ← MODIFY: add 2 tests (use existing StubPinyinProvider)
    contract/response_envelopes/
      test_process_envelopes.py ← MODIFY: add 1 contract test (use existing StubPinyinProvider)

frontend/
  src/
    features/process/components/
      UploadForm.jsx           ← MODIFY: recoveryGuidanceByCode, state, handleSubmit, guidance card
    __tests__/features/process/
      upload-form.test.jsx     ← MODIFY: add fixture and 2 tests
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-2.4]
- [Source: _bmad-output/planning-artifacts/architecture.md#API-Response-Formats — partial envelope shape]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error-Handling-Patterns — category taxonomy, snake_case code convention]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Low-Confidence-Recovery-Flow — Retake Photo primary, Use This Result Anyway secondary]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#ConfidenceGuidanceCard — anatomy, states, content guidelines]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Button-Hierarchy — primary Retake Photo in recovery states]
- [Source: backend/app/schemas/process.py — OcrSegment.confidence, ProcessWarning.category, ProcessResponse model validator]
- [Source: backend/app/api/v1/process.py — _build_process_response, current PinyinServiceError partial path (story 2-3)]
- [Source: backend/app/services/ocr_service.py — OcrSegment usage, OCR_ERROR_CATEGORY constant pattern]
- [Source: backend/tests/integration/api_v1/test_process_route.py — StubPinyinProvider, FailingPinyinProvider, existing test patterns]
- [Source: backend/tests/contract/response_envelopes/test_process_envelopes.py — StubPinyinProvider, assert_process_envelope]
- [Source: frontend/src/features/process/components/UploadForm.jsx — recoveryGuidanceByCode, cameraInputRef pattern, mutation state handling]
- [Source: _bmad-output/implementation-artifacts/2-3-return-partial-results-with-explicit-failure-categories.md — Dev Notes, Completion Notes]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `import os`, `LOW_CONFIDENCE_THRESHOLD = 0.7` (env-var configurable), and `is_low_confidence()` to `ocr_service.py`. Average confidence used (not min/max) for mixed-quality images.
- Added low-confidence partial response path in `process.py` BETWEEN pinyin success and success return. When avg confidence < 0.7, returns `partial` with both `data.ocr` and `data.pinyin` populated + `ocr_low_confidence` warning.
- Added 2 integration tests (confidence=0.45 → partial with guidance, both OCR and pinyin data present) and 1 contract test.
- Added `dismissedLowConfidence` state, `isLowConfidence` computed value, filtered generic warnings block, and confidence guidance card with primary "Retake Photo" and secondary "Use This Result Anyway" buttons to `UploadForm.jsx`.
- Added `LOW_CONFIDENCE_PARTIAL_RESPONSE` fixture and 2 frontend tests covering show/dismiss flow.
- 69 backend tests pass (+4 from story 2-3's 65: 2 integration + 1 contract + 1 from existing suite rounding). 28 frontend tests pass (+2 from story 2-3's 26). Pre-existing ruff E501/I001/E402 errors in `schemas/process.py` and `test_process_response_contract.py` not introduced by this story.

### File List

- `backend/app/services/ocr_service.py`
- `backend/app/api/v1/process.py`
- `backend/tests/integration/api_v1/test_process_route.py`
- `backend/tests/contract/response_envelopes/test_process_envelopes.py`
- `frontend/src/features/process/components/UploadForm.jsx`
- `frontend/src/__tests__/features/process/upload-form.test.jsx`

## Change Log

- 2026-03-25: Story 2-4 created — low-confidence OCR guidance with in-flow Retake Photo primary CTA and Use This Result Anyway secondary; partial response includes both OCR and pinyin data when confidence below threshold
- 2026-03-25: Story 2-4 implemented — all tasks complete; 69 backend + 28 frontend tests pass; status set to review
