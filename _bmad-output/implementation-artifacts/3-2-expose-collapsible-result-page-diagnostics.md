# Story 3.2: Expose Collapsible Result-Page Diagnostics

Status: done

## Story

As Clint,
I want diagnostics available behind a Show Details panel,
So that I can inspect OCR/confidence/timing/trace only when needed.

## Acceptance Criteria

1. **Given** a result is displayed, **When** I do not expand details, **Then** pinyin output remains primary and unobstructed **And** diagnostics stay hidden by default.

2. **Given** I expand Show Details, **When** panel opens, **Then** raw OCR output, confidence indicators, request timing, and trace summary are visible **And** collapsing restores quiet reading-focused view.

## Tasks / Subtasks

- [x] Create `frontend/src/features/process/components/DiagnosticsPanel.jsx` (AC: 1, 2)
  - [x] Accept `diagnostics` prop (DiagnosticsPayload from API, may be null/undefined for error paths) and `ocrSegments` prop (from `data.ocr.segments`, may be empty)
  - [x] Render collapsed `<details className="details-section">` with `<summary>Show Details</summary>` — collapsed by default (no `open` attribute), `aria-label="diagnostics-panel"` (used for test targeting; note: this overrides the AT-computed accessible name to "diagnostics-panel" — the summary "Show Details" remains the visible toggle label)
  - [x] Inside expanded panel: OCR section — iterate `ocrSegments`, show `text`, `language`, `confidence` formatted as `Math.round(confidence * 100)%`
  - [x] Inside expanded panel: Timing section — show only when `diagnostics` is provided; display `total_ms`, `ocr_ms`, `pinyin_ms` each rounded to 1 decimal place with `ms` suffix; label section clearly (e.g. "Timing")
  - [x] Inside expanded panel: Trace section — show only when `diagnostics` is provided; list `trace.steps` each with `step` name and `status` value; label section "Trace"
  - [x] Return `null` (render nothing) when both `diagnostics` is null/undefined and `ocrSegments` is empty

- [x] Update `frontend/src/features/process/components/UploadForm.jsx` — replace existing OCR `<details>` with DiagnosticsPanel (AC: 1, 2)
  - [x] Import `DiagnosticsPanel` from `'./DiagnosticsPanel'`
  - [x] Replace the existing `{ocrSegments.length > 0 && (<details className="details-section">...</details>)}` block with `<DiagnosticsPanel diagnostics={mutation.data?.diagnostics} ocrSegments={ocrSegments} />`
  - [x] Remove the `formatConfidence` helper function from UploadForm (it moves to DiagnosticsPanel)
  - [x] Placement: DiagnosticsPanel renders inside the result-view container, below the pinyin/image block — it replaces the old OCR `<details>` in exactly the same DOM position within that container

- [x] Write frontend tests in `frontend/src/__tests__/features/process/diagnostics-panel.test.jsx` (AC: 1, 2)
  - [x] Collapsed by default: `details` element has no `open` attribute, summary text is "Show Details"
  - [x] OCR section: text, language, and confidence percentage visible when panel expanded (with `ocrSegments` populated)
  - [x] Timing section: `total_ms`, `ocr_ms`, `pinyin_ms` visible formatted as `Xms` after expand (with `diagnostics` provided)
  - [x] Trace section: step names and statuses visible after expand (with `diagnostics` provided)
  - [x] Timing/Trace absent when `diagnostics` prop is null
  - [x] Renders nothing (returns null) when both `diagnostics` is null and `ocrSegments` is empty
  - [x] `details` element has `details-section` class (CSS hook)
  - [x] Timing/Trace visible when `diagnostics` provided but `ocrSegments` is empty (OCR section absent)

- [x] Verify all existing frontend tests pass unchanged (AC: 1)
  - [x] The existing UploadForm test "shows OCR details in secondary collapsed section" must still pass — DiagnosticsPanel is a `<details>` with same class and same OCR content
  - [x] The existing UploadForm test "renders OCR details in a collapsed details element with semantic class" must still pass

- [x] Run `npm test` (from frontend directory) and confirm all tests pass

## Dev Notes

### Story Foundation

- **Epic goal**: Epic 3 builds the diagnostics/observability layer. Story 3-1 established the backend `DiagnosticsPayload` schema and wired it into `success` and `partial` process responses. Story 3-2 is purely frontend — expose that diagnostics data behind a `Show Details` toggle on the result page.
- **FRs covered**: FR21 (collapsible diagnostics panel), FR22 (raw OCR visibility), FR23 (confidence indicators), FR24 (per-request timing), FR25 (trace data)
- **No backend changes** — this story is frontend only.

### Current State — What Exists

**`frontend/src/features/process/components/UploadForm.jsx`** — already has:
- A basic `<details className="details-section">` block that shows OCR segments (text + language + confidence)
- `formatConfidence(confidence)` helper: `Math.round(confidence * 100) + '%'`
- `ocrSegments` derived from `mutation.data?.data?.ocr?.segments || []`
- No timing or trace data is currently shown anywhere
- `mutation.data?.diagnostics` is available from the API response but is NOT currently read or displayed

**Existing OCR `<details>` block to replace (UploadForm.jsx lines ~217–230):**
```jsx
{/* Secondary: raw OCR details */}
{ocrSegments.length > 0 && (
  <details className="details-section">
    <summary>Extracted Text (OCR details)</summary>
    <ul>
      {ocrSegments.map((segment, index) => (
        <li key={`${segment.text}-${index}`}>
          <span>{segment.text}</span>{' '}
          <span>({segment.language}, {formatConfidence(segment.confidence)})</span>
        </li>
      ))}
    </ul>
  </details>
)}
```

**Backend `DiagnosticsPayload` shape (from `backend/app/schemas/diagnostics.py`):**
```python
class UploadContext(BaseModel):
    content_type: str
    file_size_bytes: int = Field(..., ge=0)

class TimingInfo(BaseModel):
    total_ms: float = Field(..., ge=0)
    ocr_ms: float = Field(..., ge=0)
    pinyin_ms: float = Field(..., ge=0)   # NOTE: all three are REQUIRED (not optional) after schema hardening

class TraceStep(BaseModel):
    step: Literal["ocr", "pinyin", "confidence_check"]
    status: Literal["ok", "skipped", "failed"]

class TraceInfo(BaseModel):
    steps: list[TraceStep]

class DiagnosticsPayload(BaseModel):
    upload_context: UploadContext
    timing: TimingInfo
    trace: TraceInfo
```

**Important**: `TimingInfo.ocr_ms` and `pinyin_ms` are **required** fields (not optional) per Story 3-1 schema hardening. When `diagnostics` is present, all three timing fields will always exist.

**JSON shape the frontend receives** (success/partial envelopes):
```json
{
  "status": "success",
  "request_id": "...",
  "data": { "ocr": { "segments": [...] }, "pinyin": { "segments": [...] } },
  "diagnostics": {
    "upload_context": { "content_type": "image/jpeg", "file_size_bytes": 12345 },
    "timing": { "total_ms": 823.4, "ocr_ms": 612.1, "pinyin_ms": 98.7 },
    "trace": {
      "steps": [
        { "step": "ocr", "status": "ok" },
        { "step": "pinyin", "status": "ok" },
        { "step": "confidence_check", "status": "ok" }
      ]
    }
  }
}
```

Error envelope: **no `diagnostics` field** (excluded by architecture spec).

### DiagnosticsPanel Component Spec

**File**: `frontend/src/features/process/components/DiagnosticsPanel.jsx`

**Props**:
- `diagnostics` — the `diagnostics` object from API response, or `null`/`undefined` (error paths)
- `ocrSegments` — array of `{ text, language, confidence }` from `data.ocr.segments`, defaults to `[]`

**Render contract**:
- Returns `null` when both `diagnostics` is falsy AND `ocrSegments` is empty — prevents empty panel
- Uses existing `<details className="details-section">` pattern (same CSS hook as the existing OCR section — ensures existing tests and styles continue to work)
- `aria-label="diagnostics-panel"` on the `<details>` element for test selection. Note: this overrides the element's AT-computed accessible name from the `<summary>` text to "diagnostics-panel". This is an intentional trade-off: the `<summary>Show Details</summary>` remains the visible and keyboard-accessible toggle label.
- Summary text: `"Show Details"` (matches UX spec `DetailDisclosurePanel` naming)
- OCR section: always render when `ocrSegments.length > 0`, under a visual heading
- Timing section: only when `diagnostics` is present
- Trace section: only when `diagnostics` is present

**Timing format**: Use `(ms).toFixed(1) + 'ms'` for display — e.g. `"823.4ms"`. Labels: `Total:`, `OCR:`, `Pinyin:`.

**Trace format**: List each step as `"step: status"` — e.g. `"ocr: ok"`, `"confidence_check: failed"`. Simple text is sufficient.

**Reference implementation sketch**:
```jsx
export default function DiagnosticsPanel({ diagnostics, ocrSegments = [] }) {
  if (!diagnostics && ocrSegments.length === 0) return null

  return (
    <details className="details-section" aria-label="diagnostics-panel">
      <summary>Show Details</summary>

      {ocrSegments.length > 0 && (
        <div>
          <h4>OCR Details</h4>
          <ul>
            {ocrSegments.map((segment, index) => (
              <li key={`${segment.text}-${index}`}>
                <span>{segment.text}</span>{' '}
                <span>({segment.language}, {Math.round(segment.confidence * 100)}%)</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {diagnostics && (
        <>
          <div>
            <h4>Timing</h4>
            <ul>
              <li>Total: {diagnostics.timing.total_ms.toFixed(1)}ms</li>
              <li>OCR: {diagnostics.timing.ocr_ms.toFixed(1)}ms</li>
              <li>Pinyin: {diagnostics.timing.pinyin_ms.toFixed(1)}ms</li>
            </ul>
          </div>
          <div>
            <h4>Trace</h4>
            <ul>
              {diagnostics.trace.steps.map((step, index) => (
                <li key={`${step.step}-${index}`}>{step.step}: {step.status}</li>
              ))}
            </ul>
          </div>
        </>
      )}
    </details>
  )
}
```

### UX Requirements (from UX Design Spec)

**`DetailDisclosurePanel` component spec**:
- Purpose: Optional technical learning mode without polluting default flow
- Collapsed by default (MVP)
- Toggle header with grouped sections: OCR text, confidence values, timing, trace summary
- Accessible keyboard/touch toggle semantics
- Must not disrupt pinyin reading view when collapsed

**Summary label**: "Show Details" (matching UX spec for the toggle name)

**Progressive disclosure principle**: existing pinyin result and image remain visible and dominant; diagnostics panel sits below the pinyin/image content inside the result-view container.

### Test File: `diagnostics-panel.test.jsx`

**Pattern**: Mirrors existing `upload-form.test.jsx` — import `@testing-library/react`, `vitest`, and `userEvent`.

**Test fixture** (the panel is pure-UI, no API calls needed — pass props directly):
```js
const MOCK_DIAGNOSTICS = {
  upload_context: { content_type: 'image/png', file_size_bytes: 4096 },
  timing: { total_ms: 823.4, ocr_ms: 612.1, pinyin_ms: 98.7 },
  trace: {
    steps: [
      { step: 'ocr', status: 'ok' },
      { step: 'pinyin', status: 'ok' },
      { step: 'confidence_check', status: 'ok' },
    ]
  }
}

const MOCK_OCR_SEGMENTS = [
  { text: '你好', language: 'zh', confidence: 0.98 }
]
```

**No QueryClientProvider needed** — DiagnosticsPanel is a pure presentational component (no hooks, no mutations).

**Render helper**: `render(<DiagnosticsPanel diagnostics={...} ocrSegments={...} />)` directly.

**Required behaviours to test** (test names are descriptive, not prescriptive):

- Collapsed by default: `details[aria-label="diagnostics-panel"]` exists, does NOT have `open` attribute, summary shows "Show Details"
- OCR section visible after expand (render with `MOCK_OCR_SEGMENTS`): `screen.getByText('你好')`, `screen.getByText(/zh, 98%/i)`
- Timing section visible after expand (render with `MOCK_DIAGNOSTICS + MOCK_OCR_SEGMENTS`): `/823\.4ms/i`, `/612\.1ms/i`, `/98\.7ms/i`
- Trace section visible after expand: `/ocr: ok/i`, `/confidence_check: ok/i`
- Timing/Trace absent when `diagnostics={null}` (but `ocrSegments` provided): `queryByText('Timing')` null, `queryByText('Trace')` null
- Returns null when `diagnostics={null}` and `ocrSegments=[]`: `document.querySelector('details')` null
- Has `details-section` class
- Timing/Trace visible when `diagnostics=MOCK_DIAGNOSTICS` and `ocrSegments=[]`: OCR section absent, Timing and Trace sections present

### Existing UploadForm Tests — No Modifications Needed

The existing tests in `upload-form.test.jsx` continue to pass because:
- DiagnosticsPanel renders a `<details className="details-section">` — same element and class as the old OCR section
- `DEFAULT_SUCCESS_RESPONSE` fixture has no `diagnostics` field — DiagnosticsPanel will still render (ocrSegments is not empty) but timing/trace sections are hidden
- Test at line 213 (`shows OCR details in secondary collapsed section`) tests `document.querySelector('details')` and `within(detailsEl).getByText(/你好/)` — still finds the details element and OCR content
- Test at line 464 (`renders OCR details in a collapsed details element with semantic class`) checks `details-section` class — still applies

**One behaviour difference**: The summary text changes from `"Extracted Text (OCR details)"` to `"Show Details"`. The existing test checks `screen.getByText(/extracted text/i)` — this **WILL BREAK**.

**Fix required in `upload-form.test.jsx`**: Update line 224:
```js
// BEFORE:
expect(screen.getByText(/extracted text/i)).toBeInTheDocument()
// AFTER:
expect(screen.getByText(/show details/i)).toBeInTheDocument()
```

Also update line 490:
```js
// BEFORE:
expect(screen.getByText(/extracted text/i)).toBeInTheDocument()
// AFTER:
expect(screen.getByText(/show details/i)).toBeInTheDocument()
```

These are the only required changes to `upload-form.test.jsx`.

### Architecture Compliance

- **Component location**: `frontend/src/features/process/components/DiagnosticsPanel.jsx` — correct per architecture spec `frontend/src/features/process/components/` directory
- **PascalCase filename**: `DiagnosticsPanel.jsx` — matches architecture convention
- **No backend changes**: error envelope rightly has no diagnostics field; architecture spec is clear
- **`response_model_exclude_none=True`** on backend route: `diagnostics` is only present in success/partial JSON; frontend handles `null`/`undefined` gracefully
- **Progressive disclosure**: panel uses native `<details>/<summary>` — matches existing pattern in codebase, keyboard accessible, no JS toggle needed
- **No new dependencies**: pure React component using existing CSS infrastructure

### File Structure Requirements

**New files:**
- `frontend/src/features/process/components/DiagnosticsPanel.jsx`
- `frontend/src/__tests__/features/process/diagnostics-panel.test.jsx`

**Modified files:**
- `frontend/src/features/process/components/UploadForm.jsx` — replace OCR `<details>` block with `<DiagnosticsPanel>`, import DiagnosticsPanel, remove `formatConfidence` helper (moves to DiagnosticsPanel)
- `frontend/src/__tests__/features/process/upload-form.test.jsx` — update 2 test assertions from `"extracted text"` to `"show details"`

**Files NOT to touch:**
- `backend/` — no backend changes
- `frontend/src/styles/` — existing `.details-section` CSS already covers DiagnosticsPanel
- `frontend/src/lib/api-client.js` — no changes
- `frontend/src/App.jsx` — no changes

### Previous Story Intelligence (3-1 → 3-2)

- **96 backend tests passing** after Story 3-1 (includes 3 integration tests verifying diagnostics in success/partial responses and absence in error responses).
- **28 frontend tests passing** after Story 3-1 — no frontend changes in that story.
- **`formatConfidence`** helper exists in UploadForm — move identical logic to DiagnosticsPanel, remove from UploadForm.
- **`response_model_exclude_none=True`** on `/v1/process`: the `diagnostics` key is absent from the JSON for error responses (it's `None` on the model and excluded). Frontend receives `undefined` for `mutation.data?.diagnostics` on error paths.
- **Existing `<details>` pattern** is working well and tested — DiagnosticsPanel should extend it, not reinvent it.
- **TimingInfo fields are all required**: after Story 3-1 code review hardening, `ocr_ms` and `pinyin_ms` are required (not optional). If `diagnostics` is present, all three timing fields are guaranteed to exist.

### Git Intelligence

- `513c009` (current): Story 3-1 — diagnostics payload, request correlation middleware, schema hardening. This landed `DiagnosticsPayload` schema, `diagnostics_service.py`, `RequestIdMiddleware`, and wired everything into the process endpoint.
- `3f51fe1`: Epic 2 — frontend in `UploadForm.jsx` with TanStack Query patterns, low-confidence guidance, and existing `<details>` OCR section established.
- Key frontend pattern: all component tests use `@testing-library/react` + `vitest` + `userEvent.setup()`. Pure presentational components don't need `QueryClientProvider` wrapper.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-3.2]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#DetailDisclosurePanel]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Diagnostics-Learning-Flow]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project-Directory-Structure — DiagnosticsPanel.jsx location]
- [Source: backend/app/schemas/diagnostics.py — DiagnosticsPayload shape with required fields]
- [Source: frontend/src/features/process/components/UploadForm.jsx — existing OCR details block, formatConfidence, ocrSegments pattern]
- [Source: frontend/src/__tests__/features/process/upload-form.test.jsx — test patterns, fixture shapes, two assertions to update]
- [Source: frontend/src/styles/main.css#details-section — CSS already defined, no new styles needed]
- [Source: _bmad-output/implementation-artifacts/3-1-capture-request-metadata-and-structured-diagnostics-payload.md — diagnostics JSON shape, schema hardening notes]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-03-26: Implemented frontend diagnostics disclosure by adding `DiagnosticsPanel`, integrating it into `UploadForm`, and updating UploadForm assertions for the new "Show Details" summary label.
- 2026-03-26: Ran `npm test` in `frontend/` — 5 test files, 36 tests passing.

### Completion Notes List

- Added `DiagnosticsPanel` as a pure presentational component using the existing `<details className="details-section">` pattern so diagnostics stay hidden by default and render only when data exists.
- Replaced the old OCR-only disclosure in `UploadForm` with `DiagnosticsPanel`, preserving OCR visibility while adding timing and trace sections from the backend diagnostics payload.
- Added focused diagnostics panel coverage and updated UploadForm assertions to the new disclosure label; full frontend suite passed.

### File List

- `frontend/src/features/process/components/DiagnosticsPanel.jsx`
- `frontend/src/features/process/components/UploadForm.jsx`
- `frontend/src/__tests__/features/process/diagnostics-panel.test.jsx`
- `frontend/src/__tests__/features/process/upload-form.test.jsx`

## Change Log

- 2026-03-26: Story 3-2 created — expose collapsible result-page diagnostics; creates DiagnosticsPanel component, integrates into UploadForm replacing existing OCR details, adds timing and trace sections from Story 3-1 diagnostics payload
- 2026-03-26: Story 3-2 implemented — added collapsible diagnostics panel with OCR/timing/trace sections, integrated it into UploadForm, added focused panel tests, updated UploadForm disclosure assertions, and verified `npm test` passes (36 tests)
