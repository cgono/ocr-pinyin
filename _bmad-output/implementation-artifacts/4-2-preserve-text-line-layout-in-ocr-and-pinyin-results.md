# Story 4.2: Preserve Text Line Layout in OCR and Pinyin Results

Status: done

## Story

As Clint,
I want the pinyin result to preserve the original line breaks from the book page,
so that I can follow the result alongside the physical book without mentally re-mapping the layout.

## Acceptance Criteria

1. **Given** OCR extracts text from a page with multiple lines, **When** the result is displayed, **Then** line breaks from the source are preserved in the pinyin output **And** each original line appears on its own visual row.

2. **Given** OCR returns a single unstructured block with no line metadata, **When** layout cannot be determined, **Then** the result falls back to the existing rendering (all segments rendered as contiguous inline ruby elements with no inter-segment spacing, matching prior behavior) with no regression.

3. **Given** a multi-line result is displayed, **When** the user views the output, **Then** each character/pinyin pair group has a visible gap below it (margin or padding) so adjacent line groups are not visually "smooshed" together.

4. **Given** all existing backend and frontend tests run, **When** the schema change is applied, **Then** all existing tests continue to pass.

## Tasks / Subtasks

- [x] Add `line_id: int | None = None` to `RawOcrSegment` in `backend/app/adapters/ocr_provider.py` (AC: 1, 4)
  - [x] Add `line_id: int | None = None` field to the frozen dataclass

- [x] Update GCV provider to assign sequential `line_id` per paragraph (AC: 1, 4)
  - [x] In `_gcv_response_to_documents`: add running `line_id` counter that increments per paragraph and store in `Document.metadata`
  - [x] In `_documents_to_segments`: pass `doc.metadata.get("line_id")` to `RawOcrSegment`

- [x] Add `line_id: int | None = None` to `OcrSegment` and `PinyinSegment` in `backend/app/schemas/process.py` (AC: 1, 4)

- [x] Propagate `line_id` through `ocr_service._normalize_segment` (AC: 1, 4)
  - [x] Pass `line_id=segment.line_id` in the `OcrSegment(...)` constructor call

- [x] Propagate `line_id` through `pinyin_service.generate_pinyin` (AC: 1, 4)
  - [x] Pass `line_id=ocr_segment.line_id` in both `PinyinSegment(...)` constructor calls (aligned path and uncertain path)

- [x] Update frontend to render multi-line groups in `frontend/src/features/process/components/UploadForm.jsx` (AC: 1, 2, 3)
  - [x] Add `groupSegmentsByLine(segments)` helper function (returns `null` if all `line_id` are null)
  - [x] Replace flat `pinyinSegments.map(...)` render with conditional: flat if no `line_id`, grouped if present
  - [x] Wrap each group in `<div className="pinyin-line-group">...</div>`

- [x] Add `.pinyin-line-group` CSS to `frontend/src/styles/main.css` (AC: 3)
  - [x] `display: block; margin-bottom: 1em;`

- [x] Update frontend test fixtures and add multi-line tests in `frontend/src/__tests__/features/process/upload-form.test.jsx` (AC: 1, 2, 4)
  - [x] Add `line_id` to OCR and pinyin segments in `DEFAULT_SUCCESS_RESPONSE` (use `line_id: 0` for single-segment fixture — no behavior change)
  - [x] Add test: multi-line response renders segments in separate `.pinyin-line-group` divs
  - [x] Add test: null `line_id` segments fall back to flat rendering (no `.pinyin-line-group` wrappers)

- [x] Add backend unit tests for `line_id` propagation (AC: 1, 4)
  - [x] In `backend/tests/unit/services/test_ocr_service.py`: assert `line_id` is passed through `_normalize_segment`
  - [x] In `backend/tests/unit/services/test_pinyin_service.py`: assert `line_id` is propagated from `OcrSegment` to `PinyinSegment`

## Dev Notes

### Schema Change — Exact Diff

```
# backend/app/adapters/ocr_provider.py
@dataclass(frozen=True)
class RawOcrSegment:
    text: str
    language: str | None = None
    confidence: float | int | None = None
+   line_id: int | None = None   # NEW

# backend/app/schemas/process.py
class OcrSegment(BaseModel):
    text: str
    language: str
    confidence: float = Field(ge=0.0, le=1.0)
+   line_id: int | None = None   # NEW

class PinyinSegment(BaseModel):
    source_text: str
    pinyin_text: str
    alignment_status: Literal["aligned", "uncertain"]
    reason_code: str | None = None
+   line_id: int | None = None   # NEW
```

**Backward compatibility:** `line_id` defaults to `None` everywhere. All existing tests that construct `OcrSegment(text=..., language=..., confidence=...)` or `PinyinSegment(...)` without `line_id` continue to work unchanged.

### GCV Provider — `line_id` Assignment

Assign `line_id` as a sequential integer (0, 1, 2 ...) counting paragraphs in iteration order across all pages and blocks. Each paragraph = one `RawOcrSegment` = one `line_id`.

```python
# In _gcv_response_to_documents, add line_id counter:
def _gcv_response_to_documents(response) -> list[Document]:
    docs = []
    line_id = 0  # NEW
    for page in response.full_text_annotation.pages or []:
        for block in page.blocks:
            if block.block_type != vision.Block.BlockType.TEXT:
                continue
            for paragraph in block.paragraphs:
                text = _paragraph_text(paragraph)
                if not text.strip():
                    continue
                langs = list(paragraph.property.detected_languages)
                language = langs[0].language_code if langs else None
                docs.append(
                    Document(
                        page_content=text,
                        metadata={"confidence": paragraph.confidence, "language": language, "line_id": line_id},  # MODIFIED
                    )
                )
                line_id += 1  # NEW
    return docs

# In _documents_to_segments:
def _documents_to_segments(docs: list[Document]) -> list[RawOcrSegment]:
    return [
        RawOcrSegment(
            text=doc.page_content,
            language=doc.metadata.get("language"),
            confidence=doc.metadata["confidence"],
            line_id=doc.metadata.get("line_id"),  # NEW
        )
        for doc in docs
    ]
```

### OCR Service — `_normalize_segment`

```python
def _normalize_segment(segment: RawOcrSegment) -> OcrSegment:
    return OcrSegment(
        text=(segment.text or "").strip(),
        language=_normalize_language(segment.language),
        confidence=_normalize_confidence(segment.confidence),
        line_id=segment.line_id,  # NEW
    )
```

### Pinyin Service — `generate_pinyin`

Both `PinyinSegment(...)` constructor calls must propagate `line_id`:

```python
for ocr_segment in segments:
    text = ocr_segment.text
    if not text:
        continue
    try:
        ...
        result_segments.append(
            PinyinSegment(
                source_text=text,
                pinyin_text=pinyin_text,
                alignment_status="aligned",
                line_id=ocr_segment.line_id,  # NEW
            )
        )
    except PinyinProviderUnavailableError as exc:
        raise ...
    except PinyinExecutionError:
        result_segments.append(
            PinyinSegment(
                source_text=text,
                pinyin_text="",
                alignment_status="uncertain",
                reason_code="pinyin_execution_failed",
                line_id=ocr_segment.line_id,  # NEW
            )
        )
```

### Frontend — Grouping Logic and Render

Add this helper **above** the `UploadForm` component (module-level function):

```js
function groupSegmentsByLine(segments) {
  const hasLineIds = segments.some(s => s.line_id != null)
  if (!hasLineIds) return null  // fallback signal

  const groups = []
  let currentLineId = undefined
  let currentGroup = []

  for (const seg of segments) {
    if (seg.line_id !== currentLineId && currentGroup.length > 0) {
      groups.push({ line_id: currentLineId, segments: currentGroup })
      currentGroup = []
    }
    currentLineId = seg.line_id
    currentGroup.push(seg)
  }
  if (currentGroup.length > 0) {
    groups.push({ line_id: currentLineId, segments: currentGroup })
  }
  return groups
}
```

Replace the existing flat render block (lines 249–255 of `UploadForm.jsx`) with:

```jsx
{pinyinSegments.length > 0 && (
  <div aria-label="pinyin-result">
    <h3 className="pinyin-result__title">Pinyin Reading</h3>
    <div className="pinyin-result__content">
      {(() => {
        const lineGroups = groupSegmentsByLine(pinyinSegments)
        if (!lineGroups) {
          // Fallback: flat rendering (no line_id available)
          return pinyinSegments.map((seg, index) => (
            <ruby key={`${seg.source_text}-${seg.alignment_status}-${index}`}>
              {seg.source_text}
              <rt>{renderPinyinAnnotation(seg)}</rt>
            </ruby>
          ))
        }
        return lineGroups.map((group, gi) => (
          <div key={`line-${group.line_id}-${gi}`} className="pinyin-line-group">
            {group.segments.map((seg, si) => (
              <ruby key={`${seg.source_text}-${seg.alignment_status}-${si}`}>
                {seg.source_text}
                <rt>{renderPinyinAnnotation(seg)}</rt>
              </ruby>
            ))}
          </div>
        ))
      })()}
    </div>
  </div>
)}
```

### CSS Addition

Add to `frontend/src/styles/main.css` (after existing `.pinyin-result__content` styles):

```css
.pinyin-line-group {
  display: block;
  margin-bottom: 1em;
}
```

No `ruby` layout change needed — `<ruby>` elements inside the group still display inline as before.

### Critical Files to Touch

| File | Action | Reason |
|------|--------|--------|
| `backend/app/adapters/ocr_provider.py` | Modify | Add `line_id` to `RawOcrSegment` dataclass |
| `backend/app/adapters/google_cloud_vision_ocr_provider.py` | Modify | Assign sequential `line_id` per paragraph |
| `backend/app/schemas/process.py` | Modify | Add `line_id` to `OcrSegment` and `PinyinSegment` |
| `backend/app/services/ocr_service.py` | Modify | Pass `line_id` through in `_normalize_segment` |
| `backend/app/services/pinyin_service.py` | Modify | Propagate `line_id` in both `PinyinSegment` constructor calls |
| `frontend/src/features/process/components/UploadForm.jsx` | Modify | Add `groupSegmentsByLine` helper and conditional grouped render |
| `frontend/src/styles/main.css` | Modify | Add `.pinyin-line-group` margin |
| `backend/tests/unit/services/test_ocr_service.py` | Update | Assert `line_id` passthrough |
| `backend/tests/unit/services/test_pinyin_service.py` | Update | Assert `line_id` propagation |
| `frontend/src/__tests__/features/process/upload-form.test.jsx` | Update | Multi-line render + null fallback tests |

### No Backend API Contract Change

`line_id: int | null` is a **new nullable field with a default of `None`** on both `OcrSegment` and `PinyinSegment`. Pydantic serializes `None` as `null` in JSON. The `ProcessResponse` schema uses `ConfigDict(extra="forbid")` but the inner `OcrData`/`PinyinData`/`OcrSegment`/`PinyinSegment` models do not — adding a nullable field with a default is purely additive. Existing contract tests (`test_process_response_contract.py`) construct `OcrSegment(text="你好", language="zh", confidence=0.88)` — these continue to work with `line_id` defaulting to `null`.

### NoOp and Textract Providers

`NoOpOcrProvider` raises `ProviderUnavailableError` — never reaches segment creation, no change needed. `TextractOcrProvider` returns `RawOcrSegment(text=..., language=..., confidence=...)` — `line_id` defaults to `None` via the new field default, and all segments will have `line_id=null`, triggering the graceful flat-render fallback in the frontend.

### Frontend Test Fixture Update

The existing test fixtures in `upload-form.test.jsx` use OCR/pinyin segments without `line_id`. Since `line_id` is absent (undefined in JS), `s.line_id != null` evaluates to `false` for all segments → `groupSegmentsByLine` returns `null` → flat rendering → all existing render assertions still pass unchanged.

For new multi-line tests, construct a response with two distinct `line_id` values:

```js
const MULTI_LINE_SUCCESS_RESPONSE = {
  status: 'success',
  request_id: 'req_multiline',
  data: {
    ocr: {
      segments: [
        { text: '老师叫', language: 'zh', confidence: 0.95, line_id: 0 },
        { text: '同学们好', language: 'zh', confidence: 0.94, line_id: 1 },
      ]
    },
    pinyin: {
      segments: [
        { source_text: '老师叫', pinyin_text: 'lǎo shī jiào', alignment_status: 'aligned', line_id: 0 },
        { source_text: '同学们好', pinyin_text: 'tóng xué men hǎo', alignment_status: 'aligned', line_id: 1 },
      ]
    }
  }
}
```

Assert that the rendered output contains two `.pinyin-line-group` divs:
```js
const lineGroups = container.querySelectorAll('.pinyin-line-group')
expect(lineGroups).toHaveLength(2)
```

### Architecture Compliance

- **No new dependencies.** This story touches only existing files — no new packages.
- **Frontend calls only through `lib/api-client.js`** — unchanged; `line_id` arrives in the response payload automatically.
- **CSS lives in `frontend/src/styles/main.css`** — confirmed by Story 4-1 which added `.loading-spinner` there (file was `index.css` in the story spec but Story 4-1 completion notes list it as `main.css` — use `main.css`).
- **Backend tests live in `backend/tests/unit/services/`** — follow the exact pattern in `test_ocr_service.py` and `test_pinyin_service.py`.
- **Frontend tests live in `frontend/src/__tests__/features/process/`** — extend `upload-form.test.jsx`.

### Previous Story (4-1) Learnings

- Story 4-1 completion notes list `frontend/src/styles/main.css` (not `index.css`) — use `main.css` for CSS additions.
- Story 4-1 added `CropPreview.jsx` to `frontend/src/features/process/components/` — it's now imported in `UploadForm.jsx`. Don't remove or break it.
- The `pinyinSegments` variable is derived at line 113: `const pinyinSegments = mutation.data?.data?.pinyin?.segments || []` — this is the correct source to pass to `groupSegmentsByLine`.
- Story 4-1 split camera capture from file upload; `handleCameraCapture` / `handleFileChange` / `handleCropConfirm` / `handleCropDismiss` are all live. Do not touch them.

### Git Intelligence

- `4fabddf` — Story 4-1: added `CropPreview.jsx`, startup health ping, loading spinner. Frontend patterns are current.
- No backend schema changes since Epic 3 merge. The `process.py` schema is clean and ready for the `line_id` addition.
- CSS changes from 4-1 went into `frontend/src/styles/main.css`.

### References

- Story spec: `_bmad-output/planning-artifacts/epics.md` — Epic 4, Story 4.2
- Schema files: `backend/app/schemas/process.py`, `backend/app/adapters/ocr_provider.py`
- GCV provider: `backend/app/adapters/google_cloud_vision_ocr_provider.py`
- OCR service: `backend/app/services/ocr_service.py`
- Pinyin service: `backend/app/services/pinyin_service.py`
- Frontend render: `frontend/src/features/process/components/UploadForm.jsx` lines 246–258
- CSS: `frontend/src/styles/main.css`
- Architecture patterns: `_bmad-output/planning-artifacts/architecture.md` — Implementation Patterns & Consistency Rules

## Dev Agent Record

### Agent Model Used

gpt-5-codex

### Debug Log References

- `./.venv/bin/python -m pytest tests/unit/services/test_ocr_service.py tests/unit/services/test_pinyin_service.py tests/unit/schemas/test_process_response_contract.py`
- `./.venv/bin/python -m pytest`
- `./.venv/bin/python -m ruff check .`
- `npm test -- src/__tests__/features/process/upload-form.test.jsx`
- `npm test`
- `npm run lint`

### Completion Notes List

- Added nullable `line_id` fields to raw OCR, normalized OCR, and pinyin segment schemas so line metadata survives end-to-end without breaking existing callers.
- Updated the Google Cloud Vision paragraph extraction path to assign sequential paragraph-based `line_id` values and attach them to downstream `RawOcrSegment` instances.
- Added grouped pinyin rendering in the upload form when any `line_id` values are present, while preserving the legacy flat rendering path when all line IDs are null or absent.
- Added `.pinyin-line-group` spacing so visually separate source lines are not compressed together in the result view.
- Extended backend and frontend tests to cover `line_id` propagation, multiline grouped rendering, null-line fallback rendering, and schema backward compatibility.

### File List

- backend/app/adapters/ocr_provider.py
- backend/app/adapters/google_cloud_vision_ocr_provider.py
- backend/app/schemas/process.py
- backend/app/services/ocr_service.py
- backend/app/services/pinyin_service.py
- backend/tests/unit/services/test_ocr_service.py
- backend/tests/unit/services/test_pinyin_service.py
- frontend/src/features/process/components/UploadForm.jsx
- frontend/src/styles/main.css
- frontend/src/__tests__/features/process/upload-form.test.jsx

### Change Log

- 2026-03-28: Implemented Story 4.2 by propagating nullable `line_id` metadata through OCR and pinyin processing, rendering multiline frontend groups with fallback flat rendering, and adding backend/frontend regression coverage. Status set to `review`.
