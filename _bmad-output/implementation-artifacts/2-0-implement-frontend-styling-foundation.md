# Story 2.0: Implement Frontend Styling Foundation

Status: done

## Story

As Clint,
I want a mobile-first styling foundation applied to the frontend upload and result flow,
so that the app feels polished, readable, and consistent with the UX design specification.

## Acceptance Criteria

1. Given I open the app on iPhone Safari, when the main process screen loads, then layout is single-column, touch-friendly, and readable without zooming.
2. Given I interact with upload, status, result, and details sections, when states change (idle/loading/success/error), then visual hierarchy and spacing remain consistent across sections.
3. Given the pinyin result is rendered, when text and ruby annotations display, then typography prioritizes pinyin readability and preserves line wrapping for small screens.
4. Given diagnostics are available, when I choose to inspect details, then details remain visually secondary using progressive disclosure styling.
5. Given accessibility checks run, when evaluating contrast and tap targets, then controls meet WCAG AA contrast intent and minimum 44x44 touch target guidance.

## Tasks / Subtasks

- [x] Establish styling baseline and tokens (AC: 1, 2)
  - [x] Add a global stylesheet with spacing, color, and typography tokens for a calm reading-first UI.
  - [x] Replace ad-hoc inline styles in App and UploadForm with semantic class-based styles.
- [x] Style core flow components (AC: 1, 2, 4)
  - [x] Apply consistent styles to page shell, upload actions, status panel, result view, and details section.
  - [x] Ensure loading, success, error, and partial states have clear but low-noise visual treatment.
- [x] Improve pinyin readability styling (AC: 3)
  - [x] Tune ruby typography scale, line-height, and wrapping behavior for small viewport readability.
  - [x] Keep pinyin output dominant over technical metadata.
- [x] Implement accessibility-focused polish (AC: 5)
  - [x] Verify focus-visible states for keyboard/touch-assistive interactions.
  - [x] Ensure button/input tap targets and spacing satisfy mobile ergonomics.
- [x] Add/extend frontend tests (AC: 1-5)
  - [x] Add assertions for state class rendering and details progressive disclosure behavior.
  - [x] Add viewport-oriented smoke expectations for key content visibility.

## Dev Notes

- Source references:
  - `_bmad-output/planning-artifacts/ux-design-specification.md`
  - `_bmad-output/planning-artifacts/epics.md`
- Current implementation is functionally complete for Story 1.5 but relies on minimal inline styles.
- Keep this story focused on presentation and accessibility polish only; no API contract changes.

## File Targets

- `frontend/src/App.jsx`
- `frontend/src/features/process/components/UploadForm.jsx`
- `frontend/src/main.jsx` (if global stylesheet import is needed)
- `frontend/src/styles/*` (new styling files)
- `frontend/src/__tests__/features/process/upload-form.test.jsx`

## Definition of Done

- Visual styling foundation is applied and consistent across the main user flow.
- Existing behavior remains unchanged except for UI presentation improvements.
- Frontend lint/tests pass with updated assertions for styled states.

## Dev Agent Record

### Implementation Plan

Implemented Night Comfort palette (Direction 5) with Reader First layout structure (Direction 4) per UX design specification, using plain CSS with CSS custom properties (design tokens). No new runtime dependencies added.

- Created `frontend/src/styles/tokens.css` — CSS custom properties for all design tokens: Night Comfort colors, 8px-base spacing scale, system font stack, pinyin-optimized typography, WCAG touch target minimum.
- Created `frontend/src/styles/main.css` — full component styling: app shell, buttons (primary/secondary), upload actions, file input, status panel with state modifiers, result view, pinyin result, details section.
- Updated `frontend/src/main.jsx` — imports global stylesheet.
- Updated `frontend/src/App.jsx` — replaced inline styles with `.app-shell` / `.app-title` classes.
- Updated `frontend/src/features/process/components/UploadForm.jsx` — replaced all inline styles with semantic CSS classes; added `statusPanelClass()` helper to derive state modifier (`.status-panel--idle/loading/success/error`) from mutation state; removed inline styles from ruby `<rt>` elements (now handled by CSS).
- Updated `frontend/src/__tests__/features/process/upload-form.test.jsx` — added 7 new assertions in a dedicated `'UploadForm styling and accessibility'` describe block covering: semantic class structure, all 4 status panel state classes, pinyin content class, details progressive disclosure with `.details-section` class, key content accessibility smoke.

All 22 tests pass; ESLint clean.

### Completion Notes

✅ All 5 tasks and 10 subtasks complete.
✅ AC 1–5 satisfied:
  - AC1: single-column `.app-shell` max-width 480px, mobile-first layout.
  - AC2: state modifier classes (--idle/--loading/--success/--error) provide consistent visual hierarchy.
  - AC3: `.pinyin-result__content` at 1.4rem / 2.8 line-height with `word-break: break-word`; rt inherits secondary color via CSS.
  - AC4: `<details class="details-section">` collapsed by default; visually secondary via color-text-secondary.
  - AC5: all buttons/inputs use `min-height: 44px` (--tap-target-min); focus-visible outlines on all interactive elements; WCAG AA Night Comfort palette with strong contrast ratios.
✅ All 22 frontend tests pass; lint clean.
✅ No new runtime dependencies added.

## File List

- `frontend/src/styles/tokens.css` (new)
- `frontend/src/styles/main.css` (new)
- `frontend/src/main.jsx` (modified)
- `frontend/src/App.jsx` (modified)
- `frontend/src/features/process/components/UploadForm.jsx` (modified)
- `frontend/src/__tests__/features/process/upload-form.test.jsx` (modified)

## Change Log

- 2026-03-23: Implemented frontend styling foundation — Night Comfort palette, CSS design tokens, semantic class-based styles, status panel state modifiers, pinyin readability tuning, accessibility polish (focus-visible, 44px tap targets), 7 new test assertions.
