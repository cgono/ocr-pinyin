# Story 1.5: Generate Pinyin and Return Unified Result View

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As Clint,
I want pinyin generated from extracted Chinese text and shown with the uploaded image,
so that I can continue reading immediately.

## Acceptance Criteria

1. Given OCR extracted Chinese text, when pinyin generation runs, then the API returns pinyin in a structured JSON response and HTML output presents image plus pinyin in one view.
2. Given processing completes successfully, when I view the result, then completion state is clearly indicated and response shape remains versioned under `/v1` with no auth required for MVP.

## Tasks / Subtasks

- [x] Implement pinyin generation service with provider seam (AC: 1)
  - [x] Create `backend/app/services/pinyin_service.py` to transform OCR segments into pinyin output using a dedicated service boundary.
  - [x] Add adapter contract and default implementation in `backend/app/adapters/pinyin_provider.py` (and provider-specific module if needed) so engine/vendor can change without route rewrites.
  - [x] Ensure pinyin output is deterministic and stable enough for bedtime reading use; return typed pinyin execution errors when generation fails.
- [x] Extend `/v1/process` response schema for structured pinyin payload (AC: 1, 2)
  - [x] Update `backend/app/schemas/process.py` to include pinyin data in `ProcessData` without breaking existing envelope invariants.
  - [x] Keep top-level response shape unchanged: `status`, `request_id`, and `data|warnings|error` according to status semantics.
  - [x] Keep all API fields `snake_case` and route versioning under `/v1`.
- [x] Integrate pinyin stage into process orchestration (AC: 1, 2)
  - [x] In `backend/app/api/v1/process.py`, run pinyin generation only after OCR yields usable segments.
  - [x] Map failures to typed categories/codes (`pinyin` category) and preserve request correlation id.
  - [x] Keep partial-ready schema compatibility for future Epic 2 behavior.
- [x] Deliver unified result view in frontend (AC: 1, 2)
  - [x] Update `frontend/src/features/process/components/UploadForm.jsx` (or extracted result component) to render uploaded image and pinyin result together in one result section.
  - [x] Preserve existing processing status visibility and ensure successful completion state remains explicit.
  - [x] Keep UX progressive disclosure direction: reading output primary, technical details secondary.
- [x] Expand automated tests and contracts (AC: 1, 2)
  - [x] Add backend unit tests for pinyin service normalization/error mapping.
  - [x] Extend backend integration tests for `/v1/process` success path with pinyin payload and pinyin failure path with typed `pinyin` error.
  - [x] Extend contract tests to guard envelope stability after pinyin payload addition.
  - [x] Add frontend tests verifying unified image+pinyin rendering and clear success state behavior.

## Dev Notes

### Story Foundation

- Source story: Epic 1, Story 1.5 in `_bmad-output/planning-artifacts/epics.md`.
- This story closes the Epic 1 vertical slice by adding pinyin conversion on top of Story 1.4 OCR output.
- Scope boundary: produce structured pinyin output and unified result rendering; do not implement mixed-language filtering/alignment uncertainty logic from Epic 2.

### Developer Context Section

- Current backend pipeline already performs image validation and OCR extraction in `/v1/process`.
- Story 1.5 should layer pinyin generation directly after OCR success, not as a separate endpoint.
- Existing OCR payload (`data.ocr.segments[]`) must remain available for downstream features and diagnostics.
- Keep implementation composable for Story 2.1 and Story 2.2 (filtering and alignment enhancements).

### Technical Requirements

- API contract requirements:
  - `/v1/process` remains the single processing endpoint.
  - Response envelope invariants remain strict (`success` requires `data`; `error` requires `error`; no mixed envelope fields).
  - Add structured pinyin payload under `data` (for example `data.pinyin` with segment/line entries) and avoid breaking existing OCR fields.
- Error handling requirements:
  - Pinyin failures must return typed errors with `category="pinyin"` and stable error codes.
  - Do not leak provider/internal exception strings to clients.
- MVP access model requirements:
  - Keep unauthenticated MVP behavior unchanged.
  - Keep route versioning and naming conventions unchanged (`/v1`, `snake_case`).

### Architecture Compliance

- Maintain architecture layering and boundaries:
  - Route/orchestration: `backend/app/api/v1/process.py`
  - Pinyin service logic: `backend/app/services/pinyin_service.py`
  - Provider integration: `backend/app/adapters/pinyin_provider.py`
  - Contracts: `backend/app/schemas/process.py`
- Follow existing architecture patterns:
  - Standardized response envelope and typed error taxonomy.
  - Thin route orchestration; heavy logic in service/adapters.
  - Preserve future async-ready fields (`job_id`) and evolution seams.
- Do not add DB/auth/history scope in this story.

### Library / Framework Requirements

Current pinned versions in repo:

- Backend: `fastapi==0.129.0`, `pydantic==2.11.9`, `pillow==11.2.1`, `python-multipart==0.0.20`, `uvicorn==0.37.0`, `langchain-core==0.3.61`, `boto3==1.37.26`.
- Frontend: `react==19.1.1`, `@tanstack/react-query==5.87.1`, `vite==7.1.4`.

Latest stable checks during story generation (2026-03-02):

- FastAPI `0.135.1` (released 2026-03-01).
- Pydantic `2.12.5` (released 2025-11-26).
- Pillow `12.1.1` (released 2026-02-11).
- Uvicorn `0.41.0` (released 2026-02-16).
- python-multipart `0.0.22` (released 2026-01-25).
- React docs indicate latest major `19.2`.
- `@tanstack/react-query` npm package shows `5.87.1`.
- `vite` npm package shows `7.1.4`.

Implementation guidance:

- Do not combine dependency upgrades with Story 1.5 unless a blocking bug/security issue is hit.
- If pinyin generation introduces a new library/provider, pin exact versions and add provider-level tests.

### File Structure Requirements

Expected files to add/modify:

- `backend/app/api/v1/process.py`
- `backend/app/schemas/process.py`
- `backend/app/services/pinyin_service.py` (new)
- `backend/app/adapters/pinyin_provider.py` (new, plus provider-specific module if applicable)
- `backend/tests/unit/services/test_pinyin_service.py` (new)
- `backend/tests/integration/api_v1/test_process_route.py`
- `backend/tests/contract/response_envelopes/test_process_envelopes.py`
- `frontend/src/features/process/components/UploadForm.jsx` (or extracted result component)
- `frontend/src/__tests__/features/process/upload-form.test.jsx`

### Testing Requirements

Backend:

- Unit tests:
  - pinyin conversion from OCR segments into structured response fields.
  - pinyin error mapping from provider exceptions to typed API-facing errors.
- Integration tests (`/v1/process`):
  - valid image + OCR + pinyin success returns `status="success"` with both OCR and pinyin data.
  - pinyin provider failure returns structured `status="error"` with `error.category="pinyin"`.
  - existing validation and OCR failure behaviors remain unchanged.
- Contract tests:
  - enforce envelope invariants and required keys for success/error paths after pinyin payload addition.

Frontend:

- Component tests:
  - result view renders uploaded image and pinyin in one unified screen.
  - explicit completion state is visible on successful processing.
  - pinyin failure path shows actionable retry guidance.

### Previous Story Intelligence

From Story 1.4 implementation and follow-up fixes:

- Keep route orchestration thin and async-safe; service/adapters should own external provider work.
- Preserve strict contract discipline (`ProcessResponse` model validation prevents envelope drift).
- Reuse test helpers and avoid duplicating integration/contract fixture setup.
- Maintain structured error taxonomy with user-safe recovery messages.
- UI should stay low-noise and recovery-oriented; avoid technical-detail-first rendering.

### Git Intelligence Summary

Recent commit pattern (`feat: story 1-4`, then targeted fixes) indicates:

- Story-scoped incremental delivery is preferred.
- Quality gates and tests are expected to accompany feature work.
- Follow-up commits resolved async I/O and test duplication concerns, so Story 1.5 should continue the same discipline:
  - async-safe provider calls
  - shared test utilities
  - typed error contracts

### Latest Tech Information

- PyPI confirms newer versions than current backend pins for FastAPI, Pydantic, Pillow, Uvicorn, and python-multipart.
- Frontend pins are aligned with currently indexed npm versions for Vite and TanStack Query.
- React documentation currently tracks major `19.2`; repo pin remains `19.1.1` and is acceptable for this story unless an explicit upgrade need appears.
- For Story 1.5, prioritize implementation stability over ecosystem upgrades.

### Project Context Reference

- No `project-context.md` file detected in repository discovery.
- Primary context sources for this story are:
  - `_bmad-output/planning-artifacts/epics.md`
  - `_bmad-output/planning-artifacts/architecture.md`
  - `_bmad-output/planning-artifacts/prd.md`
  - `_bmad-output/planning-artifacts/ux-design-specification.md`
  - `_bmad-output/implementation-artifacts/1-4-extract-chinese-text-from-valid-images.md`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.5-Generate-Pinyin-and-Return-Unified-Result-View]
- [Source: _bmad-output/planning-artifacts/prd.md#Pinyin-Generation--Result-Presentation]
- [Source: _bmad-output/planning-artifacts/architecture.md#API--Communication-Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project-Structure--Boundaries]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Core-User-Experience]
- [Source: _bmad-output/implementation-artifacts/1-4-extract-chinese-text-from-valid-images.md]
- [Source: https://pypi.org/project/fastapi/]
- [Source: https://pypi.org/project/pydantic/]
- [Source: https://pypi.org/project/pillow/]
- [Source: https://pypi.org/project/uvicorn/]
- [Source: https://pypi.org/project/python-multipart/]
- [Source: https://react.dev/versions]
- [Source: https://www.npmjs.com/package/%40tanstack/react-query]
- [Source: https://www.npmjs.com/package/vite]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Implementation Plan

1. Created `pinyin_provider.py` with `PinyinProvider` Protocol, `NoOpPinyinProvider`, error classes, and `get_pinyin_provider()` factory (defaults to `pypinyin`).
2. Created `pypinyin_provider.py` implementing `PyPinyinProvider` using `pypinyin==0.55.0` with `Style.TONE` for Unicode tone-marked output.
3. Created `pinyin_service.py` with `generate_pinyin(segments)` async function wrapping provider with typed `PinyinServiceError` (category="pinyin").
4. Extended `schemas/process.py` with `PinyinSegment`, `PinyinData`; added `pinyin: PinyinData | None` to `ProcessData`.
5. Updated `api/v1/process.py` to run pinyin generation after OCR success, mapping failures to `category="pinyin"` error responses.
6. Updated `UploadForm.jsx` with `useEffect`-managed image preview URL, `<ruby>` pinyin rendering with tone marks, explicit success indicator (`aria-label="processing-complete"`), and secondary `<details>` OCR section.
7. Added `URL.createObjectURL`/`URL.revokeObjectURL` stubs in `src/test/setup.js` for jsdom compatibility.

### Completion Notes

- All 5 story tasks and 20 subtasks completed and verified.
- **Backend:** 50 tests pass (12 new: 5 pinyin service unit, 4 pypinyin adapter unit, 2 integration pinyin paths, 3 contract pinyin envelope tests).
- **Frontend:** 13 tests pass (5 new: pinyin reading render, completion state, unified view, OCR details secondary section, pinyin retry guidance).
- Acceptance Criteria satisfied:
  - AC1: `/v1/process` returns structured `data.pinyin` with per-character hanzi/pinyin pairs after successful OCR; frontend renders image + pinyin in one unified result view.
  - AC2: Completion state clearly indicated (`✓ Processing complete`); response shape remains versioned under `/v1` with no auth changes.
- Architecture compliance: thin route orchestration, service/adapter boundaries maintained, strict envelope invariants preserved (no mixed fields).
- `pypinyin==0.55.0` added to `pyproject.toml` dependencies.
- Code review fixes applied:
  - Enforced request body size limit during streaming reads in `/v1/process` (not only via `Content-Length`) to prevent oversized upload memory pressure.
  - Preserved backend structured error code/message for non-2xx frontend responses so UI recovery guidance remains accurate.
  - Added strict pinyin output length validation in adapter to prevent silent truncation on malformed provider output.
  - Hardened CORS defaults to localhost allowlist with env-configurable origins (`CORS_ALLOW_ORIGINS`).

### Senior Developer Review (AI)

- Review date: 2026-03-02
- Outcome: Changes Requested -> Fixed
- Findings addressed:
  - HIGH: Unbounded request-body read path in `backend/app/api/v1/process.py` for missing/malformed `Content-Length`.
  - MEDIUM: Frontend API client dropped backend structured error metadata on non-2xx responses.
  - MEDIUM: Pinyin adapter could silently truncate output on provider/input length mismatch.
  - MEDIUM: CORS policy used wildcard origin instead of localhost-focused allowlist.
- Verification after fixes:
  - Backend full suite: `51 passed`
  - Frontend full suite: `15 passed`

### Debug Log References

- Story file: `_bmad-output/implementation-artifacts/1-5-generate-pinyin-and-return-unified-result-view.md`
- Workflow: `_bmad/bmm/workflows/4-implementation/dev-story`

### File List

New files:
- `backend/app/adapters/pinyin_provider.py`
- `backend/app/adapters/pypinyin_provider.py`
- `backend/app/services/pinyin_service.py`
- `backend/tests/unit/adapters/test_pypinyin_provider.py`
- `backend/tests/unit/services/test_pinyin_service.py`

Modified files:
- `backend/app/schemas/process.py`
- `backend/app/api/v1/process.py`
- `backend/app/main.py`
- `backend/pyproject.toml`
- `backend/tests/integration/api_v1/test_process_route.py`
- `backend/tests/contract/response_envelopes/test_process_envelopes.py`
- `backend/tests/unit/adapters/test_pypinyin_provider.py`
- `backend/tests/unit/test_main.py`
- `frontend/src/features/process/components/UploadForm.jsx`
- `frontend/src/__tests__/features/process/upload-form.test.jsx`
- `frontend/src/lib/api-client.js`
- `frontend/tests/lib/api-client.test.js`
- `frontend/src/test/setup.js`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/1-5-generate-pinyin-and-return-unified-result-view.md`

### Change Log

- 2026-03-02: Implemented Story 1.5 — pinyin service + provider seam, schema extension, route integration, unified frontend result view with image preview and ruby pinyin rendering, full test coverage (unit/integration/contract/frontend).
- 2026-03-02: Code review remediation — fixed body size enforcement during stream read, non-2xx structured error propagation in frontend API client, pinyin adapter output-length validation, and CORS localhost allowlist defaults with new regression tests.
