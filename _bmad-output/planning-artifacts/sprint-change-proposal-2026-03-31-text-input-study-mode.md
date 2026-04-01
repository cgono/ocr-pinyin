# Sprint Change Proposal — Direct Pasted-Text Study Mode

**Date:** 2026-03-31
**Scope:** Moderate — new input mode with cross-artifact updates
**Status:** Approved

---

## Section 1: Issue Summary

**Trigger:** User-requested product priority change on 2026-03-31.

The current app is strong for camera-based reading help, and Epic 6 already added translation, pronunciation, and assistive reading improvements. But the product still assumes image input as the start of the workflow. That creates unnecessary friction for a second high-value use case the current product does not serve well:

1. studying Chinese song lyrics copied from the web
2. studying Chinese stories or passages found online
3. practicing aloud from text that already exists digitally

Right now, copied Chinese text has to be moved through another app or converted into an image before this app becomes useful. That is the wrong tradeoff for study workflows where OCR adds no value.

Problem statement:

> The product currently optimizes for photo capture only. For copied Chinese text, that forces avoidable OCR friction and blocks a valuable study flow. The app needs a direct pasted-text mode that generates pinyin and English translation inside the existing reading surface.

Evidence from current artifacts and codebase:

- The PRD and UX both emphasize low-friction reading continuity, but the current frontend entry point is still the single [`UploadForm.jsx`](/Users/clint/Documents/GitHub/ocr-pinyin/frontend/src/features/process/components/UploadForm.jsx) camera/upload flow.
- The current API is image-first: [`process.py`](/Users/clint/Documents/GitHub/ocr-pinyin/backend/app/api/v1/process.py) accepts binary image input only.
- Translation already exists and is valuable, but it currently depends on the OCR-oriented process route rather than a direct text-study path.
- Epic 5 History remains backlog and lower value for immediate day-to-day use than text study.

---

## Section 2: Impact Analysis

**Epic Impact:**

- Epic 6 is the correct home for this change, because it already owns translation, pronunciation, and reading-assistance output.
- Epic 6 should be reopened with a new story:
  - `6-6-add-direct-pasted-text-study-mode`
- Epic 5 History remains backlog and should stay behind Epic 6 at the user's direction.
- No existing epic becomes obsolete.

**Story Impact:**

- No completed story requires rollback.
- Stories 6.1 through 6.5 remain valid and become reusable foundations for the new flow.
- New work is additive and should reuse the existing result renderer as much as possible.

**Artifact Conflicts / Updates Needed:**

- `prd.md`: broaden product scope and journeys to include direct pasted-text study; add FR44.
- `epics.md`: expand Epic 6 scope and add Story 6.6; align missing Story 6.5 entry while touching the section.
- `architecture.md`: document a separate text-processing endpoint and service boundary.
- `ux-design-specification.md`: update the entry flow to support both camera and pasted-text modes.
- `sprint-status.yaml`: reopen Epic 6 and add Story 6.6 as backlog.

**Technical Impact:**

- Frontend:
  - add a clear `Paste Text` mode alongside `Take Photo` / `Upload Existing`
  - reuse the current pinyin/translation reading surface
  - suppress image-specific preview/diagnostics when the request started from text input
- Backend:
  - add a dedicated text-processing route instead of overloading the binary upload route
  - validate pasted Chinese text separately from image validation
  - reuse pinyin, translation, and derived reading services where possible
- API:
  - add `POST /v1/process-text` with JSON input such as `{ "source_text": "..." }`
  - keep the existing `ProcessResponse` envelope so the UI can share the renderer

**Secondary Artifact Impact:**

- OpenAPI docs need a second process endpoint
- frontend and backend tests need new coverage for text validation and shared result rendering
- cost accounting remains relevant, but OCR-specific metrics should not be required for text-only flows

---

## Section 3: Recommended Approach

**Selected approach:** Direct adjustment.

Add a dedicated pasted-text processing path inside the existing app instead of pushing this work into History or forcing a larger MVP reset.

**Why this is the right path:**

1. It delivers direct user value quickly.
2. It reuses existing translation and reading work rather than discarding it.
3. It keeps the product concept coherent: one app for Chinese reading help, regardless of whether the source starts as a photo or text.
4. It avoids a risky contract rewrite by using a new endpoint rather than overloading `POST /v1/process`.

**Option review:**

- Option 1, Direct adjustment: Viable. Medium effort, low-to-medium risk.
- Option 2, Potential rollback: Not viable. No existing feature needs removal to support this.
- Option 3, PRD MVP review: Not needed. MVP is still valid; this is a priority shift inside the current direction, not a reduction.

**Effort:** Medium

**Risk:** Medium

**Timeline impact:** Low to Medium. One focused story should cover it if the endpoint and rendering reuse stay disciplined.

---

## Section 4: Detailed Change Proposals

### PRD changes

**OLD direction:**

```md
- Web UI accessible from phone for image upload.
- Image parsing/OCR to extract Chinese characters.
- Pinyin generation from extracted characters.
```

**NEW direction:**

```md
- Web UI accessible from phone for image upload.
- Image parsing/OCR to extract Chinese characters.
- Pinyin generation from extracted characters.
- English translation for extracted Chinese text.
```

Additional PRD edits:

- expand the differentiator from photo-only to photo-or-pasted-text
- add a new user journey for pasted-text study flow
- add `FR44: User can paste Chinese text directly into the app and generate pinyin plus English translation without running OCR.`

### Epic change

**OLD Epic 6 title:**

```md
### Epic 6: Translation & Pronunciation Output
```

**NEW Epic 6 title:**

```md
### Epic 6: Translation, Pronunciation & Direct Text Study
```

**New Story 6.6:**

```md
### Story 6.6: Add Direct Pasted-Text Study Mode

As Clint,
I want to paste Chinese text directly into the app and generate pinyin plus English translation,
So that I can study song lyrics, online stories, and other copied passages without taking a photo first.
```

**Acceptance direction:**

1. Add a pasted-text mode in the app that skips OCR.
2. Add a text-processing API endpoint that returns the same response envelope as image processing.
3. Reuse the current reading result renderer for pinyin, translation, and derived reading groups.
4. Add clear validation for empty, oversized, or non-Chinese input.
5. Preserve current image-upload behavior with no regression.

### Architecture change

**OLD direction:**

```md
- Clean API boundary for `/v1/process`, `/v1/health`, `/v1/metrics`, history endpoints.
```

**NEW direction:**

```md
- Clean API boundary for `/v1/process`, `/v1/process-text`, `/v1/health`, `/v1/metrics`, history endpoints.
```

The architecture should explicitly separate:

- image processing orchestration
- pasted-text validation/processing orchestration
- shared pinyin, translation, and reading-projection services

### UX change

**OLD entry model:**

```md
Title, short hint text, `Take Photo` primary CTA, `Upload Existing` secondary action.
```

**NEW entry model:**

```md
Title, short hint text, `Take Photo` primary CTA, `Upload Existing` secondary action, `Paste Text` tertiary mode switch.
```

The same quiet reading surface remains primary after submission; only the intake method changes.

---

## Section 5: Implementation Handoff

**Scope classification:** Moderate

**Route to:** Scrum Master / planning owner now, then Dev agent for implementation

**Planning artifacts updated in this proposal:**

1. `prd.md`
2. `epics.md`
3. `architecture.md`
4. `ux-design-specification.md`
5. `sprint-status.yaml`

**Execution handoff for development:**

1. Create the Story 6.6 implementation artifact.
2. Add `POST /v1/process-text`.
3. Extend the frontend intake UI with `Paste Text`.
4. Reuse the current result renderer and reading services.
5. Add backend/frontend regression coverage.

**Success criteria:**

- Pasted Chinese text can be processed without OCR.
- The result includes pinyin and English translation in the same study surface.
- The app supports both live photo reading and copied-text study without splitting into separate products.
- Epic 5 History remains backlog until this higher-value study flow is complete.

**Approval status:** Approved by user request on 2026-03-31
