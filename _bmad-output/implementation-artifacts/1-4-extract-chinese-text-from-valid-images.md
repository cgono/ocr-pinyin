# Story 1.4: Extract Chinese Text from Valid Images

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As Clint,
I want Chinese text extracted from a validated page image,
so that the system has source text for pinyin conversion.

## Acceptance Criteria

1. Given a valid uploaded image with Chinese text, when OCR runs, then extracted Chinese text is returned in `data.ocr.segments[]` with fields `text`, `language`, and `confidence`, and `status` is one of `success|partial|error` and is shown in both API response and UI state.
2. Given OCR cannot produce usable text, when extraction fails, then the response returns a structured failure category and the UI offers immediate retry guidance.

## Tasks / Subtasks

- [x] Implement OCR extraction service and response payload contract (AC: 1, 2)
  - [x] Add backend OCR models in `backend/app/schemas/process.py` so `ProcessData` can include `ocr.segments[]` with `text`, `language`, and `confidence` fields.
  - [x] Keep top-level envelope stable (`status`, `request_id`, `data|warnings|error`) and preserve snake_case naming.
  - [x] Add OCR-specific error taxonomy values under the existing shared pattern (for example `category="ocr"` with typed `code` values such as `ocr_no_text_detected`, `ocr_provider_unavailable`).
- [x] Add OCR service layer with clean adapter seam (AC: 1, 2)
  - [x] Create `backend/app/services/ocr_service.py` to own OCR execution and normalization into `segments[]`.
  - [x] Introduce adapter boundary (`backend/app/adapters/ocr_provider.py`) so engine/provider can be swapped without route-level rewrites.
  - [x] Normalize output to include only usable Chinese segments for this story; keep non-Chinese handling extensible for Story 2.1.
- [x] Integrate OCR stage into `/v1/process` flow after validation (AC: 1, 2)
  - [x] Run OCR only after `validate_image_upload` passes.
  - [x] Map OCR outcomes into envelope statuses:
  - [x] `success` when usable Chinese segments are produced.
  - [x] `error` when OCR fails to produce usable text.
  - [x] Keep `partial` path schema-safe for future stories even if not produced yet.
  - [x] Ensure failure responses remain structured and never leak raw provider exceptions.
- [x] Update frontend process screen for OCR result/error states (AC: 1, 2)
  - [x] Render current processing status from response (`success|partial|error`) and show extracted OCR segment preview when present.
  - [x] For OCR failure category, show immediate retry guidance with `Take Photo` as primary recovery action.
  - [x] Keep reading-flow ergonomics from UX spec: low-noise status area, no diagnostics-first UI.
- [x] Expand automated tests and contract coverage (AC: 1, 2)
  - [x] Backend unit tests for OCR normalization and error mapping.
  - [x] Backend integration tests for `/v1/process` success path (segments returned) and OCR failure path (typed `ocr` error).
  - [x] Contract tests asserting envelope invariants still hold across OCR success/error responses.
  - [x] Frontend tests for status display, segment rendering, and retry guidance messaging.

### Review Follow-ups (AI)

- [x] [AI-Review][MEDIUM] Extract shared `StubOcrProvider` and `_request_with_body()` helpers into a `conftest.py`; they are currently copy-pasted verbatim between `backend/tests/integration/api_v1/test_process_route.py` and `backend/tests/contract/response_envelopes/test_process_envelopes.py`. [test_process_route.py:20, test_process_envelopes.py:31]
- [x] [AI-Review][MEDIUM] `extract_chinese_segments()` performs blocking synchronous I/O (`file.file.seek(0)`, `file.file.read()`) inside the async FastAPI route handler. Once a real Textract call is live, this will also be blocking sync I/O on the event loop. Wrap the extraction call in `asyncio.get_event_loop().run_in_executor(None, ...)` or restructure as an async-safe operation before high-concurrency load. [ocr_service.py:26-29]

## Dev Notes

### Story Foundation

- Source story: Epic 1, Story 1.4 in `_bmad-output/planning-artifacts/epics.md`.
- This story is the first OCR extraction implementation and feeds Story 1.5 (pinyin generation).
- Scope boundary: implement extraction and structured OCR output only; do not implement Chinese/non-Chinese filtering policy beyond what is required for this story.

### Technical Requirements

- API contract requirements:
  - `POST /v1/process` remains the single processing entrypoint.
  - Response envelope must remain version-safe and consistent across statuses.
  - OCR payload must appear under `data.ocr.segments[]` with:
    - `text: str`
    - `language: str`
    - `confidence: float|int` (documented and normalized to one convention, preferably `0.0-1.0`).
- Error handling requirements:
  - OCR extraction failures return typed, structured errors.
  - Distinguish validation failures from OCR failures (`validation` vs `ocr` categories).
  - Preserve request correlation id in every response path.
- Performance and reliability:
  - Keep OCR stage implementation compatible with NFR target (<2s typical path) where feasible.
  - Prefer deterministic extraction path and explicit failure over ambiguous "success with empty text".

### Architecture Compliance

- Follow architecture layering:
  - Route/orchestration: `backend/app/api/v1/process.py`
  - OCR domain/service logic: `backend/app/services/ocr_service.py`
  - Provider integration details: `backend/app/adapters/ocr_provider.py`
  - Contracts/schemas: `backend/app/schemas/process.py`
- Preserve architecture conventions:
  - `/v1` route versioning
  - snake_case fields
  - standardized error envelope and category/code taxonomy
  - no auth/no DB changes in this story
- Keep MVP extensibility:
  - Use adapter interface so OCR backend can evolve without rewriting process route.
  - Keep response contract compatible with future diagnostics fields (Epic 3).

### Library / Framework Requirements

Current repo pins:

- Backend: `fastapi==0.129.0`, `pydantic==2.11.9`, `pillow==11.2.1`, `python-multipart==0.0.20`, `uvicorn==0.37.0`.
- Frontend: `react==19.1.1`, `@tanstack/react-query==5.87.1`, `vite==7.1.4`.

Latest stable references checked during story creation (2026-03-01):

- FastAPI `0.135.0` (released 2026-03-01).
- Pydantic `2.12.5` (released 2025-11-26).
- Pillow `12.1.1` (released 2026-02-11).
- python-multipart `0.0.22` (released 2026-01-25).
- Uvicorn `0.41.0` (released 2026-02-16).
- Starlette `0.52.1` (released 2026-01-18).
- LangChain `1.2.10` (released 2026-02-10).

Implementation guidance:

- Do not upgrade framework versions inside Story 1.4 unless required for OCR implementation correctness; prefer lockstep upgrade in a dedicated maintenance story.
- If introducing an OCR dependency/provider for this story, pin exact versions and add provider-specific adapter tests.

### File Structure Requirements

Expected files to add/modify:

- `backend/app/api/v1/process.py`
- `backend/app/schemas/process.py`
- `backend/app/services/ocr_service.py` (new)
- `backend/app/adapters/ocr_provider.py` (new)
- `backend/tests/unit/services/test_ocr_service.py` (new)
- `backend/tests/integration/api_v1/test_process_route.py`
- `backend/tests/contract/response_envelopes/test_process_envelopes.py`
- `frontend/src/features/process/components/UploadForm.jsx`
- `frontend/src/__tests__/features/process/upload-form.test.jsx`
- `frontend/src/lib/api-client.js` (only if response parsing needs extension)

### Testing Requirements

Backend:

- Unit tests:
  - OCR response normalization into `segments[]`.
  - Confidence normalization rules and language tag behavior.
  - OCR error mapping to typed category/code.
- Integration tests (`/v1/process`):
  - valid image + OCR success returns `status="success"` with `data.ocr.segments[]`.
  - valid image + OCR no usable text returns structured `status="error"` with `error.category="ocr"`.
  - validation failures from Story 1.3 remain unchanged.
- Contract tests:
  - ensure no top-level key drift and no status/envelope regression.

Frontend:

- Component tests:
  - success path displays processing completion + OCR segment preview.
  - OCR failure path shows retry-focused guidance.
  - status label reflects API status values.
- Keep existing tests for validation guidance intact.

### Previous Story Intelligence

From Story 1.3 implementation and review:

- Preserve intake-validation guardrails and do not bypass them when adding OCR stage.
- Keep typed error handling strict; avoid raw upstream/provider errors leaking to UI.
- Avoid route bloat: move OCR logic to service/adapters, keep route orchestration thin.
- Maintain contract-test seam discipline to reduce regression risk during response-shape changes.
- Keep UI copy neutral and actionable; avoid premature "success" messages until OCR step is complete.

### Git Intelligence Summary

Recent commits indicate story-scoped, incremental delivery (`feat: story 1-3`) and active contract/test rigor. For Story 1.4:

- Prefer narrowly scoped OCR changes with clear file boundaries.
- Extend existing test suites instead of introducing one-off test harnesses.
- Preserve established API envelope constraints and CI passability as first-class acceptance.

### Latest Tech Information

- FastAPI has newer releases than current pin (`0.135.0` latest vs `0.129.0` pinned); treat as deferred upgrade unless blocked.
- Pydantic and Pillow have newer stable lines; this matters if OCR schema/validation behavior depends on newer APIs.
- Python-multipart and Starlette have moved forward; keep parser/stream handling assumptions aligned with current pinned versions.
- LangChain has progressed to `1.2.10`; if OCR orchestration uses LangChain in this story, pin and encapsulate integration in adapters to avoid API churn across future stories.

### Project Structure Notes

- Current project structure generally follows architecture conventions.
- No `project-context.md` was found in repository discovery; planning artifacts remain the source of truth.
- This story should not introduce persistence, history storage, or auth changes.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.4-Extract-Chinese-Text-from-Valid-Images]
- [Source: _bmad-output/planning-artifacts/prd.md#Text-Extraction--Language-Handling]
- [Source: _bmad-output/planning-artifacts/architecture.md#API--Communication-Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation-Patterns--Consistency-Rules]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Core-User-Experience]
- [Source: _bmad-output/implementation-artifacts/1-3-validate-uploaded-images-and-return-actionable-errors.md]
- [Source: https://pypi.org/project/fastapi/]
- [Source: https://pypi.org/project/pydantic/]
- [Source: https://pypi.org/project/pillow/]
- [Source: https://pypi.org/project/python-multipart/]
- [Source: https://pypi.org/project/uvicorn/]
- [Source: https://pypi.org/project/starlette/]
- [Source: https://pypi.org/project/langchain/]
- [Source: https://www.npmjs.com/package/react]
- [Source: https://www.npmjs.com/package/vite]
- [Source: https://www.npmjs.com/package/%40tanstack/react-query]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Workflow: `_bmad/bmm/workflows/4-implementation/create-story`
- Core executor: `_bmad/core/tasks/workflow.xml`
- Story source context: `_bmad-output/planning-artifacts/epics.md`
- Architecture source context: `_bmad-output/planning-artifacts/architecture.md`
- UX source context: `_bmad-output/planning-artifacts/ux-design-specification.md`
- Prior implementation context: `_bmad-output/implementation-artifacts/1-3-validate-uploaded-images-and-return-actionable-errors.md`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story prepared for `dev-story` implementation workflow.
- Includes OCR extraction contract guardrails, file-level change map, and test expectations.
- Implemented OCR response contract (`data.ocr.segments[]`) and typed OCR failure taxonomy (`ocr_no_text_detected`, `ocr_provider_unavailable`) in backend route/schema/service layers.
- Added OCR adapter seam and normalization logic to keep route orchestration thin and provider details isolated.
- Updated frontend process UI to show API status, request id, OCR segment preview, and retry guidance for OCR failures.
- Validation status: backend tests passed (`27 passed`) and frontend tests passed (`9 passed`); lint checks pass.

### File List

- _bmad-output/implementation-artifacts/1-4-extract-chinese-text-from-valid-images.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- backend/app/adapters/ocr_provider.py
- backend/app/adapters/textract_ocr_provider.py
- backend/app/api/v1/process.py
- backend/app/schemas/process.py
- backend/app/services/ocr_service.py
- backend/pyproject.toml
- backend/tests/helpers.py
- backend/tests/contract/response_envelopes/test_process_envelopes.py
- backend/tests/integration/api_v1/test_process_route.py
- backend/tests/unit/adapters/test_textract_ocr_provider.py
- backend/tests/unit/schemas/test_process_response_contract.py
- backend/tests/unit/services/test_ocr_service.py
- frontend/src/__tests__/features/process/upload-form.test.jsx
- frontend/src/features/process/components/UploadForm.jsx

### Change Log

- 2026-03-01: Implemented Story 1.4 OCR extraction flow, response contract, typed OCR errors, frontend OCR status/preview UI, and expanded backend/frontend automated tests.
- 2026-03-01: Code review fixes — implemented AWS Textract provider with LangChain extraction chain (`textract_ocr_provider.py`); wired `get_ocr_provider()` via `OCR_PROVIDER` env var; fixed `OcrExecutionError` → `ocr_execution_failed` code mapping; added `boto3==1.37.26` and `langchain-core==0.3.61` to `pyproject.toml`; added Textract adapter unit tests and missing OCR service error-mapping tests; added `ocr_execution_failed` to frontend recovery guidance map. 2 medium follow-up items remain (test consolidation, blocking I/O).
- 2026-03-01: Resolved M3 and M4 — extracted shared `StubOcrProvider`, `_request_with_body`, and `PNG_1X1_BYTES` into `backend/tests/helpers.py` (added `tests` to `pythonpath`); deduped integration and contract test preambles; made `extract_chinese_segments` async with `(image_bytes, content_type)` signature; wraps blocking Textract call in `asyncio.get_running_loop().run_in_executor`; updated `process.py` and all service unit tests accordingly. All review action items resolved.
