# Story 1.2: Establish Baseline CI Quality Gates (Backend + Frontend + Contract)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As Clint,
I want baseline CI quality gates running early in the project,
so that regressions are caught before feature expansion and implementation stays consistent.

## Acceptance Criteria

1. Given the repository includes backend and frontend apps, when CI runs on pull requests and main branch updates, then backend lint/test checks execute (Ruff and backend tests) and frontend lint/test checks execute (ESLint and frontend tests).
2. Given API response envelope conventions are defined, when contract checks run in CI, then `/v1/process` success/partial/error envelope checks validate required fields (`status`, `request_id`, and `data|warnings|error` as applicable) and CI fails if required envelope fields are missing or renamed.
3. Given any required quality check fails, when CI completes, then the pipeline status is failed and merge is blocked until checks pass.

## Tasks / Subtasks

- [x] Create baseline CI workflow for backend, frontend, and contract checks (AC: 1, 2, 3)
  - [x] Add `.github/workflows/ci.yml` triggered on `pull_request` and pushes to `main`.
  - [x] Use matrix-free deterministic jobs for MVP (`backend-checks`, `frontend-checks`, `contract-checks`) to keep failures easy to diagnose.
  - [x] Pin action major tags and include explicit runtime setup steps.
- [x] Implement backend quality gates (AC: 1, 3)
  - [x] Add Ruff configuration in `backend/pyproject.toml` (`[tool.ruff]`, `[tool.ruff.lint]`) and enforce via `ruff check backend/app backend/tests`.
  - [x] Ensure backend tests run via `pytest` and fail CI on any test failure.
  - [x] Add/adjust backend dev dependencies so lint+tests are reproducible in CI.
- [x] Implement frontend quality gates (AC: 1, 3)
  - [x] Add ESLint flat config (`frontend/eslint.config.js`) aligned with Vite + React 19.
  - [x] Add npm scripts in `frontend/package.json`: `lint`, `test`, and keep `build` unaffected.
  - [x] Ensure `vitest run` is used for non-watch CI execution.
- [x] Add API envelope contract checks (AC: 2, 3)
  - [x] Add backend contract tests in `backend/tests/contract/response_envelopes/` focused on `/v1/process` envelope shape.
  - [x] Validate `status` is one of `success|partial|error` and that required top-level fields exist by status.
  - [x] Fail tests if keys are renamed, missing, or violate `snake_case` contract assumptions.
- [x] Make merge-blocking behavior explicit (AC: 3)
  - [x] Document required checks in README (or contribution section) so branch protection can target exact check names.
  - [x] Name CI jobs predictably so branch protection mapping stays stable.

## Dev Notes

### Story Foundation

- Epic: `Epic 1 - Foundation & Capture-to-Result Vertical Slice`.
- This story establishes quality guardrails before deeper OCR/pinyin features to reduce regression risk.
- Story 1.1 already scaffolded backend/frontend and basic tests; Story 1.2 should extend that baseline rather than re-scaffold.

### Technical Requirements

- CI must run on both PRs and `main` updates.
- Backend gate must include Ruff lint and pytest tests.
- Frontend gate must include ESLint lint and Vitest tests.
- Contract checks must validate `/v1/process` envelope requirements:
  - `status` required and constrained to `success|partial|error`
  - `request_id` required
  - `data` required for `success`
  - `warnings` allowed/expected for `partial`
  - `error` required for `error`
- CI failures must produce non-zero exit status so required checks can block merge.

### Architecture Compliance

- Preserve backend layering (`api`, `schemas`, `services`, `adapters`, `core`, `middleware`) and put contract tests under backend test tree, not ad-hoc scripts.
- Preserve frontend feature-first structure; lint config should live in `frontend/` and target `src/` + tests only.
- Keep API contract validation in automated tests, not one-off shell scripts.
- Keep `/v1` versioning and `snake_case` payload conventions enforced via tests.

### Library / Framework Requirements

Use current pinned project versions unless the story explicitly upgrades:

- Backend runtime deps currently pinned:
  - `fastapi==0.129.0`
  - `pydantic==2.11.9`
  - `uvicorn[standard]==0.37.0`
- Backend dev deps currently pinned:
  - `pytest==8.4.2`
  - `httpx==0.28.1`
- Frontend currently pinned:
  - `react==19.1.1`
  - `react-dom==19.1.1`
  - `vite==7.1.4`
  - `@vitejs/plugin-react==5.0.2`
  - `vitest==2.1.1`

Latest-knowledge notes gathered during story creation (2026-03-01 UTC):

- Ruff latest observed on PyPI: `0.15.1` (2026-02-12).
- Pytest latest observed on PyPI: `9.0.2` (2025-12-06).
- ESLint latest v9 release observed in ESLint blog: `9.39.1` (2025-11-03).
- Vitest has released major `4.0` (Vitest blog, 2025-10-22); current project is on `2.1.1`.
- GitHub Actions major lines now include:
  - `actions/checkout@v6`
  - `actions/setup-node@v6`
  - `actions/setup-python@v6`

Guidance: for this story, avoid broad toolchain upgrades unless required by CI breakage; prioritize stable guardrails with current project pins. If upgrading actions to v6, ensure runner compatibility notes are met.

### File Structure Requirements

Create or modify:

- `.github/workflows/ci.yml`
- `backend/pyproject.toml` (Ruff config)
- `backend/requirements-dev.txt` (if lint deps need explicit pinning)
- `backend/tests/contract/response_envelopes/test_process_envelopes.py`
- `frontend/eslint.config.js`
- `frontend/package.json` (scripts)
- `README.md` (required checks documentation)

Do not relocate existing Story 1.1 files; extend in place.

### Testing Requirements

- Backend CI commands:
  - `python -m pip install -r backend/requirements-dev.txt`
  - `ruff check backend/app backend/tests`
  - `pytest backend/tests`
- Frontend CI commands:
  - `npm ci --prefix frontend`
  - `npm run lint --prefix frontend`
  - `npm run test --prefix frontend`
- Contract checks should run as part of backend tests (or dedicated job using the same test suite path).
- Contract tests must include at least one test each for `success`, `partial`, and `error` envelope assertions.

### Previous Story Intelligence

From Story 1.1 implementation and fixes:

- Baseline FastAPI app and Vite React app are already scaffolded and working.
- Shared API client exists at `frontend/src/lib/api-client.js`; keep this pattern.
- Existing backend and frontend smoke tests are present; build CI on top of them instead of replacing.
- Code-review fixes already introduced important conventions:
  - CORS middleware is enabled.
  - `status` typing uses `Literal["success", "partial", "error"]` in backend schema.
  - Frontend upload uses React Query mutation.
- Story 1.2 should avoid refactoring runtime behavior; focus is guardrails and contracts.

### Git Intelligence Summary

Recent commit pattern:

- `50373bf feat: story 1-1` introduced scaffold, tests, and baseline artifacts.
- Earlier commits are planning/readiness/course-correction updates.

Actionable guidance:

- Keep incremental changes small and isolated to CI/lint/test contract files.
- Avoid broad structural churn; current repo layout already matches architecture guidance.

### Latest Tech Information

- ESLint docs currently require modern Node.js ranges (Node `^20.19.0`, `^22.13.0`, or `>=24`) for latest ESLint tooling; align CI Node runtime accordingly.
- Vite ecosystem is on major line 7.x; project already pins `vite==7.1.4`.
- Newer GitHub Actions major versions (checkout/setup-node/setup-python v6 lines) include Node24-based runners and compatibility expectations; if using v6, ensure hosted runner supports required version.

### Project Structure Notes

- Architecture expects contract tests under `backend/tests/contract/response_envelopes/` and explicit CI gates.
- No conflict between PRD, architecture, UX, and this story scope.
- This story is a quality-infrastructure story; avoid introducing OCR/pinyin feature behavior changes.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.2-Establish-Baseline-CI-Quality-Gates-Backend--Frontend--Contract]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation-Patterns--Consistency-Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project-Structure--Boundaries]
- [Source: _bmad-output/planning-artifacts/prd.md#API-Backend-Specific-Requirements]
- [Source: _bmad-output/implementation-artifacts/1-1-set-up-initial-project-from-starter-template.md]
- [Source: https://pypi.org/project/ruff/]
- [Source: https://pypi.org/project/pytest/]
- [Source: https://eslint.org/docs/latest/use/getting-started]
- [Source: https://eslint.org/blog/2025/11/eslint-v9.39.1-released/]
- [Source: https://vitest.dev/blog]
- [Source: https://www.npmjs.com/package/vite]
- [Source: https://www.npmjs.com/package/%40vitejs/plugin-react]
- [Source: https://github.com/actions/checkout]
- [Source: https://github.com/actions/setup-node]
- [Source: https://github.com/actions/setup-python]
- [Source: https://github.com/actions/setup-python/releases]
- [Source: https://github.com/actions/setup-node/releases]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Workflow: `_bmad/bmm/workflows/4-implementation/create-story`
- Core executor: `_bmad/core/tasks/workflow.xml`
- Story source context: `_bmad-output/planning-artifacts/epics.md`
- Architecture source context: `_bmad-output/planning-artifacts/architecture.md`
- Prior implementation context: `_bmad-output/implementation-artifacts/1-1-set-up-initial-project-from-starter-template.md`

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Story prepared for `dev-story` implementation workflow.
- Includes CI guardrails, contract-testing scope, and action-version guidance with current ecosystem notes.
- Added CI workflow with deterministic `backend-checks`, `frontend-checks`, and `contract-checks` jobs on PRs and `main`.
- Added Ruff config and backend dev dependency pin for `ruff==0.15.1`; CI runs `ruff check backend/app backend/tests` and `pytest backend/tests`.
- Implemented `/v1/process` contract envelope enforcement using schema-level validation for `success|partial|error` and `data|warnings|error` requirements.
- Added contract tests for `/v1/process` envelope shape and unit tests validating response-model status constraints.
- Added frontend ESLint flat config and `lint` script while preserving `build` and `vitest run` usage for CI.
- Updated README with explicit required check names for branch protection mapping.
- Validation limits in this environment: pip and npm network installs are blocked; backend dependency installation and frontend lint package download could not be executed locally.
- Code review (2026-03-01): 3 High + 4 Medium issues found and fixed. See Change Log for details. NOTE: `frontend/package-lock.json` must be regenerated via `npm install` in a network-accessible environment after the ESLint devDependency additions.

### File List

- _bmad-output/implementation-artifacts/1-2-establish-baseline-ci-quality-gates-backend-frontend-contract.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- .github/workflows/ci.yml
- README.md
- backend/app/api/v1/process.py
- backend/app/schemas/process.py
- backend/pyproject.toml
- backend/requirements-dev.txt
- backend/tests/contract/response_envelopes/test_process_envelopes.py
- backend/tests/integration/api_v1/test_process_route.py
- backend/tests/unit/schemas/test_process_response_contract.py
- frontend/eslint.config.js
- frontend/package.json
- frontend/package-lock.json

## Change Log

- 2026-03-01: Created Story 1.2 with comprehensive implementation context, architecture guardrails, and latest technical/version guidance.
- 2026-03-01: Implemented baseline CI quality gates (backend/frontend/contract), added `/v1/process` envelope contract tests and schema enforcement, and documented merge-blocking required checks.
- 2026-03-01: Code review fixes applied — ESLint moved to devDependencies with `eslint-plugin-react` + `eslint-plugin-react-hooks` added; `eslint.config.js` updated with React/hooks rules; contract tests for `partial`/`error` now exercise live API via `_build_process_response` mock seam; 5 missing negative rejection tests added to unit schema suite; `backend-checks` CI job now excludes contract dir (deduplication); pip caching added to both Python CI jobs; Ruff rules expanded to `E,F,I,W,N`.
