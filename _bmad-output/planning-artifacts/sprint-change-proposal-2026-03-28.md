# Sprint Change Proposal — 2026-03-28

**Trigger:** Live MVP testing by Clint and wife
**Date:** 2026-03-28
**Scope:** Minor — direct implementation by dev agent
**Epic affected:** Epic 4

---

## Section 1: Issue Summary

Five gaps identified after sharing the live MVP with a first-time user:

1. **Bug — Take Photo doesn't trigger upload.**
   `handleFileChange` in `UploadForm.jsx:65–67` only auto-submits when the previous result had `ocr_low_confidence` warnings. Normal camera capture sets the file and preview but does not call `mutation.mutate()`. Users must separately tap "Submit", which is not obvious to first-time users.

2. **UX Gap — No photo preview or crop before submission.**
   After taking a photo, users cannot verify what was captured or crop out irrelevant content (e.g., hands, furniture, adjacent pages) before sending to OCR.

3. **UX Gap — No loading animation.**
   The status panel shows text-only "Uploading image..." during `mutation.isPending` with no visual spinner.

4. **UX Gap — Pinyin results lose original line layout.**
   OCR segments are rendered inline. If the source text had three distinct lines, the result merges them into one run, making it harder to follow along with the physical book. For example:

   Source layout in book:
   ```
   老师叫
   同学们好
   我们开始上课了
   ```

   Current result:
   ```
   老师叫 同学们好 我们开始上课了
   ```

5. **Performance concern — No backend warm-up on startup.**
   Render free tier spins down after 15 minutes of inactivity. Wake-up takes ~1 minute. The frontend currently does nothing on startup to trigger a warm-up, so the first request after an idle period bears the full cold-start cost.
   Note: `healthCheckPath: /v1/health` is already correctly configured in `render.yaml` — no change needed there.

**Deferred / accepted items:**
- **Bot prevention:** Epic 4's cost guardrail stories (budget threshold 4-5, input size limits 4-6) provide partial protection. Manual Render suspension remains the escalation path for MVP. A dedicated rate-limiting story can be considered for Epic 5 if usage warrants it.
- **Story 4-0 (sprint change process docs):** Already created as `ready-for-dev` in `sprint-status.yaml` — the retrospective action item is resolved, no further action needed.

---

## Section 2: Impact Analysis

### Epic Impact

Epic 4 goal statement is amended to include UX polish from live MVP testing. Two new stories are inserted before the cost guardrail stories. Existing cost stories 4-1 through 4-4 are renumbered 4-3 through 4-6 with no content changes.

### Story Impact

| Story | Change |
|-------|--------|
| 4-1 (new) | Camera capture flow: preview → crop → auto-submit + loading spinner + startup wake-up ping |
| 4-2 (new) | Preserve text line layout in OCR and pinyin results |
| 4-3 (was 4-1) | Estimate per-request processing cost — content unchanged |
| 4-4 (was 4-2) | Track daily aggregate usage cost — content unchanged |
| 4-5 (was 4-3) | Enforce or warn on daily budget threshold — content unchanged |
| 4-6 (was 4-4) | Restrict oversized or high-cost inputs — content unchanged |

### Artifact Conflicts

| Artifact | Change needed |
|----------|--------------|
| `_bmad-output/planning-artifacts/epics.md` | Add Stories 4.1 and 4.2; renumber cost stories 4.1→4.3 through 4.4→4.6; amend Epic 4 goal |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | Add new story keys; renumber cost story keys; update `last_updated` |
| PRD | No changes — FR12, FR14, FR15 implicitly cover these improvements |
| Architecture | No structural changes; minor OCR service schema addition for Story 4-2 |
| UX Design | No spec changes — changes align with "continuous reading loop" and "iPhone Safari mobile-first" principles |
| `render.yaml` | No change — `healthCheckPath: /v1/health` already configured |

### Technical Impact

- **Story 4-1:** Frontend only — `UploadForm.jsx` (capture flow), new `CropPreview.jsx` component (image crop UI), `App.jsx` (startup health ping), CSS
- **Story 4-2:** Backend `ocr_service.py` (expose line grouping from GCV response), `schemas/process.py` (add `line_id` to `OcrSegment` and `PinyinSegment`), `UploadForm.jsx` (line-aware rendering)

---

## Section 3: Recommended Approach

**Direct Adjustment** — insert two new stories at the top of Epic 4's story sequence and renumber cost stories. No rollback, no MVP scope reduction needed.

**Rationale:** The MVP is live with real users. Camera flow and layout preservation directly impact the core use case (reading with a child). These gaps should ship before cost guardrail stories, which are backend-only and do not affect current usability. All changes are additive and low-risk — Story 4-1 is entirely frontend; Story 4-2 adds one field to the OCR schema and one rendering change. Effort: Low–Medium. Risk: Low.

---

## Section 4: Detailed Change Proposals

### Story 4.1: Camera Capture Flow — Preview, Crop, Auto-Submit, Loading Spinner, Startup Ping

**Story:**

As Clint,
I want to preview and crop a captured photo before it is submitted, see a loading animation while processing, and have the backend warmed up by the time I take my first photo,
So that the capture-to-result flow is smooth and I don't accidentally send irrelevant parts of the image to OCR.

**Acceptance Criteria:**

**Given** I tap Take Photo and the camera opens
**When** I take a photo and the camera closes
**Then** a preview of the captured image is displayed
**And** crop handles are shown so I can select the region to submit.

**Given** a preview with crop handles is shown
**When** I adjust the crop region and confirm
**Then** the cropped image is submitted to `POST /v1/process` automatically (no additional Submit tap required for the camera flow).

**Given** I confirm the photo (with or without crop adjustment)
**When** the upload request is in flight
**Then** a visible loading spinner (not just text) is displayed in the status panel.

**Given** the app loads in the browser
**When** the page mounts
**Then** the frontend silently calls `GET /v1/health` in the background to trigger a Render wake-up before the user submits their first photo.

**Implementation notes:**
- Use a React image-crop library (e.g., `react-image-crop`) for the crop UI
- Crop produces a new `Blob`/`File` passed directly to `mutation.mutate()`
- "Upload image" file input (non-camera path) retains current explicit Submit behavior — only the camera capture path gains auto-submit
- Startup health ping: add `useEffect` to `App.jsx` that calls the health endpoint once on mount; no result handling needed (fire and forget)

---

### Story 4.2: Preserve Text Line Layout in OCR and Pinyin Results

**Story:**

As Clint,
I want the pinyin result to preserve the original line breaks from the book page,
So that I can follow the result alongside the physical book without mentally re-mapping the layout.

**Acceptance Criteria:**

**Given** OCR extracts text from a page with multiple lines
**When** the result is displayed
**Then** line breaks from the source are preserved in the pinyin output
**And** each original line appears on its own visual row, for example:
```
老师叫
lǎo shī jiào

同学们好
tóng xué men hǎo

我们开始上课了
wǒ men kāi shǐ shàng kè le
```

**Given** OCR returns a single unstructured block with no line metadata
**When** layout cannot be determined
**Then** the result falls back to the current inline rendering with no regression.

**Given** all existing backend and frontend tests run
**When** the schema change is applied
**Then** all existing tests continue to pass.

**Schema change:**

```
OLD OcrSegment: { text, language, confidence }
NEW OcrSegment: { text, language, confidence, line_id: int | null }

OLD PinyinSegment: { source_text, pinyin_text, alignment_status, reason_code }
NEW PinyinSegment: { source_text, pinyin_text, alignment_status, reason_code, line_id: int | null }
```

**Implementation notes:**
- GCV `DOCUMENT_TEXT_DETECTION` response includes line-level structure in `fullTextAnnotation.pages[].blocks[].paragraphs[].lines[]` — the OCR service should assign a sequential `line_id` when building segments from this structure
- `line_id` is `null` when line structure is unavailable (graceful fallback)
- Pinyin service propagates `line_id` from corresponding OCR segment
- Frontend groups segments by `line_id` and renders a `<br>` (or block separator) between line groups

---

### Renumbered Cost Stories (content unchanged)

| New number | Old number | Title |
|-----------|------------|-------|
| Story 4.3 | Story 4.1 | Estimate Per-Request Processing Cost |
| Story 4.4 | Story 4.2 | Track Daily Aggregate Usage Cost |
| Story 4.5 | Story 4.3 | Enforce or Warn on Daily Budget Threshold |
| Story 4.6 | Story 4.4 | Restrict Oversized or High-Cost Inputs |

---

## Section 5: Implementation Handoff

**Scope: Minor** — direct implementation by dev agent.

**Stories to implement:**

| Story | Type | Files affected |
|-------|------|---------------|
| 4-0 | Documentation | `docs/sprint-change-proposal-process.md` (already ready-for-dev) |
| 4-1 | Frontend | `UploadForm.jsx`, new `CropPreview.jsx`, `App.jsx`, CSS |
| 4-2 | Backend + Frontend | `ocr_service.py`, `schemas/process.py`, `UploadForm.jsx` |
| 4-3 through 4-6 | Backend | Cost guardrail stories (unchanged content) |

**Artifact updates required after this proposal is applied:**
1. `epics.md` — add Stories 4.1 and 4.2; renumber cost stories; amend Epic 4 goal
2. `sprint-status.yaml` — add `4-1-camera-capture-flow-...` and `4-2-preserve-text-line-layout-...` as `backlog`; renumber cost story keys to 4-3 through 4-6; update `last_updated`
3. Create story files for Stories 4-1 and 4-2 via `bmad-create-story`

**Success criteria:**
- First-time users can take a photo, see a preview, optionally crop, and receive results without a separate Submit tap
- Pinyin results visually match the line structure of the source book
- App initiates backend warm-up on load, reducing first-request cold-start impact
- All existing tests pass after schema change
