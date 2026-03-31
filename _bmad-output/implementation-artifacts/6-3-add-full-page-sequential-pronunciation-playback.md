# Story 6.3: Add Full-Page Sequential Pronunciation Playback

Status: done

## Story

As Clint,
I want to play the current page's Chinese lines from top to bottom,
so that I can follow the whole reading flow without tapping each line individually.

## Acceptance Criteria

1. **Given** a successful OCR + pinyin result with grouped lines and pronunciation playback support, **When** the user starts full-page playback, **Then** the UI plays each rendered line group's combined Chinese source text in visual order **And** only one utterance is active at a time **And** the active line is clearly indicated while playback advances.

2. **Given** full-page playback is active, **When** the user stops playback, starts playback on a different line, or a new result replaces the current page, **Then** the current utterance and any queued continuation are cancelled immediately **And** playback state resets without leaving stale active indicators.

3. **Given** full-page playback reaches the last available line, **When** the final utterance finishes, **Then** playback stops automatically **And** the UI returns to the idle state with no active line or page-level playing status.

4. **Given** the browser does not support speech synthesis, cannot find a suitable Chinese voice, or playback fails mid-sequence, **When** the result is displayed or playback is attempted, **Then** the existing reading result remains fully usable **And** full-page playback controls are disabled or hidden with the same non-blocking fallback pattern used for per-line playback **And** no backend error or response-contract change is introduced.

5. **Given** all existing frontend and backend tests run, **When** story 6.3 is implemented, **Then** all existing tests continue to pass.

## Tasks / Subtasks

- [x] Extend the existing frontend-only pronunciation orchestration to support page-level sequential playback without changing backend contracts (AC: 1, 2, 3, 4, 5)
  - [x] Keep `/v1/process`, `ProcessResponse`, and `PinyinSegment` unchanged for this story
  - [x] Reuse the Web Speech API path introduced in Story 6.2 instead of adding a backend audio provider, audio URLs, or persisted media
  - [x] Continue treating pronunciation as a frontend enhancement layered on top of grouped result rendering

- [x] Add page-level playback state and sequencing on top of the existing line-group model (AC: 1, 2, 3, 5)
  - [x] Reuse `groupSegmentsByLine(...)` and `buildSpokenLineText(...)` in [frontend/src/features/process/components/UploadForm.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/features/process/components/UploadForm.jsx)
  - [x] Start with the first grouped line and advance to the next line only after the current utterance's `onend` fires
  - [x] Keep exactly one active utterance at a time while preserving deterministic top-to-bottom line order
  - [x] Reset both line-level and page-level playback state when the sequence finishes, the user stops playback, or a new result is loaded

- [x] Preserve clean interaction between page playback and line playback controls (AC: 1, 2, 3, 4, 5)
  - [x] Add one page-level control near the grouped result header, for example `Play Page` / `Stop Page`
  - [x] If page playback is active and the user starts a specific line, cancel the page sequence and switch cleanly to that line
  - [x] If a line is already playing and the user starts page playback, cancel the line utterance first and then begin the page sequence from the first line
  - [x] Ensure the active line indicator stays accurate regardless of whether playback was started from the page-level or line-level control

- [x] Keep fallback and unsupported-browser behavior quiet and consistent with Story 6.2 (AC: 4, 5)
  - [x] Reuse the same support detection, voice-selection logic, and non-blocking fallback messaging already present in `UploadForm.jsx`
  - [x] Disable the page-level control when speech synthesis is unsupported, no Chinese-capable voice is available, or there are no grouped lines to play
  - [x] Treat mid-sequence playback errors as local UI failures only; never degrade the processed result status

- [x] Add styling for the page-level control and active-line affordances without disrupting the reading layout (AC: 1, 3, 4, 5)
  - [x] Update [frontend/src/styles/main.css](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/styles/main.css) with a small secondary page-playback control that fits the existing result hierarchy
  - [x] Add a subtle active-line visual cue that helps the user track which line is currently being spoken
  - [x] Preserve the current quiet reading layout, mobile tap targets, and translation row spacing

- [ ] Add regression coverage for sequential playback, switching, cancellation, and fallbacks (AC: 1, 2, 3, 4, 5)
  - [x] Extend [frontend/src/__tests__/features/process/upload-form.test.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/__tests__/features/process/upload-form.test.jsx) with page-level play/stop coverage
  - [x] Mock `window.speechSynthesis` and `SpeechSynthesisUtterance` to cover sequence advancement via `onend`, mid-sequence interruption, and error handling
  - [x] Add coverage proving that starting line playback cancels page playback and vice versa
  - [ ] Confirm existing backend tests remain unchanged and green because this story does not alter server contracts

### Review Findings

- [x] [Review][Patch] `onerror` handler lacks session guard — stale utterance can call `clearActivePlayback` against an active new session if async error fires after re-use of same lineKey [UploadForm.jsx — `startUtterance` onerror callback]
- [x] [Review][Patch] Duplicate `.pinyin-result__title` CSS rules — `margin: 0` added as a second rule at line 263 rather than merged into the existing rule at line 243 [main.css:243,263]
- [x] [Review][Patch] No test asserts page button is absent (not just disabled) for flat/non-grouped results — current fallback tests use `GROUPED_PLAYBACK_SUCCESS_RESPONSE` [upload-form.test.jsx]
- [x] [Review][Defer] `onSequenceEnd` closes over render-scope `lineGroups` — safe via session guard but fragile; future weakening of session guard would silently break sequence advancement [UploadForm.jsx — `startPagePlayback`] — deferred, pre-existing architectural pattern
- [x] [Review][Defer] `buildLineKey` still embeds `groupIndex` — violates Story 6.2 deferred "stable identifiers" note; not worsened but not resolved [UploadForm.jsx:72] — deferred, pre-existing
- [x] [Review][Defer] Cancel/`onend` race on Safari — simultaneous `onend` + stop click can cause a spurious extra `speak` call before cancel; session guard ultimately recovers [UploadForm.jsx — `cancelPlayback`] — deferred, browser quirk
- [x] [Review][Defer] Backend regression unverified — pre-existing local environment failure prevents `pytest` collection; story makes no backend changes — deferred, environment limitation
- [x] [Review][Defer] `handlePagePlayback` skips `!speechSynthesis` guard — benign today since `startUtterance` catches it, but `cancelPlayback` fires unnecessarily in unsupported browsers [UploadForm.jsx — `handlePagePlayback`] — deferred, minor

## Dev Notes

### Story Provenance

Epic 6 explicitly defined Story 6.1 and Story 6.2, but not Story 6.3. This story is inferred from the remaining Epic 6 "future audio pronunciation output" scope in [epics.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/epics.md), the UX goal of uninterrupted reading flow in [ux-design-specification.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/ux-design-specification.md), and the browser-based speech foundation already implemented in Story 6.2.

This story should remain a frontend-only extension of the current Web Speech API implementation. Do not turn it into a backend audio-generation project.

### Current Brownfield Reality

The live result UI still renders inside [frontend/src/features/process/components/UploadForm.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/features/process/components/UploadForm.jsx), not in the dedicated `ResultView.jsx` shown in the aspirational architecture. Implement this story against the actual brownfield structure.

Story 6.2 already established:

- grouped line rendering through `groupSegmentsByLine(...)`
- per-line spoken text assembly through `buildSpokenLineText(...)`
- one active utterance at a time
- Chinese-voice discovery and fallback messaging
- frontend regression coverage around play, stop, interruption, and unsupported cases

Page-level playback should extend that exact foundation rather than introducing a second speech stack.

### Playback Scope and Sequencing Rules

- Playback is page-level but still line-oriented; the sequence must speak one grouped line at a time in visual order.
- Build each utterance from the grouped line's concatenated `source_text` values in rendered order.
- Use Chinese source text for speech synthesis, not `pinyin_text`.
- Do not attempt to synthesize flat fallback results where `line_id` grouping is absent; page playback is only for grouped line output.
- When the sequence finishes normally, all active playback state must be cleared.

### State Management Guardrails

- Maintain exactly one active utterance at a time, even during page playback.
- Avoid duplicating the Story 6.2 playback logic into a second independent state machine for page controls.
- Prefer refactoring the existing pronunciation logic into a focused helper or local hook if that makes the sequencing logic clearer and safer.
- If refactoring, preserve current behaviors for unsupported browsers, missing voices, single-line playback, and result-reset cleanup.
- Treat queued continuation as local UI state only; do not persist it or expose it through API responses.

### Interaction Rules Between Page and Line Playback

- Page playback and line playback must be mutually exclusive.
- Starting a line while the page is playing cancels the page sequence immediately and begins that line only.
- Starting page playback while a line is playing cancels the line first and then starts the page from the first available grouped line.
- Stopping playback must clear both the active line indicator and any page-level "playing" state immediately.
- Replacing the current result set must cancel any in-flight or queued playback before the new result renders.

### Accessibility and UX Guardrails

- Controls must be keyboard accessible.
- Keep the page-level control visually secondary to the reading content, similar to the line-level controls from Story 6.2.
- The active line indication should be obvious enough to guide reading, but still quiet by default; avoid loud animations or disruptive focus jumps.
- Do not introduce modal errors, toast spam, or blocking banners for playback failures.
- Keep the interaction consistent with the mobile-first, calm reading flow described in the UX spec.

### Architecture and Contract Boundaries

This story should not:

- change the backend schema
- add new API fields such as `audio_url`, `page_audio_status`, or `pronunciation_queue`
- add a backend audio provider, media storage, or server-generated speech assets
- expand diagnostics contracts or trace-step enums for pronunciation playback
- add third-party frontend speech libraries unless the native browser API proves insufficient during implementation

If future work needs downloadable audio or provider-backed speech, that should be a separate story with explicit contract planning.

### Review Intelligence From Story 6.2

The Story 6.2 code review deferred a few low-risk items in [deferred-work.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/implementation-artifacts/deferred-work.md). Do not let this story deepen those weak spots unnecessarily:

- avoid making playback cleanup more brittle by layering more behavior onto the current ref-callback pattern without simplifying it
- prefer stable line identifiers over keys that depend on render order if the new sequencing state needs lookup maps
- add explicit test coverage for event-driven state changes such as `onend`, interruption, and any `voiceschanged` interaction that becomes relevant during page playback

### Relevant Existing Files

- [frontend/src/features/process/components/UploadForm.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/features/process/components/UploadForm.jsx)
- [frontend/src/styles/main.css](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/styles/main.css)
- [frontend/src/__tests__/features/process/upload-form.test.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/__tests__/features/process/upload-form.test.jsx)
- [backend/app/schemas/process.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/schemas/process.py)
- [backend/app/api/v1/process.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/api/v1/process.py)

### Suggested Frontend Test Coverage

- Page-level control renders only when grouped lines are available
- `Play Page` starts with the first grouped line and advances to the next line on `onend`
- Final line completion resets the page-playing state and clears the active line
- Stopping page playback cancels the current utterance and prevents further advancement
- Starting a specific line while page playback is active cancels the sequence and switches to line-only playback
- Starting page playback while a specific line is active cancels the line and begins the full sequence from the first grouped line
- Unsupported-browser and no-voice fallbacks disable the page-level control without breaking grouped rendering

### Suggested Implementation Plan

1. Refactor the current pronunciation logic just enough to support both line-level and page-level playback from one source of truth.
2. Add a page-level control near the grouped result heading and wire it to sequential line playback.
3. Add a subtle active-line visual treatment and any required page-control styling in `main.css`.
4. Extend the existing speech-synthesis mocks and frontend tests for sequence advancement, stop/reset behavior, switching between line/page playback, and fallback handling.
5. Run the existing frontend test suite and targeted backend regression tests to confirm there is still no contract churn.

### References

- Epic/story source: [epics.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/epics.md)
- Sprint change proposal: [sprint-change-proposal-2026-03-29-translation-release.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-29-translation-release.md)
- PRD: [prd.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/prd.md)
- Architecture: [architecture.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/architecture.md)
- UX guidance: [ux-design-specification.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/ux-design-specification.md)
- Previous related implementation context: [4-2-preserve-text-line-layout-in-ocr-and-pinyin-results.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/implementation-artifacts/4-2-preserve-text-line-layout-in-ocr-and-pinyin-results.md)
- Previous related implementation context: [6-1-add-english-translation-below-chinese-characters.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/implementation-artifacts/6-1-add-english-translation-below-chinese-characters.md)
- Previous related implementation context: [6-2-add-per-line-pronunciation-playback-controls.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/implementation-artifacts/6-2-add-per-line-pronunciation-playback-controls.md)
- Deferred review follow-ups: [deferred-work.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/implementation-artifacts/deferred-work.md)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-03-30: Story 6.3 context created from Epic 6, Story 6.1 and 6.2 artifacts, the translation-release sprint change proposal, current frontend pronunciation implementation, deferred review notes, and project UX/architecture constraints.
- 2026-03-30: Implemented shared line/page playback orchestration in `UploadForm.jsx`, added page playback UI and active-line styling, and extended Vitest coverage for sequential playback, cancellation, fallback, and line/page switching.
- 2026-03-30: `npm test -- --run src/__tests__/features/process/upload-form.test.jsx`, `npm test`, and `npm run lint` passed in `frontend/`. Backend `python -m pytest` could not be validated because the local backend environment currently fails test collection with pre-existing import/native-extension issues (`app`/`helpers` path resolution plus missing compiled `grpc`/`pydantic_core` modules).

### Implementation Plan

- 2026-03-30: Extend the existing browser speech-synthesis flow to support page-level sequential playback while keeping the backend contract unchanged and preserving current line-level playback behavior.

### Completion Notes List

- Added shared pronunciation state that supports both single-line playback and full-page sequential playback while preserving the existing browser speech path and unchanged backend contracts.
- Added a page-level `Play Page` / `Stop Page` control, mutual exclusion between page and line playback, automatic line-to-line advancement on `onend`, and immediate reset on stop/result replacement/error.
- Added a subtle active-line visual state and preserved the flat non-grouped reading fallback so page playback only appears for grouped line output.
- Added regression coverage for sequential playback, page stop behavior, page-to-line switching, line-to-page switching, and disabled fallback states.
- Frontend validation is green (`npm test`, targeted upload-form tests, and `npm run lint`), but backend regression validation remains blocked by the current local test environment rather than by this frontend-only story.

### File List

- _bmad-output/implementation-artifacts/6-3-add-full-page-sequential-pronunciation-playback.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- frontend/src/__tests__/features/process/upload-form.test.jsx
- frontend/src/features/process/components/UploadForm.jsx
- frontend/src/styles/main.css

### Change Log

- 2026-03-30: Created Story 6.3 as an inferred Epic 6 follow-on for page-level sequential pronunciation playback using the existing frontend speech-synthesis foundation.
- 2026-03-30: Implemented page-level sequential pronunciation playback in the frontend, added active-line styling, and expanded regression coverage for sequence advancement, cancellation, and fallback behavior.
