# Story 4.8: Track Google Translate Cost for Pasted-Text Requests

Status: done

## Story

As Clint,
I want pasted-text translation requests included in request-cost estimation and daily budget accounting,
so that the budget system reflects actual Google Translate spend instead of treating text study as free.

## Acceptance Criteria

1. **Given** a `POST /v1/process-text` request is accepted for translation processing, **When** request cost is estimated, **Then** the system calculates text-processing cost from submitted text size using configured Google Translate pricing rules **And** the estimated cost is returned through the same diagnostics/metrics field used by image requests.

2. **Given** a pasted-text request completes, **When** cost accounting is recorded, **Then** the request cost is persisted through the same daily accounting path as image requests **And** daily totals include text-translation spend when evaluating budget warnings or enforcement.

3. **Given** translation is disabled, skipped, or provider-pricing metadata is unavailable, **When** the text-request estimate is prepared, **Then** the system uses the same explicit fallback/confidence signaling pattern defined in Story 4.3 **And** the request still completes without misreporting the cost path as OCR-based.

4. **Given** backend tests run, **When** text-processing cost support is added, **Then** targeted coverage verifies request diagnostics, daily aggregate totals, and budget-threshold behavior for pasted-text requests **And** existing image-request cost behavior remains unchanged.

## Tasks / Subtasks

- [x] Extend backend budget estimation to support pasted-text translation cost (AC: 1, 3, 4)
  - [x] Add a text-cost estimation entrypoint in `backend/app/services/budget_service.py` that derives Google Translate cost from accepted text size and pricing configuration
  - [x] Preserve explicit `confidence="unavailable"` fallback when translation is disabled or pricing metadata is invalid/unavailable
  - [x] Keep existing image-request OCR cost estimation unchanged

- [x] Wire pasted-text processing through the shared budget accounting path (AC: 1, 2, 3)
  - [x] Update `backend/app/api/v1/process_text.py` to estimate text-request cost from accepted zh-bearing lines instead of hardcoding zero cost
  - [x] Record full-confidence text-request cost through `record_request_cost()` after the translation phase completes
  - [x] Ensure diagnostics expose text cost estimates without labeling them as OCR cost

- [x] Add regression coverage for pasted-text diagnostics and budget thresholds (AC: 2, 4)
  - [x] Add unit tests in `backend/tests/unit/services/test_budget_service.py` for text-cost estimation, pricing fallback, and image-cost regression
  - [x] Add integration tests in `backend/tests/integration/api_v1/test_process_text_route.py` for diagnostics cost estimates, daily aggregate recording, and warn/block threshold behavior

### Review Findings

- [x] [Review][Patch] Translation enrichment failure → full-confidence cost still recorded and returned in diagnostics (AC3 violation) [backend/app/api/v1/process_text.py]
- [x] [Review][Patch] No test for translation-enabled-but-enrichment-fails cost path — `confidence="unavailable"` and zero spend not verified (AC4 gap) [backend/tests/integration/api_v1/test_process_text_route.py]
- [x] [Review][Defer] Direct `os.environ.get()` in `estimate_text_processing_cost` bypasses app config layer — deferred, pre-existing
- [x] [Review][Defer] `_GOOGLE_TRANSLATE_USD_PER_MILLION_CHARS` constant and `.env.example` value can drift independently — deferred, pre-existing

## Dev Notes

### Architecture Notes

- Budget estimation and accounting stay centralized in `backend/app/services/budget_service.py`.
- `POST /v1/process-text` should keep using the same diagnostics payload shape as image processing while reporting text-derived costs, not OCR costs.
- Daily aggregate totals must continue to flow through `daily_cost_store` and `record_request_cost()`.

### Technical Notes

- Preserve Story 6.6 behavior for validation, pinyin generation, translation enrichment, and reading projection.
- Use text size from accepted pasted-text content, scoped to the lines that actually flow through translation.
- No new dependencies are required.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-01-translate-budget.md`
- `_bmad-output/implementation-artifacts/6-6-add-direct-pasted-text-study-mode.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-04-01 08:00: Loaded BMAD config, sprint status, Story 4.8 planning context, and the existing image/text budget-processing paths.
- `cd backend && ./.venv/bin/pytest tests/unit/services/test_budget_service.py tests/integration/api_v1/test_process_text_route.py`
- `cd backend && ./.venv/bin/ruff check app tests`
- `cd backend && ./.venv/bin/pytest`

### Implementation Plan

- Add failing budget-service and pasted-text route tests first for text-cost estimation, diagnostics, and daily accounting.
- Implement text-cost estimation in `budget_service.py`, then wire `process_text.py` to estimate and record pasted-text translation spend.
- Run targeted and full backend verification, then update story bookkeeping and sprint tracking to `review`.

### Completion Notes List

- Added `estimate_text_processing_cost()` in `budget_service.py` with Google Translate per-million-character pricing, explicit unavailable fallback, and no regression to image OCR cost estimation.
- Updated `POST /v1/process-text` to estimate cost from accepted zh-bearing lines, surface that estimate in diagnostics, and record full-confidence text-request spend through the shared daily budget store after translation handling.
- Added backend regression coverage for text-cost estimation defaults/overrides/fallbacks plus pasted-text diagnostics, daily aggregate recording, and warn/block budget-threshold behavior.
- Fixed the pasted-text pinyin-failure integration test to patch the route’s actual `generate_pinyin` import seam.

### File List

- _bmad-output/implementation-artifacts/4-8-track-google-translate-cost-for-pasted-text-requests.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/.env.example
- backend/app/api/v1/process_text.py
- backend/app/services/budget_service.py
- backend/tests/integration/api_v1/test_process_text_route.py
- backend/tests/unit/services/test_budget_service.py

### Change Log

- 2026-04-01: Story artifact created from the approved sprint change proposal and moved to in-progress for implementation.
- 2026-04-01: Implemented pasted-text translation cost estimation/accounting, added backend regression coverage, and moved the story to review.
