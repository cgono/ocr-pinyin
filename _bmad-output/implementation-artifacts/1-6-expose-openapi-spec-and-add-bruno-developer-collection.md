# Story 1.6: Expose OpenAPI Spec and Add Bruno Developer Collection

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As Clint,
I want the backend API spec automatically available at /openapi.json and a Bruno collection pre-configured in the repo,
so that I can test endpoints interactively and have the API contract update automatically as new endpoints are added.

## Acceptance Criteria

1. Given the backend is running, when I request GET /openapi.json, then a valid OpenAPI 3.x schema is returned listing all /v1 endpoints and the schema includes the binary request body content-types for POST /v1/process.
2. Given the backend is running, when I navigate to GET /docs, then Swagger UI is accessible and POST /v1/process shows the expected image/jpeg, image/png, and image/webp binary body options.
3. Given the Bruno collection exists in docs/bruno/, when opened in Bruno, then it imports cleanly, references http://localhost:8000/openapi.json as its base, and a pre-configured Process Image request is available for immediate use.
4. Given the CORS configuration is updated, when GET /openapi.json is requested cross-origin from localhost dev ports, then the response is not blocked by CORS and all existing backend tests continue to pass.

## Tasks / Subtasks

- [x] Add GET to CORS allowed methods in main.py (AC: 4)
  - [x] In `backend/app/main.py`, change `allow_methods=["POST", "OPTIONS"]` to `allow_methods=["GET", "POST", "OPTIONS"]` so that `/openapi.json` and `/docs` are reachable cross-origin from the Vite dev server (port 5173).
  - [x] Do NOT widen `allow_origins` — the existing localhost-focused allowlist is correct.
- [x] Document binary request body content-types in OpenAPI spec (AC: 1, 2)
  - [x] In `backend/app/api/v1/process.py`, add an `openapi_extra` parameter to the `@router.post('/process', ...)` decorator to declare the `requestBody` with `image/jpeg`, `image/png`, and `image/webp` binary schema entries. This does not change the runtime behavior — the route still reads raw bytes from `Request`.
  - [x] Confirm GET /docs Swagger UI correctly renders the three binary content-type options for POST /v1/process.
- [x] Create Bruno developer collection in docs/bruno/ (AC: 3)
  - [x] Create `docs/bruno/bruno.json` — collection manifest (name: OCR Pinyin API, version: 1, type: collection).
  - [x] Create `docs/bruno/environments/local.bru` — environment file setting `baseUrl: http://localhost:8000`.
  - [x] Create `docs/bruno/Process Image.bru` — pre-configured POST /v1/process request using binary body, Content-Type: image/jpeg, and pointing to `{{baseUrl}}/v1/process`.
  - [x] Verify the collection directory can be opened in Bruno without import errors.
- [x] Add backend tests for OpenAPI endpoint and CORS (AC: 1, 4)
  - [x] Create `backend/tests/integration/api_meta/test_openapi_route.py` with tests for: GET /openapi.json returns 200; schema is valid JSON with openapi field; `/v1/process` POST route is present in the paths; binary content-types (image/jpeg, image/png, image/webp) appear in the process route requestBody; CORS response header `access-control-allow-origin` is present for a GET request from localhost:5173.
  - [x] Run the full test suite to confirm all existing tests still pass.

## Dev Notes

### Story Foundation

- Source story: Epic 1, Story 1.6 in `_bmad-output/planning-artifacts/epics.md`.
- This is the final story in Epic 1 (Foundation & Capture-to-Result Vertical Slice). It adds developer tooling and spec exposure on top of the completed processing pipeline from Stories 1.1–1.5.
- Scope boundary: OpenAPI spec exposure, Swagger UI correctness, CORS update for GET, Bruno collection creation, and supporting tests. **Do NOT** touch OCR/pinyin logic, schemas, or response envelopes.

### Previous Story / Revert Intelligence

- **IMPORTANT**: A previous attempt at "story 1-6" (commit `0b720ee`) was **reverted** (commit `61280c4`, message: "Revert 'feat: story 1-6' — Don't use LangChain anymore"). That reverted commit was in the wrong scope entirely (it modified `textract_ocr_provider.py` and attempted a LangChain Graph orchestrated flow migration). It had nothing to do with OpenAPI/Bruno.
- The correct scope for story 1-6 is exactly what the epics file specifies: OpenAPI spec endpoint + Bruno collection. Do not deviate.
- The revert also removed a `sprint-change-proposal-2026-03-02.md` and two story files. None of those are relevant to this story.

### Developer Context Section

- FastAPI **already serves /openapi.json and /docs by default** via `FastAPI(title="OCR Pinyin API", version="0.1.0")` in `backend/app/main.py`. No new route registration is needed.
- The sole backend code change needed for OpenAPI correctness is adding `openapi_extra` to the existing `@router.post('/process', ...)` decorator, because the endpoint currently accepts a raw `Request` object (not a typed `UploadFile` body). FastAPI cannot auto-infer binary body types from a raw `Request` parameter — the `openapi_extra` injection is the correct pattern for this.
- The CORS middleware currently only lists `"POST"` and `"OPTIONS"` in `allow_methods`. GET must be added for `/openapi.json` to be reachable cross-origin from the Vite dev server.
- The `docs/` directory at the project root currently **exists but is empty** — confirmed by filesystem inspection. Create `docs/bruno/` inside it.

### Technical Requirements

- OpenAPI spec requirements:
  - GET /openapi.json must return a valid OpenAPI 3.x JSON document.
  - The `paths` section must include `/v1/process` POST operation.
  - The `/v1/process` POST operation must include a `requestBody` with explicit content entries for `image/jpeg`, `image/png`, and `image/webp`, each with schema `{"type": "string", "format": "binary"}`.
- CORS requirements:
  - Add `"GET"` to the `allow_methods` list in `backend/app/main.py`.
  - The existing localhost-focused `allow_origins` (`localhost:5173`, `127.0.0.1:5173`) is appropriate — do not expand to `"*"`.
  - Do NOT change `allow_headers` — it is already `["*"]` which is fine for developer tooling.
- No new runtime dependencies required. No changes to `pyproject.toml` or `uv.lock`.
- No schema/envelope changes. All existing `ProcessResponse`, `OcrData`, `PinyinData` etc. remain unchanged.

### Architecture Compliance

- Architecture document `_bmad-output/planning-artifacts/architecture.md` explicitly states: _"API docs: FastAPI OpenAPI + Swagger UI/ReDoc defaults"_ — this story delivers that.
- Architecture CORS policy: _"localhost-focused CORS allowlist"_ — add GET but keep origins unchanged.
- Architecture API naming: keep `/v1` prefix, `snake_case` fields, REST conventions — no changes needed here.
- Architecture security: _"request-size limits, MIME/type validation"_ — adding GET to CORS does not relax any of those; the `/openapi.json` endpoint is static and read-only.
- Architecture file structure: `docs/` is the designated docs directory. Bruno collection goes in `docs/bruno/`.

### Library / Framework Requirements

Current pinned versions in repo (from `backend/pyproject.toml`):

- `fastapi==0.129.0` — `openapi_extra` is supported in this version.
- `pydantic==2.11.9`
- `uvicorn[standard]==0.37.0`

**No new backend dependencies needed** for this story.

**Bruno** is a desktop API client (https://www.usebruno.com). It is NOT a backend dependency — the Bruno collection is plain text files on disk (`.bru` format). No npm/pip install required.

Bruno collection file format (v1, current stable):
- `bruno.json` — collection manifest
- `*.bru` — request files (custom text DSL)
- `environments/*.bru` — environment variable files

### File Structure Requirements

Files to create:
- `docs/bruno/bruno.json`
- `docs/bruno/environments/local.bru`
- `docs/bruno/Process Image.bru`
- `backend/tests/integration/api_meta/__init__.py` (new package init — required for pytest discovery)
- `backend/tests/integration/api_meta/test_openapi_route.py`

Files to modify:
- `backend/app/main.py` — add `"GET"` to `allow_methods`
- `backend/app/api/v1/process.py` — add `openapi_extra` to `@router.post`

Files NOT to touch:
- `backend/app/schemas/process.py` — no schema changes needed
- `backend/app/services/` — no service changes needed
- `backend/app/adapters/` — no adapter changes needed
- `frontend/` — no frontend changes in scope for this story
- All existing test files — must remain green; do not modify them

### Implementation Reference: openapi_extra for Binary Body

The `@router.post` decorator currently looks like:

```python
@router.post('/process', response_model=ProcessResponse, response_model_exclude_none=True)
async def process_image(request: Request) -> ProcessResponse:
```

Add `openapi_extra` to annotate the binary request body (runtime behavior unchanged):

```python
@router.post(
    '/process',
    response_model=ProcessResponse,
    response_model_exclude_none=True,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
                "image/png": {"schema": {"type": "string", "format": "binary"}},
                "image/webp": {"schema": {"type": "string", "format": "binary"}},
            },
        }
    },
)
async def process_image(request: Request) -> ProcessResponse:
```

### Implementation Reference: CORS Change

In `backend/app/main.py`, change:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)
```

To:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
```

### Implementation Reference: Bruno Collection Files

**`docs/bruno/bruno.json`:**
```json
{
  "version": "1",
  "name": "OCR Pinyin API",
  "type": "collection",
  "ignore": []
}
```

**`docs/bruno/environments/local.bru`:**
```
vars {
  baseUrl: http://localhost:8000
}
```

**`docs/bruno/Process Image.bru`:**
```
meta {
  name: Process Image
  type: http
  seq: 1
}

post {
  url: {{baseUrl}}/v1/process
  body: binary
  auth: none
}

headers {
  Content-Type: image/jpeg
}

body:binary {
}

docs {
  Upload a Chinese language image to extract text and generate Hanyu Pinyin.

  Steps:
  1. Select this request in Bruno
  2. Set the active environment to "local" (ensure backend is running at localhost:8000)
  3. In the Body tab, click "Select File" and choose a JPEG/PNG/WebP image
  4. Update Content-Type header to match your file: image/jpeg, image/png, or image/webp
  5. Click Send

  The response follows the standard envelope:
  - status: "success" | "partial" | "error"
  - request_id: UUID string
  - data.ocr.segments[]: extracted text segments with language and confidence
  - data.pinyin.segments[]: hanzi/pinyin pairs

  OpenAPI spec: http://localhost:8000/openapi.json
  Swagger UI:   http://localhost:8000/docs
}
```

### Testing Requirements

New test file: `backend/tests/integration/api_meta/test_openapi_route.py`

Required test cases:
1. `test_openapi_json_returns_200` — GET /openapi.json → HTTP 200.
2. `test_openapi_json_is_valid_schema` — response body is valid JSON with at least `openapi`, `info`, and `paths` keys.
3. `test_openapi_includes_process_route` — `paths` contains `/v1/process` with a `post` operation.
4. `test_openapi_process_route_has_binary_content_types` — the `post.requestBody.content` for `/v1/process` includes keys `image/jpeg`, `image/png`, and `image/webp`.
5. `test_openapi_cors_get_allowed` — GET /openapi.json with `Origin: http://localhost:5173` request header returns an `access-control-allow-origin` response header.

Use the same `TestClient` pattern already in use across `backend/tests/integration/api_v1/test_process_route.py`. Import `app` from `app.main`.

Do NOT add CORS preflight (OPTIONS) tests — those are covered implicitly by existing test patterns and add complexity without value here.

### Previous Story Intelligence

From Story 1.5 and pattern analysis:
- Keep thin route handlers; this story's changes follow that — `openapi_extra` is pure metadata, not logic.
- Maintain strict contract discipline: `ProcessResponse` model must not change.
- The `TestClient` from `starlette.testclient` (already in use via httpx dependency) is the right tool for integration tests. Import `TestClient` and `app` from `app.main`.
- Test fixtures follow the pattern in `backend/tests/helpers.py` — check if any helpers are reusable.
- Quality gates must pass: Ruff lint + full test suite.

### Git Intelligence Summary

Recent commit history:
- `e0f32f8` — feat: fix Textract credentials issue (modified main.py +6, minor env updates)
- `61280c4` — Revert "feat: story 1-6" (reverted a LangChain migration — unrelated to this story)
- `63682ea` — feat: linting
- `8e64eff` — feat: story 1-5 (pending code review)

The main.py in `e0f32f8` added something — the current main.py already has a `_get_cors_origins()` function sourced from `CORS_ALLOW_ORIGINS` env var. The CORS update in this story (adding GET method) is a 1-line change and surgical. No other changes in main.py needed.

Pattern to follow: story-scoped incremental delivery with passing CI gates.

### Project Context Reference

No `project-context.md` detected in repository. Primary context sources:
- `_bmad-output/planning-artifacts/epics.md` — Story 1.6 definition
- `_bmad-output/planning-artifacts/architecture.md` — CORS policy, OpenAPI expectation, file structure
- `_bmad-output/implementation-artifacts/1-5-generate-pinyin-and-return-unified-result-view.md` — previous story patterns
- `backend/app/main.py` — current CORS configuration
- `backend/app/api/v1/process.py` — current process route definition

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.6-Expose-OpenAPI-Spec-and-Add-Bruno-Developer-Collection]
- [Source: _bmad-output/planning-artifacts/architecture.md#API--Communication-Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Authentication--Security]
- [Source: _bmad-output/planning-artifacts/architecture.md#File-Structure-Patterns]
- [Source: _bmad-output/implementation-artifacts/1-5-generate-pinyin-and-return-unified-result-view.md]
- [Source: backend/app/main.py — current CORS configuration]
- [Source: backend/app/api/v1/process.py — current route definition]
- [Source: https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/#openapi-extra]
- [Source: https://www.usebruno.com — Bruno collection format reference]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

_No debug issues encountered._

### Completion Notes List

- Added `"GET"` to `allow_methods` in CORS middleware (`backend/app/main.py`) — enables `/openapi.json` and `/docs` to be fetched cross-origin from Vite dev server.
- Added `openapi_extra` to `@router.post('/process', ...)` in `backend/app/api/v1/process.py` to expose `image/jpeg`, `image/png`, and `image/webp` binary content-type entries in the OpenAPI spec. Runtime behaviour unchanged.
- Created Bruno developer collection under `docs/bruno/`: `bruno.json` manifest, `environments/local.bru` (baseUrl=localhost:8000), and `Process Image.bru` pre-configured POST request.
- Created `backend/tests/integration/api_meta/test_openapi_route.py` with 5 tests covering: /openapi.json 200 response, valid schema structure, /v1/process route presence, binary content-types in requestBody, and CORS header on GET /openapi.json from localhost:5173.
- All 59 tests pass; Ruff lint passes with zero issues.
- No new runtime dependencies added; no schema/envelope changes.

### File List

**Modified:**
- `backend/app/main.py`
- `backend/app/api/v1/process.py`

**Created:**
- `docs/bruno/bruno.json`
- `docs/bruno/environments/local.bru`
- `docs/bruno/Process Image.bru`
- `backend/tests/integration/api_meta/__init__.py`
- `backend/tests/integration/api_meta/test_openapi_route.py`

## Change Log

- 2026-03-21: Implemented story 1.6 — CORS GET method added, `openapi_extra` binary content-types declared, Bruno collection created in `docs/bruno/`, integration tests added for OpenAPI endpoint and CORS. All 59 tests pass.
