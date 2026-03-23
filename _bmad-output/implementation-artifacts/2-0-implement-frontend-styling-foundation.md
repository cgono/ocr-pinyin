# Story 2.0: Implement Frontend Styling Foundation

Status: draft

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

- [ ] Establish styling baseline and tokens (AC: 1, 2)
  - [ ] Add a global stylesheet with spacing, color, and typography tokens for a calm reading-first UI.
  - [ ] Replace ad-hoc inline styles in App and UploadForm with semantic class-based styles.
- [ ] Style core flow components (AC: 1, 2, 4)
  - [ ] Apply consistent styles to page shell, upload actions, status panel, result view, and details section.
  - [ ] Ensure loading, success, error, and partial states have clear but low-noise visual treatment.
- [ ] Improve pinyin readability styling (AC: 3)
  - [ ] Tune ruby typography scale, line-height, and wrapping behavior for small viewport readability.
  - [ ] Keep pinyin output dominant over technical metadata.
- [ ] Implement accessibility-focused polish (AC: 5)
  - [ ] Verify focus-visible states for keyboard/touch-assistive interactions.
  - [ ] Ensure button/input tap targets and spacing satisfy mobile ergonomics.
- [ ] Add/extend frontend tests (AC: 1-5)
  - [ ] Add assertions for state class rendering and details progressive disclosure behavior.
  - [ ] Add viewport-oriented smoke expectations for key content visibility.

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
