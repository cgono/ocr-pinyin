# Story 4.1: Camera Capture Flow — Preview, Crop, Auto-Submit, Loading Spinner, Startup Ping

Status: done

## Story

As Clint,
I want to preview and crop a captured photo before it is submitted, see a loading animation while processing, and have the backend warmed up by the time I take my first photo,
So that the capture-to-result flow is smooth and I don't accidentally send irrelevant parts of the image to OCR.

## Acceptance Criteria

1. **Given** I tap Take Photo and the camera opens, **When** I take a photo and the camera closes, **Then** a preview of the captured image is displayed **And** crop handles are shown so I can select the region to submit.

2. **Given** a preview with crop handles is shown, **When** I adjust the crop region and confirm, **Then** the cropped image is submitted to `POST /v1/process` automatically (no additional Submit tap required for the camera flow).

3. **Given** I confirm the photo (with or without crop adjustment), **When** the upload request is in flight, **Then** a visible loading spinner (not just text) is displayed in the status panel.

4. **Given** a crop preview is displayed, **When** the user dismisses without confirming, **Then** no upload occurs and the user is returned to the initial state.

5. **Given** the app loads in the browser, **When** the page mounts, **Then** the frontend silently calls `GET /v1/health` in the background to trigger a Render wake-up before the user submits their first photo.

6. **Given** the startup health ping fails or times out, **When** the failure occurs, **Then** the failure is silently ignored with no user-visible error and no blocking of subsequent usage.

## Tasks / Subtasks

- [x] Add `react-image-crop` package to `frontend/package.json` (AC: 1, 2)
  - [x] Run `npm install react-image-crop` in `frontend/`
  - [x] Verify it appears in `package.json` dependencies and `package-lock.json` is updated

- [x] Add `getHealthStatus` to `frontend/src/lib/api-client.js` (AC: 5, 6)
  - [x] Export `async function getHealthStatus()` that fetches `GET ${API_BASE}/v1/health`
  - [x] Function resolves (does not throw) on any response — caller handles errors silently

- [x] Create `frontend/src/features/process/components/CropPreview.jsx` (AC: 1, 2, 4)
  - [x] Accept props: `imageUrl` (blob URL), `onConfirm(croppedFile)`, `onDismiss()`
  - [x] Use `react-image-crop` `ReactCrop` component with `aspect` undefined (freeform crop)
  - [x] Default to full-image crop selection on mount (no forced crop required)
  - [x] "Confirm" button: uses canvas to extract cropped region, converts to `Blob`, calls `onConfirm(croppedFile)`
  - [x] "Cancel" button: calls `onDismiss()` with no side effects
  - [x] Revoke the `imageUrl` object URL in a cleanup `useEffect` (prevent memory leaks)
  - [x] Apply `.crop-preview` CSS class; mobile-friendly layout

- [x] Modify `frontend/src/features/process/components/UploadForm.jsx` (AC: 1, 2, 3, 4)
  - [x] Add `cropImageUrl` state (string | null) — set when camera capture fires, cleared on confirm or dismiss
  - [x] Separate camera input `onChange` handler (`handleCameraCapture`) from file upload `onChange` handler (`handleFileChange`)
  - [x] `handleCameraCapture`: set `cropImageUrl` to blob URL of captured file (do NOT auto-submit yet); do NOT call `mutation.mutate()`
  - [x] When `cropImageUrl` is set: render `<CropPreview>` instead of the normal result/status area
  - [x] `CropPreview` `onConfirm`: receive cropped `File/Blob`, call `mutation.mutate(cropped)`, clear `cropImageUrl`, set `file` state for `previewUrl` display
  - [x] `CropPreview` `onDismiss`: clear `cropImageUrl`, clear `file` state, reset `previewUrl`, reset mutation (return to idle)
  - [x] `handleFileChange` (upload-file path): retain existing behavior — set file, no auto-submit (user must tap Submit)
  - [x] Remove legacy auto-submit logic on `handleFileChange` that triggered only for `ocr_low_confidence` — it was identified as a bug and the camera path now handles auto-submit properly
  - [x] In status panel loading state: render a visible spinner element (`<span className="loading-spinner" aria-hidden="true" />`) alongside the "Uploading image..." text (AC: 3)

- [x] Modify `frontend/src/App.jsx` (AC: 5, 6)
  - [x] Import `useEffect` from React and `getHealthStatus` from `lib/api-client`
  - [x] Add `useEffect(() => { getHealthStatus().catch(() => {}) }, [])` — fires once on mount, all errors silently caught

- [x] Add CSS for loading spinner to `frontend/src/styles/index.css` (AC: 3)
  - [x] `.loading-spinner` — small rotating circle, calm/minimal animation consistent with Night Comfort palette

- [x] Update `frontend/src/__tests__/features/process/upload-form.test.jsx` (regression)
  - [x] Ensure existing tests still pass after split of camera/upload handlers
  - [x] Add test: camera capture shows CropPreview (not immediate submit)
  - [x] Add test: CropPreview dismiss resets state to idle (no mutation fired)
  - [x] Add test: loading spinner element is present when `isPending`

## Dev Notes

### Bug Being Fixed

`handleFileChange` in the current `UploadForm.jsx:61–68` had a conditional auto-submit that only fired when `ocr_low_confidence` was in the previous result's warnings. Normal camera capture set the file and preview but required a separate Submit tap. This story replaces that conditional with a clean camera-specific handler that always shows CropPreview after capture.

The "Upload image" file input path intentionally retains the existing Submit behavior — only the camera capture path gains auto-submit after crop confirmation.

### Critical Files to Touch

| File | Action | Reason |
|------|--------|--------|
| `frontend/src/features/process/components/UploadForm.jsx` | Modify | Split camera/upload handlers, add CropPreview rendering, add spinner |
| `frontend/src/features/process/components/CropPreview.jsx` | Create (new) | Image crop UI component |
| `frontend/src/App.jsx` | Modify | Add startup health ping useEffect |
| `frontend/src/lib/api-client.js` | Modify | Add `getHealthStatus` function |
| `frontend/src/styles/index.css` | Modify | Add `.loading-spinner` CSS animation |
| `frontend/src/__tests__/features/process/upload-form.test.jsx` | Update | Cover new camera flow + spinner |

### Library: react-image-crop

**Package:** `react-image-crop` (not yet in `package.json` — must be added)

**Key API:**
```jsx
import ReactCrop, { makeAspectCrop, centerCrop } from 'react-image-crop'
import 'react-image-crop/dist/ReactCrop.css'

const [crop, setCrop] = useState()  // undefined = full image selected by default

<ReactCrop crop={crop} onChange={c => setCrop(c)} onComplete={c => setCompletedCrop(c)}>
  <img ref={imgRef} src={imageUrl} />
</ReactCrop>
```

**Crop-to-Blob pattern (canvas extraction):**
```js
async function cropToBlob(imgEl, completedCrop, mimeType = 'image/jpeg') {
  const canvas = document.createElement('canvas')
  const scaleX = imgEl.naturalWidth / imgEl.width
  const scaleY = imgEl.naturalHeight / imgEl.height
  canvas.width = completedCrop.width
  canvas.height = completedCrop.height
  const ctx = canvas.getContext('2d')
  ctx.drawImage(
    imgEl,
    completedCrop.x * scaleX, completedCrop.y * scaleY,
    completedCrop.width * scaleX, completedCrop.height * scaleY,
    0, 0, completedCrop.width, completedCrop.height
  )
  return new Promise(resolve => canvas.toBlob(resolve, mimeType, 0.9))
}
```

**If no crop is set / completedCrop is undefined:** treat as full-image (no crop applied) — pass the original file directly to `onConfirm`.

**Important:** import the ReactCrop CSS — `import 'react-image-crop/dist/ReactCrop.css'` — inside `CropPreview.jsx`.

### State Flow for Camera Path

```
User taps "Take Photo"
  → cameraInputRef.current.click()
  → Camera opens
  → User takes photo
  → handleCameraCapture fires
    → file = event.target.files[0]
    → cropImageUrl = URL.createObjectURL(file)
    → CropPreview renders (mutation NOT called yet)

User in CropPreview:
  Option A: Confirm (with or without adjustment)
    → cropToBlob(imgEl, completedCrop) → croppedBlob
    → onConfirm(croppedBlob) called
    → mutation.mutate(croppedBlob)
    → cropImageUrl = null
    → file = croppedBlob (for previewUrl display post-result)

  Option B: Cancel/Dismiss
    → onDismiss() called
    → cropImageUrl = null
    → file = null
    → previewUrl = null
    → mutation.reset() (back to idle state)
```

### Startup Health Ping

The health ping in `App.jsx` is fire-and-forget:
```jsx
useEffect(() => {
  getHealthStatus().catch(() => {})
}, [])
```

`getHealthStatus` in `api-client.js` should be a simple fetch that never throws — wrap the internal fetch in try/catch and resolve regardless:
```js
export async function getHealthStatus() {
  try {
    await fetch(`${API_BASE}/v1/health`)
  } catch {
    // intentionally silent
  }
}
```

This means the `catch(() => {})` in `App.jsx` is a safety belt, not the primary error handler.

### Loading Spinner

The current loading state in `UploadForm.jsx:124–126` shows text only:
```jsx
{mutation.isPending && (
  <p className="status-panel__message">Uploading image...</p>
)}
```

Replace with:
```jsx
{mutation.isPending && (
  <p className="status-panel__message">
    <span className="loading-spinner" aria-hidden="true" />
    Uploading image...
  </p>
)}
```

CSS for `.loading-spinner` should be a small rotating border circle, consistent with the Night Comfort palette (calm/restrained — not large or flashy). Example:
```css
.loading-spinner {
  display: inline-block;
  width: 1em;
  height: 1em;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  vertical-align: middle;
  margin-right: 0.4em;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
```

### Architecture Compliance

- **TanStack Query:** `mutation.mutate(croppedFile)` is the correct call — `mutationFn: (nextFile = file) => submitProcessRequest(nextFile)` already accepts a parameter. No changes to mutation config needed.
- **Loading states (from architecture):** Three states — `idle`, `processing`, `completed/failed` — must all remain visible. Spinner adds to `processing` state; it does not replace text.
- **Disable duplicate submit while processing:** Already handled by `disabled={mutation.isPending}` on Submit button. CropPreview Confirm button must also be disabled while `mutation.isPending`.
- **Component file naming:** `CropPreview.jsx` — PascalCase, `.jsx` extension, inside `features/process/components/`.
- **API client pattern:** All backend calls go through `lib/api-client.js`. `getHealthStatus` must live there, not be inlined in `App.jsx`.

### Testing Notes

- Existing tests in `upload-form.test.jsx` test the file upload path — these must not break.
- Camera path uses `cameraInputRef.current.click()` — in tests, simulate `onChange` on the hidden camera input directly.
- CropPreview involves a canvas operation; in tests, mock `HTMLCanvasElement.prototype.toBlob` if needed, or test that `onConfirm` is called with a Blob-like argument.
- Health ping test: verify `getHealthStatus` is called once on App mount; since it's fire-and-forget, just confirm the call was made (do not assert on its result).

### Previous Story (4-0) Intelligence

Story 4-0 was documentation only — no frontend patterns were established. The most relevant prior frontend work is the Epic 2–3 merge (commit `4586b23`). The existing `UploadForm.jsx` and `App.jsx` are the canonical starting point.

### Git Intelligence (Recent)

- `3857eaa` — Story 4-0: documentation only, no source file changes
- `d54209b` — pin PYTHON_VERSION and UV_VERSION in render.yaml (infra only)
- `793203b/2583eb3/759c3c6` — render.yaml free plan fixes (infra only)
- `4586b23` — Epic 3 merge: established current `UploadForm.jsx`, `App.jsx`, `api-client.js` patterns

The working `UploadForm.jsx` was written in the Epic 3 merge. Read it carefully before modifying — the `cameraInputRef`, `previewUrl` useEffect, and `useMutation` config are the patterns to extend, not replace.

### Project Structure Notes

Architecture calls for:
- `frontend/src/features/process/components/` — feature-specific UI components
- `frontend/src/lib/api-client.js` — all backend calls, no direct fetch() calls in components
- `frontend/src/__tests__/features/process/` — tests for process feature components

No backend changes in this story. This is entirely frontend.

### References

- Sprint change proposal: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-28.md` (Section 4, Story 4.1)
- Current UploadForm: `frontend/src/features/process/components/UploadForm.jsx`
- Current App: `frontend/src/App.jsx`
- API client: `frontend/src/lib/api-client.js`
- Architecture loading states: `_bmad-output/planning-artifacts/architecture.md#Loading-State-Patterns`
- UX component spec for ProcessingStateStrip: `_bmad-output/planning-artifacts/ux-design-specification.md#ProcessingStateStrip`
- UX design direction (Night Comfort): `_bmad-output/planning-artifacts/ux-design-specification.md#Design-Direction-Decision`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `npm install react-image-crop`
- `npm test`
- `npm run lint`

### Completion Notes List

- Added a new `CropPreview` component using `react-image-crop`, freeform crop selection, canvas export, and blob URL cleanup.
- Split camera capture from manual upload so camera images now preview, crop, and auto-submit on confirm, while file uploads still require the Submit button.
- Added a silent startup `GET /v1/health` warm-up call plus a visible loading spinner in the processing state.
- Expanded frontend tests to cover crop preview, dismiss/reset behavior, camera confirm submission, spinner rendering, and app mount health ping.

### File List

- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/src/App.jsx`
- `frontend/src/lib/api-client.js`
- `frontend/src/features/process/components/CropPreview.jsx`
- `frontend/src/features/process/components/UploadForm.jsx`
- `frontend/src/styles/main.css`
- `frontend/src/__tests__/app.test.jsx`
- `frontend/src/__tests__/features/process/upload-form.test.jsx`

### Change Log

- 2026-03-28: Implemented camera crop preview flow, startup health warm-up, loading spinner UI, dependency/test updates, and marked story ready for review.
