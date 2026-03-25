# Story 2.2: Align Pinyin Output with Source Text Segments

Status: done

## Story

As Clint,
I want pinyin output aligned to extracted source segments,
So that I can follow sentence flow accurately while reading.

## Acceptance Criteria

1. **Given** extracted Chinese source segments are available, **When** pinyin is produced, **Then** output preserves segment-level alignment by returning `data.pinyin.segments[]` with `source_text`, `pinyin_text`, and `alignment_status` **And** any non-aligned segment sets `alignment_status="uncertain"` and includes `reason_code`.

2. **Given** some segments cannot be confidently aligned, **When** response is generated, **Then** uncertain segments are explicitly marked **And** remaining aligned segments are still returned.

## Tasks / Subtasks

- [x] Update `PinyinSegment` schema in `backend/app/schemas/process.py` (AC: 1)
  - [x] Replace `{hanzi, pinyin}` fields with `{source_text, pinyin_text, alignment_status, reason_code?}`
  - [x] Add `alignment_status: Literal["aligned", "uncertain"]`
  - [x] Add `reason_code: str | None = None` (only set for `alignment_status="uncertain"`)
- [x] Redesign `generate_pinyin()` in `backend/app/services/pinyin_service.py` to produce segment-level output (AC: 1, 2)
  - [x] Produce one `PinyinSegment` per OCR segment (not per character)
  - [x] On success: `alignment_status="aligned"`, `pinyin_text` = space-joined pinyin characters from provider
  - [x] On `PinyinExecutionError`: mark segment `alignment_status="uncertain"`, `reason_code="pinyin_execution_failed"`, continue processing remaining segments
  - [x] On `PinyinProviderUnavailableError`: still raise `PinyinServiceError` (systemic failure, nothing will work)
  - [x] Skip OCR segments with empty `text` (same as before)
- [x] Update existing unit tests in `backend/tests/unit/services/test_pinyin_service.py` (AC: 1, 2)
  - [x] Update `test_generate_pinyin_returns_per_char_segments` → verify segment-level output with `source_text`/`pinyin_text`/`alignment_status`
  - [x] Update `test_generate_pinyin_concatenates_multiple_ocr_segments` → verify one `PinyinSegment` per OCR segment
  - [x] Add test: when one segment raises `PinyinExecutionError`, that segment is `uncertain` and other segments are still `aligned`
- [x] Update contract tests in `backend/tests/contract/response_envelopes/test_process_envelopes.py` (AC: 1)
  - [x] Update `test_process_endpoint_success_envelope_contract` lines 86-87: replace `hanzi` field assertions with `source_text`/`pinyin_text`/`alignment_status` assertions
  - [x] Update `test_process_success_ocr_fields_unchanged_after_pinyin_addition` pinyin segment assertions
- [x] Add/update integration test in `backend/tests/integration/api_v1/test_process_route.py` (AC: 1, 2)
  - [x] Update `test_process_route_valid_upload_returns_success_with_ocr_and_pinyin` to check new segment shape
  - [x] Add test: multiple OCR segments where one fails alignment → `status="success"` with mixed `aligned`/`uncertain` segments
- [x] Verify all 63 tests still pass and `ruff check .` is clean (AC: 1, 2)

## Dev Notes

### Story Foundation

- **Epic goal**: Epic 2 improves output trust for real-world mixed-content images. Story 2.2 is the alignment step — pinyin must be traceable back to specific source text segments.
- **Dependencies**: Requires Story 2.1 complete (`_is_usable_chinese_segment` filter in place; GCV language codes available). OCR segments in `data.ocr.segments[]` are the input.
- **FRs covered**: FR11 (pinyin aligned to source text), FR7 (source text preserved), FR8 (uncertainty indication).

### Current State — What Exists

**`PinyinSegment` (current — `backend/app/schemas/process.py`):**
```python
class PinyinSegment(BaseModel):
    hanzi: str
    pinyin: str
```
This is per-character. Story 2.2 replaces it with per-segment alignment.

**`PinyinData` (unchanged):**
```python
class PinyinData(BaseModel):
    segments: list[PinyinSegment]
```
`PinyinData` structure stays the same — only `PinyinSegment` fields change.

**`generate_pinyin()` (current — `backend/app/services/pinyin_service.py`):**
- Takes `list[OcrSegment]`, iterates over segments, calls provider per segment
- Collects all per-character `RawPinyinSegment` results into one flat list
- Returns `PinyinData` with all characters concatenated

**`pypinyin_provider.py`** returns `list[RawPinyinSegment]` where each entry is `{hanzi: str, pinyin: str}` — one per character. Example: `"你好"` → `[RawPinyinSegment(hanzi="你", pinyin="nǐ"), RawPinyinSegment(hanzi="好", pinyin="hǎo")]`.

The provider interface (`pinyin_provider.py`) and the `PyPinyinProvider` implementation are **unchanged** by this story. The service layer transforms provider output into the new aligned segment shape.

### Schema Change — The Only New Fields Required

Replace `PinyinSegment` in `backend/app/schemas/process.py`:

```python
class PinyinSegment(BaseModel):
    source_text: str
    pinyin_text: str
    alignment_status: Literal["aligned", "uncertain"]
    reason_code: str | None = None
```

Do NOT add a `Literal` import if it already exists — `process.py` already uses `Literal["success", "partial", "error"]` in `ProcessResponse`. Just add `"aligned"` and `"uncertain"` to the new field.

`pinyin_text` for an aligned segment: space-join the `pinyin` values from all per-character `RawPinyinSegment` results. Example: `"nǐ hǎo"` for `"你好"`.

### Service Redesign — Segment-Level Alignment

Replace `generate_pinyin()` in `backend/app/services/pinyin_service.py`:

```python
async def generate_pinyin(segments: list[OcrSegment]) -> PinyinData:
    """Generate pinyin for each OCR segment, tracking alignment status per segment.

    Aligned segments: provider succeeded; pinyin_text is space-joined tone-marked pinyin.
    Uncertain segments: PinyinExecutionError on that segment; segment is still returned.
    Systemic failure: PinyinProviderUnavailableError raises PinyinServiceError (nothing works).
    """
    provider = get_pinyin_provider()
    loop = asyncio.get_running_loop()
    result_segments: list[PinyinSegment] = []

    for ocr_segment in segments:
        text = ocr_segment.text
        if not text:
            continue
        try:
            raw_chars = await loop.run_in_executor(
                None,
                lambda t=text: provider.generate(text=t),
            )
            pinyin_text = " ".join(seg.pinyin for seg in raw_chars)
            result_segments.append(
                PinyinSegment(
                    source_text=text,
                    pinyin_text=pinyin_text,
                    alignment_status="aligned",
                )
            )
        except PinyinProviderUnavailableError as exc:
            raise PinyinServiceError(
                code="pinyin_provider_unavailable",
                message="Pinyin generation is temporarily unavailable. Please try again.",
            ) from exc
        except PinyinExecutionError:
            result_segments.append(
                PinyinSegment(
                    source_text=text,
                    pinyin_text="",
                    alignment_status="uncertain",
                    reason_code="pinyin_execution_failed",
                )
            )

    return PinyinData(segments=result_segments)
```

**Key behavior differences from current:**
- One `PinyinSegment` per OCR segment (not per character)
- `PinyinExecutionError` no longer fatal — segment marked uncertain and loop continues
- `PinyinProviderUnavailableError` still fatal — raises `PinyinServiceError` immediately

### Route Handler — No Changes Needed

`backend/app/api/v1/process.py` passes `pinyin_data` through to `ProcessData(pinyin=pinyin_data)` verbatim. The route does not inspect `PinyinSegment` fields — it just serializes whatever `PinyinData` contains. No route changes required.

### Test Updates Required

#### Contract tests (`backend/tests/contract/response_envelopes/test_process_envelopes.py`)

Two tests reference `hanzi` and must be updated:

**`test_process_endpoint_success_envelope_contract`** (lines 70-87):
The `StubPinyinProvider` in this file still returns `list[RawPinyinSegment]` — that's correct and unchanged (it's the provider adapter interface, not the schema). But the assertions at lines 86-87 check `hanzi`:
```python
# REMOVE these assertions:
assert payload["data"]["pinyin"]["segments"][0]["hanzi"] == "你"
assert payload["data"]["pinyin"]["segments"][1]["hanzi"] == "好"
```
Replace with:
```python
# The stub returns [RawPinyinSegment(hanzi="你", pinyin="nǐ"), RawPinyinSegment(hanzi="好", pinyin="hǎo")]
# generate_pinyin() with one OCR segment "你好" produces ONE PinyinSegment (not two):
assert len(payload["data"]["pinyin"]["segments"]) == 1
seg = payload["data"]["pinyin"]["segments"][0]
assert seg["source_text"] == "你好"
assert seg["pinyin_text"] == "nǐ hǎo"
assert seg["alignment_status"] == "aligned"
assert "reason_code" not in seg  # excluded because None + exclude_none=True
```

**`test_process_success_ocr_fields_unchanged_after_pinyin_addition`** (lines 158-176):
Uses `StubOcrProvider([RawOcrSegment(text="你", language="zh", confidence=0.95)])` with `StubPinyinProvider([RawPinyinSegment(hanzi="你", pinyin="nǐ")])`. After the schema change, if there are any assertions on `pinyin.segments[0]["hanzi"]`, remove or update them. The OCR assertions (text/language/confidence) are unaffected.

**`assert_process_envelope` function** (lines 29-67): Does NOT assert on pinyin segment fields — only checks `pinyin.segments` is a list. No changes needed here.

#### Unit tests (`backend/tests/unit/services/test_pinyin_service.py`)

Update these existing tests (their assertions check the old per-character shape):

**`test_generate_pinyin_returns_per_char_segments`**: Now verify one `PinyinSegment` per OCR segment with new fields:
```python
async def test_generate_pinyin_returns_segment_level_output(monkeypatch):
    stub = StubPinyinProvider([
        RawPinyinSegment(hanzi="你", pinyin="nǐ"),
        RawPinyinSegment(hanzi="好", pinyin="hǎo"),
    ])
    monkeypatch.setattr("app.services.pinyin_service.get_pinyin_provider", lambda: stub)
    result = await generate_pinyin([OcrSegment(text="你好", language="zh", confidence=0.9)])
    assert len(result.segments) == 1
    assert result.segments[0].source_text == "你好"
    assert result.segments[0].pinyin_text == "nǐ hǎo"
    assert result.segments[0].alignment_status == "aligned"
    assert result.segments[0].reason_code is None
```

**`test_generate_pinyin_concatenates_multiple_ocr_segments`**: Now verify two OCR segments → two `PinyinSegment` entries:
```python
# Two OCR segments → two result segments (one per OCR segment)
result = await generate_pinyin([
    OcrSegment(text="你好", language="zh", confidence=0.9),
    OcrSegment(text="世界", language="zh", confidence=0.8),
])
assert len(result.segments) == 2
assert result.segments[0].source_text == "你好"
assert result.segments[1].source_text == "世界"
```

Add new test for `PinyinExecutionError` → uncertain segment, others still aligned:
```python
async def test_generate_pinyin_marks_uncertain_when_execution_fails(monkeypatch):
    class PartiallyFailingProvider:
        def __init__(self):
            self._call_count = 0
        def generate(self, *, text: str) -> list[RawPinyinSegment]:
            self._call_count += 1
            if self._call_count == 2:
                raise PinyinExecutionError("malformed output")
            return [RawPinyinSegment(hanzi=c, pinyin="?") for c in text]

    monkeypatch.setattr("app.services.pinyin_service.get_pinyin_provider", lambda: PartiallyFailingProvider())
    result = await generate_pinyin([
        OcrSegment(text="你好", language="zh", confidence=0.9),
        OcrSegment(text="世界", language="zh", confidence=0.8),
    ])
    assert len(result.segments) == 2
    assert result.segments[0].alignment_status == "aligned"
    assert result.segments[1].alignment_status == "uncertain"
    assert result.segments[1].reason_code == "pinyin_execution_failed"
    assert result.segments[1].source_text == "世界"
```

#### Integration tests (`backend/tests/integration/api_v1/test_process_route.py`)

Update `test_process_route_valid_upload_returns_success_with_ocr_and_pinyin` to check new field names (`source_text`, `pinyin_text`, `alignment_status`). Add one test:

```python
# New integration test: successful response has aligned segment with correct fields
# Use StubOcrProvider returning one Chinese segment and StubPinyinProvider returning chars
# Assert: pinyin.segments[0].source_text == segment text
# Assert: pinyin.segments[0].alignment_status == "aligned"
```

### Architecture Compliance

- **Response envelope**: `data.pinyin.segments[]` is additive — the contract test `assert_process_envelope` already handles this with "pinyin field is additive — may be present but is not required by contract" comment. No contract violation.
- **Error taxonomy**: `reason_code="pinyin_execution_failed"` follows the `{category}_{specific_condition}` naming pattern. This is a sub-field within `PinyinSegment`, not a top-level `error` field — no conflict with the error taxonomy enum in `core/errors.py`.
- **Service boundaries**: All alignment logic stays in `pinyin_service.py`. Route handler, OCR service, and adapters unchanged.
- **`response_model_exclude_none=True`**: Set on the route. `reason_code=None` is excluded from serialized output for aligned segments — this is intentional and correct.
- **`snake_case`**: All new fields (`source_text`, `pinyin_text`, `alignment_status`, `reason_code`) follow the convention.

### File Structure Requirements

**Modified files:**
- `backend/app/schemas/process.py` — replace `PinyinSegment` fields
- `backend/app/services/pinyin_service.py` — redesign `generate_pinyin()` for segment-level alignment
- `backend/tests/unit/services/test_pinyin_service.py` — update 2 existing tests, add 1 new test
- `backend/tests/contract/response_envelopes/test_process_envelopes.py` — update 2 assertion blocks
- `backend/tests/integration/api_v1/test_process_route.py` — update 1 existing test, add 1 new test

**Files NOT to touch:**
- `backend/app/adapters/pinyin_provider.py` — protocol interface unchanged (`generate()` still returns `list[RawPinyinSegment]`)
- `backend/app/adapters/pypinyin_provider.py` — implementation unchanged
- `backend/app/api/v1/process.py` — route handler unchanged
- `backend/app/services/ocr_service.py` — no changes needed
- `backend/app/schemas/process.py` other classes — only `PinyinSegment` changes
- Any frontend files — this is backend-only

### Previous Story Intelligence (2.1)

- **Providers stay thin**: Per Story 2.1 and 1.4/1.7 patterns — `pypinyin_provider.py` retains its per-character output. Story 2.2 transforms that output in the service layer, not in the adapter.
- **`logger.debug` for operational detail**: If adding debug logging for uncertain segments, use `logger.debug` (not `info`). Example: `logger.debug("Segment alignment uncertain for source_text=%r: %s", text, reason)`.
- **63 tests currently passing**: After this story, expect ~66+ tests (3-4 additions across unit/integration/contract).
- **`run_in_executor` pattern**: Already in `generate_pinyin()` — keep the `lambda t=text: provider.generate(text=t)` closure pattern unchanged. The executor wrapping is correct.
- **Test import pattern**: Contract test file imports `PinyinExecutionError` inline (see `test_process_endpoint_pinyin_error_envelope_contract`). If adding a new test that needs `PinyinExecutionError`, import at the top of the relevant test module.

### Git Intelligence

- `ab3e1d8` (latest): Story 2.1 complete — `ocr_service.py` splits `ocr_no_text_detected` vs `ocr_no_chinese_text`. Chinese segments now reliably filtered before reaching `generate_pinyin()`.
- `82fdaa8`: Story 2.0 (frontend styling) — no backend impact.
- 63 tests baseline from Story 2.1.

### Project Structure Notes

```
backend/
  app/
    schemas/
      process.py          ← MODIFY: replace PinyinSegment fields
    services/
      pinyin_service.py   ← MODIFY: redesign generate_pinyin() for segment-level alignment
  tests/
    unit/services/
      test_pinyin_service.py    ← MODIFY: update 2 tests, add 1 test
    integration/api_v1/
      test_process_route.py     ← MODIFY: update 1 test, add 1 test
    contract/response_envelopes/
      test_process_envelopes.py ← MODIFY: update 2 assertion blocks (hanzi → source_text)
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-2.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#API-Response-Formats]
- [Source: _bmad-output/planning-artifacts/architecture.md#Error-Handling-Patterns]
- [Source: backend/app/schemas/process.py — PinyinSegment, PinyinData current definitions]
- [Source: backend/app/services/pinyin_service.py — generate_pinyin() current implementation]
- [Source: backend/app/adapters/pypinyin_provider.py — per-character RawPinyinSegment output]
- [Source: backend/tests/contract/response_envelopes/test_process_envelopes.py — lines 86-87, 158-176]
- [Source: _bmad-output/implementation-artifacts/2-1-filter-mixed-language-ocr-for-chinese-to-pinyin-conversion.md — Dev Notes]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No blockers encountered. Implementation matched story spec exactly.

### Completion Notes List

- Replaced `PinyinSegment(hanzi, pinyin)` with `PinyinSegment(source_text, pinyin_text, alignment_status, reason_code?)` in `process.py`
- Redesigned `generate_pinyin()` to emit one `PinyinSegment` per OCR segment (not per character); `PinyinExecutionError` now marks segment uncertain instead of raising
- Updated 2 existing unit tests (renamed and updated assertions for new schema); replaced `test_generate_pinyin_raises_on_execution_error` with `test_generate_pinyin_marks_uncertain_when_execution_fails`
- Updated contract test `test_process_endpoint_success_envelope_contract` assertions from `hanzi` to `source_text`/`pinyin_text`/`alignment_status`
- Updated integration test `test_process_route_valid_upload_returns_success_with_ocr_and_pinyin` for new segment shape; added `test_process_route_mixed_segments_returns_aligned_and_uncertain`
- 64 tests pass (up from 63 baseline); `ruff check .` clean

### File List

- backend/app/schemas/process.py
- backend/app/services/pinyin_service.py
- backend/tests/unit/services/test_pinyin_service.py
- backend/tests/contract/response_envelopes/test_process_envelopes.py
- backend/tests/integration/api_v1/test_process_route.py
- _bmad-output/implementation-artifacts/sprint-status.yaml

## Change Log

- 2026-03-24: Story 2-2 implemented — replaced per-character PinyinSegment with per-OCR-segment alignment model; PinyinExecutionError now marks segment uncertain instead of failing the request
