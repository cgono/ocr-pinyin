# Story 6.1: Add English Translation Below Chinese Characters

Status: done

## Story

As Clint,
I want an English translation displayed below each line of Chinese characters in the result,
so that I can understand the meaning without switching to another app.

## Acceptance Criteria

1. **Given** a successful OCR + pinyin result, **When** `TRANSLATION_ENABLED=true`, **Then** each `PinyinSegment` in the API response includes `translation_text` as a non-null string **And** the frontend renders the English translation below the character row in smaller, muted styling.

2. **Given** `TRANSLATION_ENABLED=false` or the translation call fails, **When** the result is returned, **Then** `translation_text` is `null` **And** the existing display is otherwise unchanged with no regression.

3. **Given** translation is defined per visual line group, **When** multiple `PinyinSegment` items share the same `line_id`, **Then** they receive the same line-level `translation_text` value and the frontend renders that translation once per rendered line group, not once per character or ruby annotation.

4. **Given** all existing backend and frontend tests run, **When** the schema change is applied, **Then** all existing tests continue to pass.

## Tasks / Subtasks

- [x] Add backend translation schema support without breaking existing envelopes (AC: 1, 2, 4)
  - [x] Add `translation_text: str | None = None` to `backend/app/schemas/process.py` `PinyinSegment`
  - [x] Keep `ProcessResponse`, diagnostics payloads, and existing status/warning/error envelopes unchanged
  - [x] Add or update schema/unit tests that exercise both `translation_text=None` and `translation_text="..."` payloads

- [x] Add a translation provider seam using the existing adapter pattern (AC: 1, 2, 4)
  - [x] Add `google-cloud-translate>=3.0,<4.0` to [backend/pyproject.toml](/Users/clint/Documents/GitHub/ocr-pinyin/backend/pyproject.toml) and refresh the backend lockfile
  - [x] Create a new adapter protocol file, expected path: [backend/app/adapters/translation_provider.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/adapters/translation_provider.py)
  - [x] Add a Google Cloud Translate implementation, expected path: [backend/app/adapters/google_cloud_translate_provider.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/adapters/google_cloud_translate_provider.py)
  - [x] Reuse the existing GCP credential pattern already used by Vision (`GOOGLE_APPLICATION_CREDENTIALS_JSON` / optional `GOOGLE_CLOUD_PROJECT`)
  - [x] Gate the feature with `TRANSLATION_ENABLED`; when disabled, the translation layer must short-circuit to `null` values without API errors

- [x] Add a dedicated translation service that enriches pinyin segments after pinyin generation (AC: 1, 2, 3, 4)
  - [x] Create [backend/app/services/translation_service.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/services/translation_service.py) instead of mixing translation into `pinyin_service.py`
  - [x] Group segments by `line_id` and translate one combined source string per line group
  - [x] Apply the same translated string back onto every segment in that line group via `translation_text`
  - [x] Treat translation provider unavailability/execution failure as non-fatal for this story: log it and return segments with `translation_text=None`
  - [x] Preserve current behavior for partial responses caused by pinyin failure or low confidence; translation is only attempted after pinyin succeeds

- [x] Wire translation into the process orchestration at the right layer (AC: 1, 2, 4)
  - [x] Update [backend/app/api/v1/process.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/api/v1/process.py) to call the translation service after `generate_pinyin(...)`
  - [x] Keep translation out of the OCR service and out of raw FastAPI route glue as much as practical
  - [x] Do not expand `DiagnosticsPayload`, `TimingInfo`, or `TraceStep` in this story; translation failures should not trigger new response-contract churn
  - [x] Add integration coverage in [backend/tests/integration/api_v1/test_process_route.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/tests/integration/api_v1/test_process_route.py) for enabled, disabled, and provider-failure paths

- [x] Render translation text in the existing result UI without replacing the current line-group layout (AC: 1, 2, 3, 4)
  - [x] Update the existing brownfield result renderer in [frontend/src/features/process/components/UploadForm.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/features/process/components/UploadForm.jsx)
  - [x] Reuse the existing `groupSegmentsByLine(...)` helper from Story 4.2; do not replace the grouping model
  - [x] For grouped rows, render the translation once beneath the character row using the first segment's `translation_text` for that group
  - [x] For flat fallback rendering when `line_id` data is absent, preserve the current ruby-only behavior and do not introduce duplicated translation rows
  - [x] Add muted/smaller styling in [frontend/src/styles/main.css](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/styles/main.css)

- [x] Update tests and configuration docs for the new toggle (AC: 1, 2, 4)
  - [x] Extend [frontend/src/__tests__/features/process/upload-form.test.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/__tests__/features/process/upload-form.test.jsx) with translation-enabled grouped rendering and null-translation fallback cases
  - [x] Add backend unit coverage for translation grouping/fallback behavior
  - [x] Update [backend/.env.example](/Users/clint/Documents/GitHub/ocr-pinyin/backend/.env.example) to document `TRANSLATION_ENABLED`

## Dev Notes

### Story Intent

This story adds a line-level English translation layer on top of the existing OCR + pinyin flow. It must feel like a small, safe extension of the current reading experience, not a rewrite of the result page or response contracts.

### Current Brownfield Reality

The architecture doc describes a future-leaning structure with a dedicated `ResultView.jsx`, but the live code currently renders results inside [frontend/src/features/process/components/UploadForm.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/features/process/components/UploadForm.jsx). Implement this story against the real codebase, not the aspirational structure.

Current backend orchestration lives in [backend/app/api/v1/process.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/api/v1/process.py), with service-level logic in [backend/app/services/ocr_service.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/services/ocr_service.py) and [backend/app/services/pinyin_service.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/services/pinyin_service.py).

### Reuse Existing Story 4.2 Layout Work

Story 4.2 already introduced `line_id` propagation and frontend grouping. Reuse that work:

- [backend/app/schemas/process.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/schemas/process.py)
- [backend/app/adapters/google_cloud_vision_ocr_provider.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/adapters/google_cloud_vision_ocr_provider.py)
- [backend/app/services/ocr_service.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/services/ocr_service.py)
- [backend/app/services/pinyin_service.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/services/pinyin_service.py)
- [frontend/src/features/process/components/UploadForm.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/features/process/components/UploadForm.jsx)
- [frontend/src/styles/main.css](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/styles/main.css)

Do not replace the line-group model. Extend it.

### Translation Granularity Rules

- Translation is defined at the visual line level, keyed by `line_id`.
- Build the translatable source string from the Chinese text in that line group, in segment order.
- Every `PinyinSegment` in the same line group should receive the same `translation_text` value. This satisfies the API-level acceptance criteria while keeping frontend rendering simple.
- The frontend should render the translation once per group, not once per segment.
- If translation is disabled or unavailable, all affected `translation_text` values must be `null`.

### Fallback Rules

- Translation failure is non-fatal in Story 6.1.
- Do not turn a successful OCR + pinyin response into `partial` or `error` just because translation failed.
- Do not add new warning categories for translation in this story.
- Keep `DiagnosticsPayload` stable. `TraceStep` currently only allows `ocr`, `pinyin`, and `confidence_check`, so do not extend that contract here.

### Provider and Dependency Guidance

Use a new translation adapter seam instead of embedding SDK calls directly into the route or pinyin provider. Follow the same general pattern used for OCR and pinyin adapters.

Recommended implementation shape:

- [backend/app/adapters/translation_provider.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/adapters/translation_provider.py)
  - `TranslationProvider` protocol
  - `TranslationProviderUnavailableError`
  - `TranslationExecutionError`
  - `NoOpTranslationProvider`
  - `get_translation_provider()`
- [backend/app/adapters/google_cloud_translate_provider.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/adapters/google_cloud_translate_provider.py)
  - Google Cloud Translate implementation using existing credentials
- [backend/app/services/translation_service.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/services/translation_service.py)
  - helper that returns enriched `PinyinData`

Keep the toggle simple:

- `TRANSLATION_ENABLED=true` enables the enrichment step
- `TRANSLATION_ENABLED=false` skips it and returns `translation_text=None`

No additional provider-selection env var is required for this story unless the dev discovers a concrete need.

### Git Intelligence / Anti-Reinvention Guardrail

Recent commit `eb1c833` removed `langchain-core` from the project. Do not reintroduce LangChain for translation. Use the Google SDK directly through a thin adapter, consistent with the repo's current simplification direction.

### Frontend Rendering Guidance

Current result markup is ruby-based and line-group based. The safest extension is:

1. Keep the existing ruby output for pinyin and hanzi.
2. Under each `.pinyin-line-group`, render one translation row if that group's translation is non-null.
3. Style translation as smaller and visually secondary to the pinyin/hanzi pair.
4. Preserve the current flat fallback path when `line_id` values are absent.

Do not create a new frontend page, route, or standalone result component for this story.

### Suggested Backend Test Coverage

- [backend/tests/unit/services/test_translation_service.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/tests/unit/services/test_translation_service.py)
  - groups by `line_id`
  - duplicates the line translation back onto each segment in the group
  - returns nulls when disabled
  - returns nulls when provider is unavailable or execution fails
- [backend/tests/integration/api_v1/test_process_route.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/tests/integration/api_v1/test_process_route.py)
  - success path with translation enabled
  - translation disabled path
  - translation provider failure path still returns `success` with null translation values
- [backend/tests/unit/schemas/test_process_response_contract.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/tests/unit/schemas/test_process_response_contract.py)
  - `PinyinSegment` accepts `translation_text`

### Suggested Frontend Test Coverage

- Translation text renders once per `.pinyin-line-group`
- Translation text uses muted secondary styling hook/class
- Null `translation_text` produces no translation row
- Existing flat ruby fallback still renders unchanged when `line_id` values are absent

### Project Structure Notes

- Architecture intent says feature-first modules and adapter/service layering. Follow that intent on the backend.
- Actual frontend structure is smaller than the architecture sketch; update the existing files in place.
- Keep API field naming in `snake_case`.
- Keep `/v1/process` as the only public process endpoint.

### References

- Epic/story source: [epics.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/epics.md)
- Sprint change proposal: [sprint-change-proposal-2026-03-29-translation-release.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-29-translation-release.md)
- PRD: [prd.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/prd.md)
- Architecture: [architecture.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/architecture.md)
- UX guidance: [ux-design-specification.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/ux-design-specification.md)
- Previous related implementation context: [4-2-preserve-text-line-layout-in-ocr-and-pinyin-results.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/implementation-artifacts/4-2-preserve-text-line-layout-in-ocr-and-pinyin-results.md)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-03-29: Story context created from Epic 6, PRD, architecture, UX, sprint change proposal, Story 4.2, current repo structure, and recent git history.

### Implementation Plan

- 2026-03-29: Add schema support and translation adapter/service seams first, then wire translation into `/v1/process`, update grouped frontend rendering, and finish with backend/frontend regression coverage.

### Completion Notes List

- Added `translation_text` to `PinyinSegment` and kept the existing process envelopes and diagnostics contracts unchanged.
- Added a Google Cloud Translate adapter seam plus a dedicated translation service that enriches grouped pinyin segments and degrades to `null` translations on provider failures.
- Wired translation enrichment into `/v1/process` after successful pinyin generation and preserved existing partial/error behavior.
- Rendered one muted translation row per grouped pinyin line in the existing `UploadForm` result view with no flat fallback duplication.
- Updated backend and frontend tests for enabled, disabled, and provider-failure translation paths.
- Regenerated `backend/uv.lock` after adding `google-cloud-translate`.
- Verified with `./.venv/bin/python -m pytest` in `backend`, `npm test` in `frontend`, and `npm run lint` in `frontend`.

### File List

- _bmad-output/implementation-artifacts/6-1-add-english-translation-below-chinese-characters.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/.env.example
- backend/app/adapters/google_cloud_translate_provider.py
- backend/app/adapters/translation_provider.py
- backend/app/api/v1/process.py
- backend/app/schemas/process.py
- backend/app/services/translation_service.py
- backend/pyproject.toml
- backend/tests/integration/api_v1/test_process_route.py
- backend/tests/unit/schemas/test_process_response_contract.py
- backend/tests/unit/services/test_translation_service.py
- backend/uv.lock
- frontend/src/__tests__/features/process/upload-form.test.jsx
- frontend/src/features/process/components/UploadForm.jsx
- frontend/src/styles/main.css

### Change Log

- 2026-03-29: Implemented Story 6.1 translation enrichment across backend adapter/service layers, process orchestration, grouped frontend rendering, tests, and backend dependency lock refresh.
