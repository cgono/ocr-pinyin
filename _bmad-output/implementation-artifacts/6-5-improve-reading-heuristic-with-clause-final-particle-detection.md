# Story 6.5: Improve Reading Heuristic with Clause-Final Particle Detection

Status: done

## Story

As Clint,
I want the reading service to detect clause-final particles (了, 呢, 啊, etc.) mid-line and insert commas at those boundaries,
So that auto-punctuated text reads and plays back more naturally instead of producing one long unpunctuated sentence.

## Acceptance Criteria

1. **Given** a line of Chinese text containing one or more clause-final particles mid-line (not at the very end), **When** the reading service builds the display/playback text, **Then** a comma `，` is inserted immediately after each qualifying particle, **And** terminal `。` is still appended if the text does not already end with terminal punctuation.

2. **Given** a particle appears fewer than a minimum number of characters from the start of its current clause segment (configurable constant, suggested: 2), **When** the reading service evaluates it, **Then** no comma is inserted before it, to avoid unnatural comma-at-start-of-text artifacts.

3. **Given** a particle appears at the very end of the raw text (terminal position), **When** the reading service evaluates it, **Then** no comma is inserted after it; the particle serves as the natural sentence end and terminal `。` is still appended if needed.

4. **Given** the processed text produces the same output as v1 (no particles found, text already has terminal punctuation), **When** `build_reading_projection` is called, **Then** it falls back to `None` with the same semantics as v1 — `applied=False` triggers a `None` return.

5. **Given** all existing story 6.4 backend tests run after this change, **When** story 6.5 is implemented, **Then** all existing tests pass, including the integration test that asserts `provider.kind == "heuristic"`.

6. **Given** the provider version is bumped to `"v2"`, **When** `data.reading` is present in the API response, **Then** `provider.version` equals `"v2"`.

## Tasks / Subtasks

- [x] Add particle detection to the display-text derivation logic (AC: 1, 2, 3, 4)
  - [x] Define particle set constant in `reading_service.py`: `了`, `呢`, `啊`, `啦`, `哦`, `嘛`, `吧`, `哈`, `喔`
  - [x] Define `_MIN_CLAUSE_LENGTH` constant (suggested: 2) — minimum characters before particle for comma insertion to fire
  - [x] Replace or extend `_derive_display_text` with clause-aware logic: scan for each particle in order, insert `，` after it when the preceding clause segment meets the minimum length and the particle is not at end-of-text
  - [x] Retain the existing terminal-punctuation append logic after particle-based insertion runs
  - [x] Keep the function signature and return type identical — callers must not need to change

- [x] Bump provider version (AC: 6)
  - [x] Change `_PROVIDER_VERSION = "v1"` to `_PROVIDER_VERSION = "v2"` in `reading_service.py`

- [x] Add targeted unit tests (AC: 1, 2, 3, 4, 5)
  - [x] Test: particle mid-line inserts comma — e.g., `太阳公公起床了公鸡` → `太阳公公起床了，公鸡。`
  - [x] Test: particle at end of text does not insert comma — e.g., `你好了` → `你好了。`
  - [x] Test: particle too close to line start does not trigger comma — e.g., `了解后续` → `了解后续。` (no comma after `了`)
  - [x] Test: multiple mid-line particles produce multiple commas — e.g., `起床了吃饭吧出门啊` → `起床了，吃饭吧，出门啊。`
  - [x] Test: already-terminal-punctuated text is not double-punctuated and still returns `None` from `build_reading_projection`
  - [x] Test: text with no particles still gets terminal `。` added (same as v1 behavior)

- [x] Update the existing integration test that asserts provider version (AC: 5, 6)
  - [x] In `test_process_route_success_adds_reading_projection_without_mutating_raw_payloads`, update `provider.version` assertion from `"v1"` to `"v2"` if the assertion exists, or add it

### Review Findings

- [x] [Review][Patch] Off-by-one in `_MIN_CLAUSE_LENGTH` guard — `clause_length` is incremented before the check, so when a particle is reached it already counts the particle itself. With `_MIN_CLAUSE_LENGTH = 2`, the condition `>= 2` fires after only 1 preceding character (e.g., `不了解` → `不了，解`). Dev Notes explicitly say this should NOT fire. Fix: change `clause_length >= _MIN_CLAUSE_LENGTH` to `clause_length > _MIN_CLAUSE_LENGTH`. [`backend/app/services/reading_service.py`]
- [x] [Review][Patch] Missing test for `不了解` false-positive case — Dev Notes call out `不了解` as a case the guard should suppress, but no test asserts it. Add: `不了解` → `不了解。` (no comma after `不了`). [`backend/tests/unit/services/test_reading_service.py`]
- [x] [Review][Defer] `clause_length` counts all characters (spaces, punctuation, mixed-script) without reset — inflates preceding-char count for mixed-content OCR output; unlikely to matter for typical Chinese OCR but makes the guard imprecise. deferred, pre-existing
- [x] [Review][Defer] Early-return on terminal punctuation skips all particle processing — `"他走了吗。"` gets no comma after `了`. Intentional per AC 4 (already-punctuated text left unchanged), but asymmetric behavior is undocumented. deferred, pre-existing
- [x] [Review][Defer] Interior CJK punctuation (、…—) does not reset `clause_length` — a particle appearing just after `、` has an inflated preceding-char count. deferred, pre-existing

## Dev Notes

### What This Story Changes

**Backend only.** No schema changes, no frontend changes, no API contract changes. The `ReadingData` / `ReadingGroup` / `ReadingProviderInfo` shapes are unchanged. The only file that needs editing is `backend/app/services/reading_service.py` (and its test file).

### The Motivating Example

Input OCR line: `太阳公公起床了公鸡喔喔把我们叫你追我赶大家赛跑看谁最先到学校`

v1 output: `太阳公公起床了公鸡喔喔把我们叫你追我赶大家赛跑看谁最先到学校。`

v2 target output: `太阳公公起床了，公鸡喔喔把我们叫，你追我赶大家赛跑看谁最先到学校。`

Note: `你追我赶大家赛跑` is NOT split by v2 — there is no particle there. That kind of split requires an LLM. v2 handles particle-based clause boundaries only.

### Particle Detection Approach

The particle set for v2: `了`, `呢`, `啊`, `啦`, `哦`, `嘛`, `吧`, `哈`, `喔`

Simple scan — no NLP library, no tokenizer, pure Python string search:

```python
_CLAUSE_FINAL_PARTICLES = ("了", "呢", "啊", "啦", "哦", "嘛", "吧", "哈", "喔")
_MIN_CLAUSE_LENGTH = 2  # minimum chars before a particle before comma insertion fires
```

Pseudocode for the new `_derive_display_text`:
1. Walk through `raw_text` character by character (or scan for each particle in order).
2. When a particle is found at position `i`:
   - If `i` is the last character → skip (it's at end-of-text, not mid-line).
   - If the number of characters since the last comma (or start of text) is less than `_MIN_CLAUSE_LENGTH` → skip.
   - Otherwise insert `，` after position `i`.
3. After all particles are processed, check the result: if it does not end with terminal punctuation, append `。`.

### The `了` False-Positive Risk

`了` appears in words like `了解` (understand), `为了` (in order to), `以便了解` etc. Without a tokenizer, you cannot perfectly distinguish `了` as a verb complement/aspect marker (clause-final) from `了` as part of a multi-character word.

The `_MIN_CLAUSE_LENGTH` constant is the pragmatic mitigation:
- `了解` — `了` is at position 0 of its clause, which has length 0 before it. Does not fire.
- `起床了` — `了` has 2 chars before it in its current clause segment. Fires correctly.
- `不了解` — `了` has 1 char before it (`不`). With `_MIN_CLAUSE_LENGTH = 2`, this does NOT fire. Acceptable false-negative for v2.

This is intentionally conservative. A future v3 with a tokenizer or LLM can improve precision.

### No New Dependencies

Do NOT add `jieba`, `spacy`, `stanza`, or any other NLP library. Keep this pure Python. The architecture's dependency-management discipline is strict — new backend dependencies require a separate proposal.

### Current `reading_service.py` Structure (as of story 6.4)

```python
_PROVIDER_NAME = "built_in_rules"
_PROVIDER_VERSION = "v1"
_TERMINAL_PUNCTUATION = ("。", "！", "？", ".", "!", "?")

def _group_segments_by_line(...) -> ...:   # unchanged
def _concat_source_text(...) -> str:        # unchanged
def _derive_display_text(raw_text: str) -> str:  # THIS is what v2 replaces/extends
def build_reading_projection(pinyin_data: PinyinData) -> ReadingData | None:  # unchanged
```

Only `_derive_display_text` and `_PROVIDER_VERSION` need to change. Everything else — grouping logic, confidence calculations, schema construction — stays identical.

### Version in Provider Metadata

The version lives at:
```python
_PROVIDER_VERSION = "v1"   # change to "v2"
```

It surfaces in the API response as `data.reading.provider.version`. The frontend reads `readingData.provider.name` for the auto-punctuation note display (`"Auto-punctuation applied by built_in_rules."`) — this is unchanged. The version is informational metadata only and has no frontend rendering logic tied to it.

### Existing Tests That Must Still Pass

All tests in:
- `backend/tests/unit/services/test_reading_service.py` — the three existing tests should still pass; add the new particle tests alongside them
- `backend/tests/integration/api_v1/test_process_route.py` — specifically `test_process_route_success_adds_reading_projection_without_mutating_raw_payloads` which asserts `provider.kind == "heuristic"` (this is fine — kind doesn't change, only version)
- `backend/tests/unit/schemas/test_process_response_contract.py` — unchanged, these test schema structure not heuristic behavior

### Deferred Items From Story 6.4 Review (for Awareness)

These were logged in `deferred-work.md` from the 6.4 code review and remain deferred — do NOT address them in this story:
- `_derive_display_text` appending `。` to text ending in closing brackets like `「好。」` — v2 limitation, same as v1
- `current_line_id or 0` semantics in `_group_segments_by_line`
- Missing tests for empty segment list and `line_id=None` mid-sequence

### References

- Story 6.4 (foundation): `_bmad-output/implementation-artifacts/6-4-add-optional-auto-punctuation-and-sentence-aware-reading-groups.md`
- Current service: `backend/app/services/reading_service.py`
- Service tests: `backend/tests/unit/services/test_reading_service.py`
- Integration tests: `backend/tests/integration/api_v1/test_process_route.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-03-31 12:36:37 +08: Loaded BMAD config, story 6.5 context, current `reading_service.py`, and existing reading/integration tests before making changes.
- 2026-03-31 12:47: Running backend tests initially failed during collection because `backend/.venv` contained Linux wheels (`pydantic_core`); rebuilt the backend virtualenv with `uv sync` and resumed TDD verification.
- 2026-03-31 12:49: Verified red state with 3 expected failures tied to missing v2 provider metadata and missing particle-based comma insertion.
- 2026-03-31 12:53: Verified green state with targeted backend tests, full backend regression suite, and Ruff checks for the touched files.

### Implementation Plan

- Add story-specific regression tests for particle insertion behavior and provider version metadata.
- Implement a conservative clause-final-particle heuristic in `_derive_display_text` while preserving existing terminal punctuation semantics and `None` fallback behavior.
- Re-run targeted and full backend verification, then update story bookkeeping and sprint tracking to `review`.

### Completion Notes List

- Added a v2 clause-final-particle heuristic to `backend/app/services/reading_service.py` using a fixed particle set and `_MIN_CLAUSE_LENGTH = 2`.
- Preserved existing fallback semantics: already-terminal-punctuated text still returns unchanged, and `build_reading_projection()` still returns `None` when no useful improvement is applied.
- Bumped reading provider metadata from `v1` to `v2` and covered it in both unit and integration tests.
- Added unit coverage for mid-line particles, terminal particles, conservative false-positive avoidance near clause start, multiple particle boundaries, unchanged terminal text, and non-particle punctuation appending.
- Rebuilt the backend virtualenv locally to replace incompatible Linux wheels so validation could run on this macOS workspace.
- Verified with `.venv/bin/python -m pytest` in `backend/` and `.venv/bin/python -m ruff check app/services/reading_service.py tests/unit/services/test_reading_service.py tests/integration/api_v1/test_process_route.py`.

### File List

- backend/app/services/reading_service.py
- backend/tests/unit/services/test_reading_service.py
- backend/tests/integration/api_v1/test_process_route.py
- _bmad-output/implementation-artifacts/sprint-status.yaml

### Change Log

- 2026-03-31: Story created from post-review discussion of v1 heuristic limitations observed in OCR output. Particle-based clause detection identified as a pure-Python, no-dependency improvement feasible without an LLM.
- 2026-03-31: Implemented v2 particle-based clause detection, added targeted reading-service tests, updated provider-version integration coverage, and moved the story to review.
