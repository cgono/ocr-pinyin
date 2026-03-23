# Story 1.3: Validate Uploaded Images and Return Actionable Errors

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As Clint,
I want image quality and file constraints validated before OCR,
so that bad inputs are rejected early with clear retry guidance.

## Acceptance Criteria

1. Given an uploaded image that fails format/size/readability checks, when `/v1/process` receives it, then the API returns a structured validation failure and the UI shows actionable guidance to retake/reupload.
2. Given a valid image, when validation succeeds, then processing continues to OCR and status messaging indicates progress.

## Tasks / Subtasks

- [x] Implement backend image-validation pipeline for `/v1/process` (AC: 1, 2)
  - [x] Add validation service module for MIME/type, file size, and decode/readability checks.
  - [x] Enforce request-safe limits before full file parsing (size, file count, multipart boundaries).
  - [x] Return typed `status="error"` envelope for invalid uploads with machine-readable category/code.
  - [x] Keep valid uploads on success path and preserve current contract (`status|request_id|data|warnings|error`).
- [x] Add actionable error taxonomy and response mapping (AC: 1)
  - [x] Define validation error codes (e.g., `invalid_mime_type`, `file_too_large`, `image_decode_failed`, `image_too_large_pixels`).
  - [x] Ensure `error.message` is user-actionable and safe for frontend display.
  - [x] Keep developer/debug details internal (logs/diagnostics), not in user-facing error text.
- [x] Update frontend process flow messaging for validation outcomes (AC: 1, 2)
  - [x] Map validation error codes to clear retry guidance in upload UI.
  - [x] Show processing state for valid uploads while backend continues toward OCR stage.
  - [x] Preserve camera-first retry flow (`Take Photo` primary, reupload secondary).
- [x] Extend tests for validation and envelope behavior (AC: 1, 2)
  - [x] Add backend unit tests for validation service edge cases.
  - [x] Add integration tests for `/v1/process` invalid/valid upload scenarios.
  - [x] Add/extend contract tests to assert validation failures keep envelope invariants.
  - [x] Add frontend tests for actionable error copy and progress-state rendering.

## Dev Notes

### Story Foundation

- Epic: `Epic 1 - Foundation & Capture-to-Result Vertical Slice`.
- Story 1.3 is the intake-quality gate before OCR and pinyin features expand in Stories 1.4 and 1.5.
- Scope is validation and guidance; do not implement OCR extraction logic in this story.

### Technical Requirements

- Keep endpoint contract under `POST /v1/process` with stable top-level response envelope.
- Validation checks must cover at least:
  - MIME/content-type allowlist for image uploads.
  - File size upper bound.
  - Decode/readability check to ensure uploaded bytes are actually parseable as an image.
  - Pixel/complexity guardrail to prevent oversized/decompression-bomb style inputs.
- Invalid upload response must use structured error envelope:
  - `status: "error"`
  - `request_id: <string>`
  - `error: { code, category, message, ... }` (category from shared taxonomy)
- Valid uploads should remain on success path and return progress-oriented message while OCR is still placeholder.

### Architecture Compliance

- Follow backend layering from architecture guidance:
  - Route in `backend/app/api/v1/process.py`
  - Validation logic in `backend/app/services/` (not inline in route handler)
  - Envelope/schema definitions in `backend/app/schemas/process.py`
- Preserve API versioning and `snake_case` payload conventions.
- Maintain request-id correlation behavior in responses.
- Avoid introducing persistence or auth concerns in this story.

### Library / Framework Requirements

Current project pins (from `backend/pyproject.toml` and `frontend/package.json`):

- Backend:
  - `fastapi==0.129.0`
  - `pydantic==2.11.9`
  - `python-multipart==0.0.20`
  - `uvicorn[standard]==0.37.0`
- Frontend:
  - `react==19.1.1`
  - `@tanstack/react-query==5.87.1`
  - `vite==7.1.4`
  - `vitest==2.1.1`

Latest-knowledge notes gathered during story creation (2026-03-01 UTC):

- FastAPI file uploads use `UploadFile` backed by a spooled temporary file (memory/disk optimized), which is suitable for large uploads and validation workflows.
- Starlette multipart parsing supports `max_files`, `max_fields`, and `max_part_size` controls via `Request.form(...)`; use these limits to reduce parser abuse risk.
- Pillow supports `Image.verify()` for integrity checking and provides `MAX_IMAGE_PIXELS` plus decompression-bomb warnings/errors for oversized image safety.
- Python removed `imghdr` in 3.13, so do not use `imghdr`-based type checks for new validation logic.

### File Structure Requirements

Expected files to add/modify:

- `backend/app/api/v1/process.py`
- `backend/app/schemas/process.py`
- `backend/app/services/image_validation.py` (new)
- `backend/tests/unit/services/test_image_validation.py` (new)
- `backend/tests/integration/api_v1/test_process_route.py`
- `backend/tests/contract/response_envelopes/test_process_envelopes.py`
- `frontend/src/features/process/components/UploadForm.jsx`
- `frontend/src/__tests__/features/process/UploadForm.test.jsx` (new/extend)

### Testing Requirements

Backend:

- Unit tests for validation service:
  - rejects unsupported MIME/type
  - rejects oversize file bytes
  - rejects unreadable/corrupt image bytes
  - rejects excessive pixel dimensions/count
  - accepts valid image samples
- Integration tests for `/v1/process`:
  - invalid file returns `status="error"` with validation category/code
  - valid image keeps non-error path and includes `request_id`
- Contract tests:
  - ensure validation error responses preserve envelope shape
  - ensure no accidental key drift (`request_id`, not `requestId`; no `payload`)

Frontend:

- Component tests validating:
  - actionable guidance appears for validation failures
  - progress message appears while valid image is submitted
  - retry path remains obvious (`Take Photo`, reupload option)

### Previous Story Intelligence

From Story 1.2 and repository state:

- Contract envelope enforcement is already strict in `ProcessResponse`; keep new validation responses compliant with status-specific constraints.
- Existing tests already assert top-level contract and snake_case invariants; extend them rather than introducing parallel assertion styles.
- CI jobs already separate backend/frontend/contract checks; place new tests into existing suites so branch protections continue to work.
- Current `/v1/process` uses `_build_process_response` seam for contract patching tests; preserve this seam or replace with an equally testable abstraction.

### Git Intelligence Summary

Recent commit pattern (`f90ec93`, `343e546`, `9438b05`, `0fa58aa`, `826f334`) shows:

- incremental, story-scoped changes are preferred,
- tooling and dependency management has active churn,
- quality gates and contract stability are already a team priority.

Actionable guidance for this story:

- keep validation changes narrowly scoped to intake and messaging,
- avoid broad refactors in route/schema files,
- avoid introducing new top-level API fields that would force contract churn.

### Latest Tech Information

- Use FastAPI `UploadFile` for file intake and validation path compatibility (official docs).
- Apply Starlette multipart limits (`max_files`, `max_fields`, `max_part_size`) as guardrails for upload attack surface.
- Use Pillow integrity and decompression safeguards (`verify`, `MAX_IMAGE_PIXELS`) when decoding uploaded images.
- Avoid `imghdr` (removed in Python 3.13); use maintained libraries and MIME/type validation patterns instead.

### Project Structure Notes

- Current project structure aligns with architecture guidance (`backend/app/api/v1`, `backend/app/services`, `frontend/src/features/process`, `frontend/src/lib`).
- No `project-context.md` file was discovered; rely on planning artifacts as source of truth.
- This story should keep MVP no-auth/no-db posture unchanged.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.3-Validate-Uploaded-Images-and-Return-Actionable-Errors]
- [Source: _bmad-output/planning-artifacts/prd.md#Image-Intake--Validation]
- [Source: _bmad-output/planning-artifacts/architecture.md#API--Communication-Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation-Patterns--Consistency-Rules]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Flow-Optimization-Principles]
- [Source: _bmad-output/implementation-artifacts/1-2-establish-baseline-ci-quality-gates-backend-frontend-contract.md]
- [Source: https://fastapi.tiangolo.com/tutorial/request-files/]
- [Source: https://www.starlette.io/requests/]
- [Source: https://pillow.readthedocs.io/en/stable/reference/Image.html]
- [Source: https://docs.python.org/3/library/imghdr.html]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Workflow: `_bmad/bmm/workflows/4-implementation/create-story`
- Core executor: `_bmad/core/tasks/workflow.xml`
- Story source context: `_bmad-output/planning-artifacts/epics.md`
- Architecture source context: `_bmad-output/planning-artifacts/architecture.md`
- UX source context: `_bmad-output/planning-artifacts/ux-design-specification.md`
- Prior implementation context: `_bmad-output/implementation-artifacts/1-2-establish-baseline-ci-quality-gates-backend-frontend-contract.md`
- Backend tests: `cd backend && pytest -q`
- Frontend tests: `cd frontend && npm test`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story prepared for `dev-story` implementation workflow.
- Includes validation guardrails, file-level change map, and test expectations.
- Includes latest technical specifics for FastAPI/Starlette/Pillow/Python validation concerns.
- Implemented `image_validation` service with MIME allowlist, file-size guard, decode/readability checks, and pixel-limit guardrail.
- Updated `/v1/process` flow to return typed validation errors (`category`, `code`, `message`) while preserving response envelope contract.
- Added frontend validation guidance mapping and pending-state messaging for valid uploads.
- Added backend unit/integration/contract coverage and expanded frontend behavior tests; all backend and frontend test suites pass.

### Senior Developer Review (AI)

**Reviewer:** Clint | **Date:** 2026-03-01 | **Outcome:** ✅ Approved (after fixes)

| # | Severity | Issue | Fix Applied |
|---|----------|-------|-------------|
| H1 | HIGH | "Request-safe limits before full parsing" task not done — entire body loaded before size check; Starlette limits never applied | Added `Content-Length` pre-check in `process_image`; exported `MAX_FILE_SIZE_BYTES` |
| H2 | HIGH | Pillow not used; no decompression-bomb protection; hand-rolled parsers used instead | Replaced with Pillow `Image.open` + `img.load()`; added `pillow==11.2.1` to `pyproject.toml` |
| H3 | HIGH | JPEG decoder silently broken for progressive/RST-marker images | Fixed by H2 (Pillow handles all JPEG variants) |
| M1 | MEDIUM | `sprint-status.yaml` modified but not in File List | Added to File List |
| M2 | MEDIUM | Frontend showed "Valid image accepted" before server validation complete | Changed to neutral "Uploading image..." during pending; OCR confirmation shown on success |
| M3 | MEDIUM | No integration test for empty-body / missing-file path | Added `test_process_route_missing_file_returns_validation_error` |
| M4 | MEDIUM | `ImageValidationError` as frozen dataclass never called `Exception.__init__` — empty `exc.args` broke log middleware | Converted to regular `Exception` subclass with `super().__init__(message)` |
| M5 | MEDIUM | `validationGuidanceByCode[code] \|\| error.message` fallback branch had no test | Added fallback-message test in `upload-form.test.jsx` |

Low issues (L1–L3) noted; no code changes required.

### Change Log

- 2026-03-01: Implemented Story 1.3 upload validation pipeline, validation error taxonomy, frontend retry/progress messaging, and related test coverage.
- 2026-03-01: Senior Developer Review (AI) — adversarial review found 3 HIGH, 5 MEDIUM, 3 LOW issues; all HIGH and MEDIUM issues fixed automatically.

### File List

- _bmad-output/implementation-artifacts/1-3-validate-uploaded-images-and-return-actionable-errors.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/api/v1/process.py
- backend/app/schemas/process.py
- backend/app/services/image_validation.py
- backend/tests/unit/services/test_image_validation.py
- backend/tests/integration/api_v1/test_process_route.py
- backend/tests/contract/response_envelopes/test_process_envelopes.py
- frontend/src/features/process/components/UploadForm.jsx
- frontend/src/__tests__/features/process/upload-form.test.jsx
- frontend/src/lib/api-client.js
- frontend/src/test/setup.js
- frontend/tests/smoke/upload-form-smoke.test.mjs
