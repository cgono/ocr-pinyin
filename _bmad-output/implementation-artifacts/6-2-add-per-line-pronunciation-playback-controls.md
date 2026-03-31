# Story 6.2: Add Per-Line Pronunciation Playback Controls

Status: done

## Story

As Clint,
I want to play back the pronunciation for each rendered line of Chinese text,
so that I can hear the line while following the page without leaving the app.

## Acceptance Criteria

1. **Given** a successful OCR + pinyin result with grouped lines, **When** the browser supports speech synthesis, **Then** each rendered line group includes a pronunciation playback control **And** activating the control speaks that line's combined Chinese source text without changing the API response contract.

2. **Given** a rendered line group contains multiple `PinyinSegment` items with the same `line_id`, **When** pronunciation playback is triggered for that line, **Then** the spoken text is built from the concatenated `source_text` values for that line group in order **And** playback is scoped to that line only.

3. **Given** pronunciation playback is already active for one line, **When** the user starts playback for another line or stops the current line, **Then** the previous utterance is cancelled **And** the UI state updates so only the active line is shown as playing.

4. **Given** the browser does not support speech synthesis, cannot find a suitable Chinese voice, or playback fails, **When** the result is displayed or playback is attempted, **Then** the existing reading result remains fully usable **And** pronunciation controls are disabled or hidden with a non-blocking fallback message **And** no backend error or response-contract change is introduced.

5. **Given** all existing frontend and backend tests run, **When** story 6.2 is implemented, **Then** all existing tests continue to pass.

## Tasks / Subtasks

- [x] Add frontend-only pronunciation playback orchestration without changing the backend contract (AC: 1, 4, 5)
  - [x] Keep `/v1/process`, `ProcessResponse`, and `PinyinSegment` unchanged for this story
  - [x] Do not add a backend audio provider, audio storage, or generated audio URLs in this story
  - [x] Keep the feature entirely in the existing frontend result experience

- [x] Add a line-level playback helper that reuses the existing grouped rendering model (AC: 1, 2, 3, 5)
  - [x] Reuse `groupSegmentsByLine(...)` in [frontend/src/features/process/components/UploadForm.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/features/process/components/UploadForm.jsx)
  - [x] Build spoken text from the grouped line's concatenated `source_text` values in segment order
  - [x] Track exactly one active utterance at a time and cancel any previous utterance before starting a new one
  - [x] Ensure playback is cleaned up if the component unmounts or the result set changes

- [x] Render accessible playback controls inside each `.pinyin-line-group` (AC: 1, 2, 3, 4, 5)
  - [x] Add a compact control per rendered line group in [frontend/src/features/process/components/UploadForm.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/features/process/components/UploadForm.jsx)
  - [x] Provide an accessible label that identifies the line being played, for example using the Chinese source text
  - [x] Reflect playing/stopped/disabled state in the button text or ARIA state
  - [x] Keep the current pinyin, hanzi, and translation layout intact

- [x] Add non-blocking fallback behavior for unsupported browsers or missing voices (AC: 4, 5)
  - [x] Detect `window.speechSynthesis` support before rendering active controls
  - [x] Attempt to select an available Chinese-capable voice if one exists
  - [x] If no suitable voice is available, disable or hide the control and optionally show a brief inline note
  - [x] Treat speech synthesis errors as local UI failures only; never degrade the processed result status

- [x] Add styling for pronunciation controls in the existing result view (AC: 1, 3, 4, 5)
  - [x] Update [frontend/src/styles/main.css](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/styles/main.css) with a small secondary control style that fits inside `.pinyin-line-group`
  - [x] Keep the control visually subordinate to the reading output
  - [x] Preserve mobile tap targets and current result spacing

- [x] Add regression coverage for supported, unsupported, and interruption paths (AC: 1, 2, 3, 4, 5)
  - [x] Extend [frontend/src/__tests__/features/process/upload-form.test.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/__tests__/features/process/upload-form.test.jsx) with grouped playback control rendering
  - [x] Mock `window.speechSynthesis` and `SpeechSynthesisUtterance` to cover play, stop, and interrupt behavior
  - [x] Add coverage for unsupported-browser or no-voice fallback behavior
  - [x] Confirm existing backend tests remain unchanged and green because this story does not alter server contracts

### Review Findings

- [x] [Review][Patch] `ignoreNextSpeechErrorRef` is reset to `false` immediately after `cancelPlayback()` in `handleLinePlayback`, defeating the flag if the browser fires `onerror` asynchronously for the cancelled utterance [frontend/src/features/process/components/UploadForm.jsx]
- [x] [Review][Patch] Dead code: `{!lineGroups && pinyinSegments.map(...)}` branch in render never executes — `groupSegmentsByLine` always returns an array, never `null` or `undefined` [frontend/src/features/process/components/UploadForm.jsx]
- [x] [Review][Patch] Test fixture `GROUPED_PLAYBACK_SUCCESS_RESPONSE` has duplicate `translation_text: 'Teacher'` on both segments of line 0 — masks any regression in translation-selection logic [frontend/src/__tests__/features/process/upload-form.test.jsx]
- [x] [Review][Defer] `cancelPlaybackIfActiveRef.current` reassigned on every render (stable-ref-callback pattern) — works correctly but any future non-ref closure dependency will silently break cleanup — deferred, pre-existing architectural choice
- [x] [Review][Defer] No `:active` CSS press state on `.pinyin-playback-button` — touch users see no feedback while holding — deferred, cosmetic
- [x] [Review][Defer] No test for `voiceschanged` event firing during active playback — unlikely but untested state transition — deferred, low priority
- [x] [Review][Defer] `lineKey` includes `groupIndex` alongside `line_id` — could mismatch if group order shifts; unlikely in practice — deferred, low risk
- [x] [Review][Defer] Fallback message not shown before first successful result — `speechFallbackMessage` is set on mount but the `<p>` is gated on `lineGroups` being truthy inside a `pinyinSegments.length > 0` block — deferred, acceptable UX for story scope

## Dev Notes

### Story Provenance

Epic 6 only explicitly defined Story 6.1 in [epics.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/epics.md). Story 6.2 is inferred from the approved note in [sprint-change-proposal-2026-03-29-translation-release.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-29-translation-release.md), which reserves `6.2+` for future audio pronunciation work.

To keep the story implementable in the current codebase, scope it to browser speech synthesis rather than a new backend-generated audio pipeline. That delivers audible pronunciation now while preserving room for richer provider-backed audio later.

### Current Brownfield Reality

The live result UI still renders inside [frontend/src/features/process/components/UploadForm.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/features/process/components/UploadForm.jsx), not in a dedicated result view component from the aspirational architecture. Implement this story against the actual brownfield structure.

Story 6.1 already established the current grouped rendering model:

- Each line is represented by adjacent `PinyinSegment` items sharing the same `line_id`
- `groupSegmentsByLine(...)` assembles those line groups in the frontend
- Translation is rendered once per `.pinyin-line-group`

Pronunciation controls should extend that exact grouping model rather than introduce a second line-assembly path.

### Playback Scope and Source Text Rules

- Playback is line-level, not per character and not whole-page.
- The spoken string should be built from the grouped line's `source_text` values in their rendered order.
- Use Chinese source text for speech synthesis, not `pinyin_text`; browser voices pronounce Hanzi more reliably than romanized pinyin.
- The playback control should operate only on grouped results. If `line_id` data is absent and the UI falls back to flat ruby rendering, do not invent a separate flat playback mode in this story.

### State Management Guardrails

- Maintain at most one active utterance at a time.
- Starting playback for a new line must cancel any existing utterance before beginning the new line.
- Stopping playback must clear active-line UI state immediately.
- Register `onend` and `onerror` handlers so the UI resets even if the browser terminates playback asynchronously.
- Cancel any active utterance on component unmount and when a new response replaces the current line groups.

### Browser API Guidance

Use the built-in Web Speech API:

- `window.speechSynthesis`
- `SpeechSynthesisUtterance`
- `speechSynthesis.getVoices()`
- `speechSynthesis.cancel()`
- `speechSynthesis.speak()`

Implementation constraints:

- Browser support is inconsistent, so unsupported paths must degrade quietly.
- Voice lists may load asynchronously; account for the case where `getVoices()` is initially empty.
- Prefer a Chinese voice (`zh`, `zh-CN`, `zh-TW`) when available.
- Do not block rendering while voice discovery resolves.

### Accessibility and UX Guardrails

- Controls must be keyboard accessible.
- Use a descriptive accessible name, such as "Play pronunciation for 老师叫".
- Reflect active state clearly, such as `Play` vs `Stop`, or `aria-pressed` while playing.
- Keep the control visually secondary so the reading layout remains the primary focus.
- Do not surface modal errors or toast-style disruptions for playback problems; an inline disabled state or subdued helper text is sufficient.

### Architecture and Contract Boundaries

This story should not:

- change the backend schema
- add new API fields such as `audio_url`, `audio_status`, or `pronunciation_available`
- add new diagnostics trace steps
- add persistence for generated audio
- add third-party frontend speech libraries unless native browser APIs prove inadequate during implementation

If a future story adds server-generated audio files, that should be a separate architectural step with explicit contract planning.

### Relevant Existing Files

- [frontend/src/features/process/components/UploadForm.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/features/process/components/UploadForm.jsx)
- [frontend/src/styles/main.css](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/styles/main.css)
- [frontend/src/__tests__/features/process/upload-form.test.jsx](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/__tests__/features/process/upload-form.test.jsx)
- [backend/app/schemas/process.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/schemas/process.py)
- [backend/app/api/v1/process.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/api/v1/process.py)
- [backend/app/services/translation_service.py](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/services/translation_service.py)

### Suggested Frontend Test Coverage

- Grouped result renders one pronunciation control per `.pinyin-line-group`
- Triggering a line control calls `speechSynthesis.cancel()` before `speak()` when another line was active
- Triggering the active line again stops playback and resets UI state
- `onend` resets the playing state
- Unsupported browser path renders no active control or a disabled control
- No-voice fallback path does not break grouped rendering

### Suggested Implementation Plan

1. Add a small speech-synthesis helper inside `UploadForm.jsx` or extract a focused helper module if the component becomes too dense.
2. Wire per-line playback controls into the existing grouped render path only.
3. Add minimal control styling in `main.css`.
4. Add mocked frontend tests for play, stop, interrupt, and fallback behavior.
5. Run the existing frontend test suite and targeted backend regression tests to confirm no contract churn.

### References

- Epic/story source: [epics.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/epics.md)
- Sprint change proposal: [sprint-change-proposal-2026-03-29-translation-release.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-29-translation-release.md)
- PRD: [prd.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/prd.md)
- Architecture: [architecture.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/architecture.md)
- UX guidance: [ux-design-specification.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/planning-artifacts/ux-design-specification.md)
- Previous related implementation context: [4-2-preserve-text-line-layout-in-ocr-and-pinyin-results.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/implementation-artifacts/4-2-preserve-text-line-layout-in-ocr-and-pinyin-results.md)
- Previous related implementation context: [6-1-add-english-translation-below-chinese-characters.md](/Users/clint/Documents/GitHub/ocr-pinyin/_bmad-output/implementation-artifacts/6-1-add-english-translation-below-chinese-characters.md)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-03-30: Story 6.2 context created from Epic 6, the approved translation-release change proposal, Story 6.1 implementation context, current frontend result rendering, and current backend response contracts.
- 2026-03-30: Added browser speech-synthesis playback orchestration in the grouped result view, extended frontend regression coverage, ran `npm test`, `npm run lint`, and `backend/.venv/bin/pytest`.

### Implementation Plan

- 2026-03-30: Implement browser-based line-level pronunciation playback in the existing grouped frontend result view, keep server contracts unchanged, and add mocked regression coverage for support and fallback behavior.

### Completion Notes List

- Added per-line pronunciation playback controls to grouped pinyin results using the browser Web Speech API only; backend request and response contracts remained unchanged.
- Built spoken line text from grouped `source_text` values in order, kept a single active utterance, and cancelled prior playback when switching lines or stopping.
- Added quiet fallback handling for unsupported browsers, missing Chinese-capable voices, and local playback failures without degrading the result view.
- Added regression tests for supported playback, stop/interruption behavior, and fallback states; full frontend and backend suites passed.

### File List

- _bmad-output/implementation-artifacts/6-2-add-per-line-pronunciation-playback-controls.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- frontend/src/features/process/components/UploadForm.jsx
- frontend/src/styles/main.css
- frontend/src/__tests__/features/process/upload-form.test.jsx

### Change Log

- 2026-03-30: Created Story 6.2 as an inferred Epic 6 follow-on for browser-based per-line pronunciation playback controls.
- 2026-03-30: Implemented frontend-only line pronunciation playback controls, fallback states, and regression coverage; story moved to review.
