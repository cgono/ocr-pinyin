# Story 1.1: Set Up Initial Project from Starter Template

Status: done

## Story

As Clint,
I want the project initialized from the selected FastAPI + Vite starter template with a /v1/process entrypoint and phone upload screen,
so that I can submit an image through a stable MVP path.

## Acceptance Criteria

1. Given a fresh repo and environment, when the app stack is started locally, then frontend and backend run with documented startup commands and /v1 routing is active with unauthenticated MVP access.
2. Given iPhone Safari opens the app, when I land on the initial screen, then I can access a clear Take Photo/upload action and submission posts to POST /v1/process.

## Tasks / Subtasks

- [x] Initialize monorepo structure and starter stacks (AC: 1)
  - [x] Create `backend/` FastAPI app scaffold with `app/main.py`, `app/api/v1/router.py`, and `app/api/v1/process.py`.
  - [x] Create `frontend/` Vite React scaffold with `src/features/process/components/UploadForm` equivalent baseline.
  - [x] Add root-level `README.md` startup instructions and per-app setup notes.
- [x] Establish backend v1 API baseline (AC: 1, 2)
  - [x] Implement `POST /v1/process` route stub with unauthenticated access.
  - [x] Return structured envelope with required baseline fields (`status`, `request_id`, and payload area).
  - [x] Wire API router mount so `/v1/*` is active.
- [x] Establish frontend upload screen baseline (AC: 2)
  - [x] Implement mobile-first initial screen with primary `Take Photo` and secondary file upload behavior.
  - [x] Wire submit action to `POST /v1/process` via a shared API client module.
  - [x] Show minimal processing/result placeholders confirming end-to-end request path.
- [x] Add local dev orchestration and parity setup (AC: 1)
  - [x] Add `docker-compose.yml` for backend + frontend startup parity.
  - [x] Add `.env.example` files for root/backend/frontend.
- [x] Add baseline checks to prevent drift in first story (AC: 1)
  - [x] Add backend smoke test for `/v1/process` route availability.
  - [x] Add frontend smoke test for initial upload action presence.

## Dev Notes

### Story Foundation

- Epic: `Epic 1 - Foundation & Capture-to-Result Vertical Slice`.
- This story is the foundation for all downstream epics; implementation must prioritize stable boundaries over feature depth.
- Keep MVP unauthenticated and /v1-versioned from day one.

### Technical Requirements

- Backend stack: FastAPI with Python service structure under `backend/`.
- Frontend stack: Vite + React under `frontend/`.
- API contract baseline must be versioned under `/v1` and use `snake_case` payload fields.
- Response envelope must support `success|partial|error` shape evolution; do not return raw unstructured strings.
- Request correlation (`request_id`) must be present in the baseline response path.

### Architecture Compliance

- Preserve feature/layer split in backend (`api`, `schemas`, `services`, `adapters`, `core`, `middleware`).
- Keep frontend API calls behind shared client abstraction (`frontend/src/lib/api-client.*` pattern), not scattered fetch calls.
- Keep MVP no-auth; if guard is needed later, use optional middleware seam without changing current behavior.
- Implement only sync `POST /v1/process` baseline now; leave async-ready field seam (`job_id`) optional.

### Library / Framework Requirements

- Use FastAPI current stable line and lock dependency versions in project manifests.
- Use React + ReactDOM matching major versions.
- Use Vite current stable major for scaffold/build.
- Use `@tanstack/react-query` (not legacy `react-query`) for frontend request lifecycle patterns.

Latest-version references used for this story context (captured 2026-03-01 UTC; verify at implementation time before pinning):
- FastAPI: `0.129.0` (PyPI listing).
- React: `19.1.1` and ReactDOM `19.1.1` (npm package pages).
- Vite: observed latest line `7.1.4` on npm package listing.
- `@tanstack/react-query`: `5.87.1` on npm package listing; docs confirm React 18+ compatibility.
- Ruff: PyPI docs indicate current install guidance and standalone installer support.

### File Structure Requirements

Create and/or align to these paths first:

- `backend/app/main.py`
- `backend/app/api/v1/router.py`
- `backend/app/api/v1/process.py`
- `backend/tests/integration/api_v1/test_process_route.py` (or equivalent)
- `frontend/src/main.jsx`
- `frontend/src/App.jsx`
- `frontend/src/features/process/components/UploadForm.jsx` (or equivalent)
- `frontend/src/lib/api-client.js`
- `frontend/src/__tests__/features/process/upload-form.test.*`
- `docker-compose.yml`
- `README.md`

### Testing Requirements

- Backend: route-availability test for `POST /v1/process` and envelope shape sanity.
- Frontend: render test for initial upload action and submit path invocation.
- Keep test scope to story ACs; avoid OCR/pinyin behavior in this story.

### Previous Story Intelligence

- Not applicable. This is Story `1.1` (no prior story in epic).

### Git Intelligence Summary

Recent commits are planning-focused (`feat: architecture`, `feat: revise epics`, readiness/course-correction updates). No implementation code conventions are established yet. Treat architecture doc conventions as source of truth for initial code layout.

### Latest Tech Information

- Prefer generating scaffold with current toolchain versions and then pinning tested versions in lockfiles.
- Avoid deprecated `react-query` package; use `@tanstack/react-query` from start.
- Validate Node/Python minimum versions against selected FastAPI and Vite/React versions before finalizing CI matrix.

### Project Structure Notes

- No structural conflicts detected between PRD, architecture, and UX for this story.
- UX direction requires mobile-first upload affordance and clear primary action hierarchy (`Take Photo` first).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.1-Set-Up-Initial-Project-from-Starter-Template]
- [Source: _bmad-output/planning-artifacts/architecture.md#Starter-Template-Evaluation]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project-Structure--Boundaries]
- [Source: _bmad-output/planning-artifacts/prd.md#API-Backend-Specific-Requirements]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#User-Journey-Flows]
- [Source: https://pypi.org/project/fastapi/]
- [Source: https://www.npmjs.com/react]
- [Source: https://www.npmjs.com/package/react-dom]
- [Source: https://www.npmjs.com/package/vite/v/7.1.4]
- [Source: https://www.npmjs.com/package/%40tanstack/react-query]
- [Source: https://tanstack.com/query/latest/docs/react/installation]
- [Source: https://pypi.org/pypi/ruff]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Workflow: `_bmad/bmm/workflows/4-implementation/create-story`
- Core executor: `_bmad/core/tasks/workflow.xml`
- Dev workflow: `_bmad/bmm/workflows/4-implementation/dev-story`
- Validation run: `python3 -m unittest discover -s backend/tests -p 'test_*.py'`
- Validation run: `node --test frontend/tests/smoke/upload-form-smoke.test.mjs`
- Validation run: `python3 -m compileall backend/app`
- Validation run: `node --check frontend/src/lib/api-client.js`
- Note: `pip install -r backend/requirements.txt` and `npm install` were attempted but blocked by network/DNS restrictions in this environment.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story prepared for `dev-story` execution.
- Implemented backend FastAPI scaffold with versioned `/v1` router and `POST /v1/process` baseline response envelope using `status`, `request_id`, and `payload`.
- Implemented frontend Vite + React baseline with mobile-first upload form, explicit `Take Photo` primary action, file upload input, and shared API client posting to `/v1/process`.
- Added local startup and parity artifacts: root README guidance, Docker Compose services, and root/backend/frontend `.env.example` files.
- Added story smoke tests in required locations and executable offline smoke tests for this restricted environment.
- [Code Review Fixes 2026-03-01] Added CORSMiddleware to backend/app/main.py (allow_origins=["*"]).
- [Code Review Fixes 2026-03-01] Typed ProcessResponse.status as Literal["success","partial","error"] in schemas/process.py.
- [Code Review Fixes 2026-03-01] Fixed docker-compose.yml: replaced env_file referencing .env.example with inline environment blocks; set VITE_API_BASE_URL=http://backend:8000 for inter-container routing.
- [Code Review Fixes 2026-03-01] Split backend/requirements.txt (prod only) and created backend/requirements-dev.txt (pytest, httpx).
- [Code Review Fixes 2026-03-01] Replaced manual useState mutation in UploadForm.jsx with useMutation from @tanstack/react-query; wired Take Photo button to hidden camera capture input.
- [Code Review Fixes 2026-03-01] Updated upload-form.test.jsx to wrap component with QueryClientProvider and use findByText for async assertion.

### File List

- _bmad-output/implementation-artifacts/1-1-set-up-initial-project-from-starter-template.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- .env.example
- README.md
- docker-compose.yml
- backend/.env.example
- backend/app/__init__.py
- backend/app/adapters/__init__.py
- backend/app/api/__init__.py
- backend/app/api/v1/__init__.py
- backend/app/api/v1/process.py
- backend/app/api/v1/router.py
- backend/app/core/__init__.py
- backend/app/main.py
- backend/app/middleware/__init__.py
- backend/app/schemas/__init__.py
- backend/app/schemas/process.py
- backend/app/services/__init__.py
- backend/pyproject.toml
- backend/requirements-dev.txt
- backend/requirements.txt
- backend/tests/integration/api_v1/test_process_route.py
- backend/tests/test_story1_smoke.py
- frontend/.env.example
- frontend/index.html
- frontend/package.json
- frontend/src/App.jsx
- frontend/src/__tests__/features/process/upload-form.test.jsx
- frontend/src/features/process/components/UploadForm.jsx
- frontend/src/lib/api-client.js
- frontend/src/main.jsx
- frontend/src/test/setup.js
- frontend/tests/smoke/upload-form-smoke.test.mjs
- frontend/vite.config.js

## Change Log

- 2026-03-01: Implemented Story 1.1 backend/frontend scaffold, `/v1/process` baseline path, mobile-first upload screen, local orchestration files, and smoke validations.
- 2026-03-01: Code review fixes applied — CORS middleware, Literal status type, docker-compose inter-container routing, requirements split, useMutation migration, Take Photo camera wiring, test QueryClient wrapper.
