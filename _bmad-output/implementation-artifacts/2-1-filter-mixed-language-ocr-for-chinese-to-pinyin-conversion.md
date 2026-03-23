# Story 2.1: Filter Mixed-Language OCR for Chinese-to-Pinyin Conversion

Status: ready-for-dev

## Story

As Clint,
I want non-Chinese OCR content filtered before pinyin conversion,
So that generated pronunciation output focuses on relevant Chinese text.

## Acceptance Criteria

1. **Given** OCR output contains Chinese and non-Chinese segments, **When** conversion preprocessing runs, **Then** non-Chinese segments are excluded from pinyin generation **And** retained Chinese source text remains available for review in `data.ocr.segments[]`.

2. **Given** OCR output is primarily non-Chinese (no usable Chinese segments survive filtering), **When** filtering completes, **Then** the system returns a structured recoverable error response with code `ocr_no_chinese_text` **And** the message guides Clint to retake the photo with better Chinese content focus.

## Tasks / Subtasks

- [ ] Update `backend/app/services/ocr_service.py` to distinguish non-Chinese content from blank images (AC: 1, 2)
  - [ ] After normalization, separate segments into `chinese_segments` (pass `_is_usable_chinese_segment`) and `non_chinese_segments` (fail the filter)
  - [ ] If `raw_segments` is empty or all segments have empty text after normalization → keep existing `ocr_no_text_detected` code (blank/unreadable image)
  - [ ] If `non_chinese_segments` exist but `chinese_segments` is empty → raise `OcrServiceError` with code `ocr_no_chinese_text`, user-facing message about retaking for Chinese content
  - [ ] If `chinese_segments` is non-empty → return `chinese_segments` (same as current happy path; non-Chinese silently filtered)
  - [ ] Add `logger.debug` logging for filtered-segment count when non-Chinese content is dropped
- [ ] Add unit tests for the new filtering behavior in `backend/tests/unit/services/test_ocr_service.py` (AC: 1, 2)
  - [ ] Test: non-Chinese-only segments raise `OcrServiceError` with `code="ocr_no_chinese_text"`
  - [ ] Test: mixed Chinese+non-Chinese segments return only the Chinese segments (non-Chinese dropped silently)
  - [ ] Test: empty `raw_segments` list still raises `ocr_no_text_detected` (regression guard)
- [ ] Add integration test for the "primarily non-Chinese" path in `backend/tests/integration/api_v1/test_process_route.py` (AC: 2)
  - [ ] Test: `POST /v1/process` with stub provider returning non-Chinese-only segments returns `status="error"`, `error.code="ocr_no_chinese_text"`, `error.category="ocr"`
- [ ] Verify all existing 59 tests still pass and `ruff check .` is clean (AC: 1, 2)

## Dev Notes

### Story Foundation

- **Epic goal**: Epic 2 improves output trust for mixed-content real-world images (Chinese storybook pages often contain page numbers, publisher marks, and English annotations).
- **Dependencies**: Requires Epic 1 complete (`/v1/process` baseline, Google Cloud Vision OCR integration from Story 1.7). GCV returns paragraph-level segments with `language_code` (`zh-Hans`, `zh-Hant`, `en`, etc.) — this is the critical prerequisite for language filtering.
- **Source**: `_bmad-output/planning-artifacts/epics.md#Story-2.1`; FR6 (filter non-Chinese for pinyin), FR7 (preserve extracted source text).

### What Already Exists — Do NOT Reinvent

**`backend/app/services/ocr_service.py` already has:**
```python
_CJK_CHAR_RE = re.compile(r"[\u3400-\u9fff]")

def _is_usable_chinese_segment(segment: OcrSegment) -> bool:
    if not segment.text:
        return False
    has_cjk_text = _CJK_CHAR_RE.search(segment.text) is not None
    is_chinese_language = segment.language.startswith("zh")
    return has_cjk_text or is_chinese_language
```
This dual-signal filter (CJK regex OR `zh`-prefixed language code) is already correct and must NOT be changed. Story 2.1 only changes what happens *after* filtering when the result is empty.

**Current `extract_chinese_segments` flow (relevant excerpt):**
```python
segments = [_normalize_segment(segment) for segment in raw_segments]
usable_segments = [segment for segment in segments if _is_usable_chinese_segment(segment)]

if not usable_segments:
    raise OcrServiceError(
        code="ocr_no_text_detected",
        message="No readable Chinese text was detected. Retake the photo and try again.",
    )

return usable_segments
```
**Problem**: `ocr_no_text_detected` is used for BOTH blank images AND non-Chinese content. Story 2.1 splits these cases.

### Implementation: The Only Code Change Required

Replace the `if not usable_segments` block with a two-branch check:

```python
segments = [_normalize_segment(segment) for segment in raw_segments]
usable_segments = [segment for segment in segments if _is_usable_chinese_segment(segment)]

if not usable_segments:
    # Distinguish blank/unreadable image from non-Chinese content
    non_chinese = [s for s in segments if s.text]  # any non-empty segment that failed the Chinese filter
    if non_chinese:
        logger.debug("OCR returned %d non-Chinese segment(s); no Chinese text detected", len(non_chinese))
        raise OcrServiceError(
            code="ocr_no_chinese_text",
            message="No Chinese text was detected. The image may contain non-Chinese content. Retake the photo focused on Chinese text.",
        )
    raise OcrServiceError(
        code="ocr_no_text_detected",
        message="No readable Chinese text was detected. Retake the photo and try again.",
    )

return usable_segments
```

**No other service/schema/route changes are needed for this story.** The route handler (`process.py`) already propagates `error.category` and `error.code` from `OcrServiceError` into the `ProcessResponse` error envelope — this works for the new error code without modification.

### Architecture Compliance

- **Error taxonomy** (`backend/app/core/errors.py` / architecture doc §Error Handling Patterns): `ocr` is an established error category. New code `ocr_no_chinese_text` follows the `{category}_{specific_condition}` naming pattern matching existing codes: `ocr_no_text_detected`, `ocr_provider_unavailable`, `ocr_execution_failed`.
- **Service boundary**: All filtering logic stays in `ocr_service.py`. The route handler (`process.py`) remains unchanged — it does not inspect error codes; it passes them through verbatim.
- **Response envelope**: `status="error"` with `error.category="ocr"`, `error.code="ocr_no_chinese_text"` matches the architecture envelope spec and existing contract tests.
- **No schema changes**: `OcrSegment`, `OcrData`, `ProcessResponse` are untouched. The story does NOT require returning filtered-out segments in the response — "retained source text" means Chinese segments are preserved in `data.ocr.segments[]`; non-Chinese segments are intentionally excluded from client output.

### File Structure Requirements

**Modified files (only):**
- `backend/app/services/ocr_service.py` — replace single `if not usable_segments` block
- `backend/tests/unit/services/test_ocr_service.py` — add 3 unit tests
- `backend/tests/integration/api_v1/test_process_route.py` — add 1 integration test

**Files NOT to touch:**
- `backend/app/schemas/process.py` — no schema changes needed
- `backend/app/api/v1/process.py` — route already handles OcrServiceError generically
- `backend/app/adapters/ocr_provider.py` — provider interface unchanged
- `backend/app/adapters/google_cloud_vision_ocr_provider.py` — provider unchanged
- Any frontend files — this is backend-only for this story

### Testing Patterns (Match Existing Style)

**Unit test pattern** (from `test_ocr_service.py` — existing tests use `StubOcrProvider` or mock `get_ocr_provider`):

```python
import pytest
from unittest.mock import patch, AsyncMock
from app.adapters.ocr_provider import RawOcrSegment
from app.services.ocr_service import OcrServiceError, extract_chinese_segments

@pytest.mark.asyncio
async def test_extract_chinese_segments_non_chinese_only_raises_specific_error():
    non_chinese_segments = [
        RawOcrSegment(text="Hello World", language="en", confidence=0.95),
        RawOcrSegment(text="Page 12", language="en", confidence=0.90),
    ]
    with patch("app.services.ocr_service.get_ocr_provider") as mock_factory:
        mock_provider = mock_factory.return_value
        mock_provider.extract.return_value = non_chinese_segments
        with pytest.raises(OcrServiceError) as exc_info:
            await extract_chinese_segments(b"fake", "image/jpeg")
    assert exc_info.value.code == "ocr_no_chinese_text"
    assert exc_info.value.category == "ocr"
```

**Integration test pattern** (from `test_process_route.py` — uses `override_dependencies` with `StubOcrProvider`):
Look at existing `StubOcrProvider` usage in that file and add a stub that returns non-Chinese segments, then assert the response JSON has `status="error"`, `error.code="ocr_no_chinese_text"`.

**Note on existing test count**: 59 tests exist and must remain green. The implementation changes a single `if` block — no existing test paths are altered.

### Previous Story Intelligence (Stories 1.4–1.7 Patterns)

- **GCV paragraph-level language codes** (Story 1.7): GCV returns `"zh-Hans"`, `"zh-Hant"`, `"en"`, `"und"` etc. The `_is_usable_chinese_segment()` filter correctly handles all these via `startswith("zh")`. Real-world storybook images will have mixed paragraphs — this is the exact scenario Story 2.1 targets.
- **Keep providers thin** (Stories 1.4, 1.7): No business logic in adapters. Language filtering stays in `ocr_service.py` (service layer) — never in the provider.
- **`logger.debug` for detail logs** (Stories 1.4, 1.7): Use `debug` level for segment counts and filtering decisions. Do not log at `info` level for per-request operational details.
- **`run_in_executor` stays in `ocr_service.py`** (Story 1.7): The `extract()` call is already wrapped in the executor in the existing `extract_chinese_segments` function — do not add another executor wrapper.
- **Test file constraint removed for this story**: Story 1.7 was not allowed to modify test files; Story 2.1 explicitly requires adding tests.

### Git Intelligence

- `1421507` (latest): "correct course — swap OCR to Google Cloud Vision" — sets GCV as the production provider with paragraph-level language codes. Story 2.1 depends on GCV language codes (`zh-Hans`/`zh-Hant`) being present for reliable filtering.
- `a645403`: 59-test baseline established at Story 1.6. All tests pass with GCV provider wired in (Story 1.7).

### UX Context for This Story

Epic 2 is backend-only for Story 2.1 — no frontend changes required. The `ocr_no_chinese_text` error code flows to the frontend in the same `status="error"` envelope. Frontend error display already shows `error.message` to the user (from Story 1.3/1.5 implementation). The message "Retake the photo focused on Chinese text." aligns with UX principle: "Recovery language should guide, not punish."

Future Story 2.4 will add the explicit low-confidence UI with `Retake Photo` CTA. For now, the error message IS the recovery guidance.

### Project Structure Notes

```
backend/
  app/
    services/
      ocr_service.py          ← MODIFY: split "no text" vs "non-Chinese" error
  tests/
    unit/services/
      test_ocr_service.py     ← MODIFY: add 3 unit tests
    integration/api_v1/
      test_process_route.py   ← MODIFY: add 1 integration test
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-2.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error-Handling-Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Service-Boundaries]
- [Source: backend/app/services/ocr_service.py — `_is_usable_chinese_segment`, `extract_chinese_segments`]
- [Source: backend/app/api/v1/process.py — route error propagation pattern]
- [Source: backend/tests/unit/services/test_ocr_service.py — unit test patterns to follow]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List
