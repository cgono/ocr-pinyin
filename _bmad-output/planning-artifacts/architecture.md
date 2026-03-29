---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - /workspaces/test-bmad/_bmad-output/planning-artifacts/prd.md
workflowType: 'architecture'
project_name: 'test-bmad'
user_name: 'Clint'
date: '2026-02-28T23:19:16Z'
lastStep: 8
status: 'complete'
completedAt: '2026-02-28T23:31:00Z'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
The product requires an end-to-end processing workflow that begins with phone-based image upload and performs quality validation, OCR extraction of Chinese text, language filtering, and Hanyu Pinyin generation. Results must be returned in both API-friendly JSON and phone-friendly HTML views, including original image context and aligned output where possible. The system must support explicit partial-result behavior and retry flows instead of binary success/fail responses.

Operationally, the requirements include service health/metrics endpoints, diagnostics visibility (raw OCR output, confidence indicators, timing, trace data), lightweight usage history retrieval, and a versioned `/v1` API contract. The MVP runs unauthenticated in a personal environment, but must preserve a migration path toward Apple ID authentication and broader content-management capabilities in future phases.

**Non-Functional Requirements:**
Architecture is strongly shaped by correctness-first output quality for reading/pronunciation use, with latency as a secondary but explicit constraint (target under 2 seconds for typical inputs). Reliability expectations require structured outcomes for every request and graceful degradation on uncertain OCR or provider/tool failures. Security and privacy expectations include TLS transport, private artifact handling, and externalized secret management.

Cost governance is an explicit non-functional driver: per-request cost estimation, daily aggregation, and budget threshold enforcement/warning around ~1 SGD/day. Observability is also foundational: telemetry emission and diagnostic detail should support rapid self-debug, Sentry-based error tracking, and lightweight metrics dashboarding.

**Scale & Complexity:**
The project is product-scope small but architecturally non-trivial due to orchestration and cross-cutting concerns. The backend must coordinate upload processing, OCR/pinyin transformation, diagnostics capture, history persistence, and cost/accounting logic while maintaining a simple user-facing flow.

- Primary domain: API backend with companion web interface
- Complexity level: medium
- Estimated architectural components: 8-10 core components (API gateway/routing, upload/validation, OCR adapter, pinyin service, orchestration layer, diagnostics/telemetry, cost guardrail, history store/service, rendering/response layer, ops endpoints)

### Technical Constraints & Dependencies

The architecture must support LangChain-based orchestration as a core implementation goal and learning objective. It should remain provider-adaptable for OCR and language processing while preserving deterministic response contracts for `/v1`. The system is intentionally constrained to MVP simplicity: one primary public processing endpoint, no SDK requirement, and no initial authentication.

Performance, correctness, and cost constraints must be enforceable with measurable signals. The implementation should expose health and metrics endpoints sufficient for direct use and future observability integration. Data handling design should preserve future features (audio, translation, book compilation) without forcing major contract redesign.

### Cross-Cutting Concerns Identified

Accuracy and confidence communication across the full pipeline; structured error taxonomy and recovery guidance; request-level tracing and timing visibility; budget governance and usage accounting; API versioning stability; privacy-aware artifact handling; extensibility for future multimodal and persistence-heavy features.

## Starter Template Evaluation

### Primary Technology Domain

Full-stack (API backend + lightweight web frontend) based on project requirements analysis.

### Starter Options Considered

1) FastAPI official full-stack template (`fastapi/full-stack-fastapi-template`)
- Pros: production-ready defaults, integrated React frontend, testing/deployment structure.
- Cons: includes PostgreSQL, auth, Docker, and broader infra that exceed MVP scope (no storage/auth for now).

2) Minimal dual-starter: FastAPI backend + Vite React frontend
- Pros: matches learning goals, keeps MVP small, aligns with workplace stack (FastAPI), and maps cleanly to Render hosting.
- Cons: requires us to define integration conventions ourselves (API client contracts, repo structure, dev scripts).

### Selected Starter: Minimal Dual-Starter (FastAPI + Vite React)

**Rationale for Selection:**
This option best matches MVP constraints: local laptop deployment, no persistence yet, React frontend learning, and FastAPI alignment with workplace practice. It minimizes accidental complexity while keeping architecture extensible for straightforward Render deployment and later cloud changes if the product outgrows the MVP platform.

**Initialization Command:**

```bash
# backend
python -m venv .venv
source .venv/bin/activate
pip install "fastapi[standard]"

# frontend
npm create vite@latest frontend -- --template react
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
- Backend: Python + FastAPI runtime conventions.
- Frontend: React on Node-based tooling (Vite).

**Styling Solution:**
- Minimal default CSS baseline from Vite React template (no forced UI framework).

**Build Tooling:**
- Frontend: Vite dev/build pipeline with HMR.
- Backend: FastAPI CLI/Uvicorn development flow.

**Testing Framework:**
- No heavy default test stack forced at scaffold stage (allows targeted tests for OCR/pinyin pipeline later).

**Code Organization:**
- Natural split architecture: `backend/` service and `frontend/` app.
- Clean API boundary for `/v1/process`, `/v1/health`, `/v1/metrics`, history endpoints.

**Development Experience:**
- Quick local iteration (`fastapi dev` + Vite dev server).
- Low setup friction for weekend MVP and rapid experimentation.

**Note:** Project initialization using this command should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Backend stack: Python + FastAPI.
- Frontend stack: React (Vite scaffold), static web UI style.
- MVP data persistence: no database.
- API style: REST `/v1` with OpenAPI documentation.
- Deployment baseline: local Docker Compose workflow for laptop use.

**Important Decisions (Shape Architecture):**
- Authentication: none for MVP, but include CORS allowlist and optional API-key feature flag path.
- Processing pattern: synchronous endpoint for MVP behavior, with async job model designed in contracts for later expansion.
- Frontend data layer: TanStack Query for request/cache lifecycle and learning value.
- Hosted deployment target: Render static site (frontend) + Render web service (backend).
- OCR Provider: Google Cloud Vision (`DOCUMENT_TEXT_DETECTION`) selected over AWS Textract. Textract does not support Chinese script. GCV plugs directly into the `OcrProvider` protocol adapter with no upstream code changes required.

**Deferred Decisions (Post-MVP):**
- Persistent history store (candidate: PostgreSQL + S3-compatible object artifacts).
- Full async queue execution (candidate: background worker plus managed queue if synchronous processing becomes limiting).
- Render deployment automation (`render.yaml`) and environment promotion workflow.
- Production auth (Apple ID or equivalent external identity flow).

### Data Architecture

- No DB in MVP.
- Use an internal repository interface from day 1 so persistence can be added without API contract rewrites.
- Store transient processing artifacts in-memory or temp filesystem only for current request lifecycle.
- Define future adapters:
  - `HistoryRepository` (PostgreSQL candidate)
  - `ArtifactStore` (S3-compatible object storage candidate)

### Authentication & Security

- No user authentication in MVP.
- Security baseline:
  - localhost-focused CORS allowlist
  - request-size limits
  - MIME/type validation for image uploads
  - secret/config via environment variables
  - TLS required when deployed beyond localhost
- Add optional API-key middleware toggle (disabled by default in MVP) to reduce migration effort later.

### API & Communication Patterns

- External API: REST under `/v1`.
- Primary MVP flow: synchronous `POST /v1/process` returning structured result.
- Async-ready design choice:
  - include response envelope fields compatible with future job processing (`status`, `request_id`, optional `job_id`)
  - keep domain service layer decoupled from transport so sync and async handlers can share logic later
- Error model: standardized machine-readable envelope with category/code/message/details.
- API docs: FastAPI OpenAPI + Swagger UI/ReDoc defaults.

### Frontend Architecture

- React + Vite scaffold.
- Use TanStack Query for API state (queries/mutations/retries/cache) to support learning and clean data-flow patterns.
- Keep routing minimal for MVP (upload/result/optional history view shell).
- Styling: lightweight baseline CSS initially; avoid heavy design system in MVP.
- Frontend calls backend `/v1` endpoints via typed API client module.

### Infrastructure & Deployment

- MVP runtime: Docker Compose profile for local laptop usage (`docker compose up`) to avoid manual multi-process startup.
- Compose spec (v2 CLI) with at least:
  - `backend` service (FastAPI)
  - `frontend` service (Vite dev or static build serve profile)
- Hosted target architecture:
  - Frontend: Render static site
  - Backend: Render web service
  - Error tracking: Sentry
  - Storage (later): managed Postgres and S3-compatible object storage if history/artifacts move beyond MVP
- Deployment configuration direction: Render Blueprint via `render.yaml` when hosted deployment work begins.

### Decision Impact Analysis

**Implementation Sequence:**
1. Scaffold backend/frontend projects.
2. Implement sync `/v1/process` vertical slice.
3. Add structured error envelope and diagnostics payload.
4. Add TanStack Query frontend flow for upload/process/result.
5. Add Docker Compose local orchestration.
6. Introduce async-ready response contract fields (without queue infra yet).
7. Add Sentry integration and Render deployment configuration in later iterations.
8. Add persistence and background-job infrastructure in later iterations if usage justifies it.

**Cross-Component Dependencies:**
- Async-ready API envelope affects backend handlers and frontend response handling.
- No-DB MVP simplifies backend now but requires repository abstraction to avoid future refactor churn.
- Dockerized local setup influences developer workflow and parity with future containerized build/deploy paths.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
12 areas where AI agents could make different choices and create integration conflicts.

### Naming Patterns

**Database Naming Conventions:**
- MVP has no DB. For future persistence, standardize on `snake_case` table/field names.
- Repository interfaces use domain terms: `HistoryRepository`, `ArtifactStore`.
- Future key naming uses `resource_id` pattern (example: `request_id`, `history_id`).

**API Naming Conventions:**
- REST endpoints use plural nouns where applicable (`/v1/history`), action endpoint remains `/v1/process`.
- Path parameters use `{id}` style in FastAPI route declarations.
- Query/path/header payload fields use `snake_case` in backend contracts.
- API version prefix is mandatory: `/v1/...`.

**Code Naming Conventions:**
- Python: modules/functions/variables `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- React: component files `PascalCase.jsx` (or `.tsx` if TS adopted later), hooks `useXxx`.
- Frontend shared API client methods mirror backend endpoint intent (`processImage`, `getHistory`).

### Structure Patterns

**Project Organization:**
- Monorepo-style split:
  - `backend/` FastAPI app
  - `frontend/` React app
- Backend organized by feature + layer:
  - `api/` (routers), `services/`, `schemas/`, `adapters/`, `core/`.
- Frontend organized by feature:
  - `features/process`, `features/history`, shared `components`, `lib/api`.

**File Structure Patterns:**
- Tests are separated by app:
  - `backend/tests/...`
  - `frontend/src/**/__tests__/...`
- Environment config:
  - `.env.example` committed
  - `.env.local` ignored
- Architecture and ADR docs remain under planning artifacts/docs.

### Format Patterns

**API Response Formats:**
- Success envelope:
  - `{ "status": "success", "request_id": "...", "data": {...}, "diagnostics": {...} }`
- Partial envelope:
  - `{ "status": "partial", "request_id": "...", "data": {...}, "warnings": [...], "diagnostics": {...} }`
- Error envelope:
  - `{ "status": "error", "request_id": "...", "error": { "code": "...", "category": "...", "message": "...", "details": {...} } }`
- Async-ready compatibility:
  - optional `job_id` field reserved for future queue execution.

**Data Exchange Formats:**
- JSON field naming is `snake_case` across backend API.
- Datetime values use ISO 8601 UTC strings (`YYYY-MM-DDTHH:MM:SSZ`).
- Booleans remain true JSON booleans (`true/false`), never `0/1`.
- Nulls are explicit `null`; avoid sentinel strings like `"N/A"`.

### Communication Patterns

**Event System Patterns:**
- MVP has no event bus. Internal async-ready domain events (if introduced) use `dot.case` names, e.g. `process.requested`.
- Event payloads include `request_id`, `event_version`, `occurred_at`.

**State Management Patterns:**
- Frontend server-state is handled via TanStack Query only.
- Local UI state stays in component/local hooks unless shared by 3 or more components.
- Query keys use array format with stable prefixes, e.g. `["process", requestId]`.

### Process Patterns

**Error Handling Patterns:**
- Backend never returns raw provider exceptions.
- Map all failures to typed categories (`validation`, `ocr`, `pinyin`, `system`, `budget`, `upstream`).
- Log full technical context server-side; return safe, actionable messages client-side.
- Frontend shows retry guidance for retriable categories.

**Loading State Patterns:**
- Use three visible states in UI: `idle`, `processing`, `completed/failed`.
- Disable duplicate submit while `processing`.
- Show request correlation (`request_id`) in diagnostics view for support/debug loops.

### Enforcement Guidelines

**All AI Agents MUST:**
- Preserve response envelope shapes and `snake_case` API fields.
- Keep FastAPI route prefixing under `/v1`.
- Use shared error category taxonomy and avoid ad-hoc codes.

**Pattern Enforcement:**
- PR checklist includes "API envelope unchanged" and "naming conventions followed".
- Contract tests validate response shape for success/partial/error paths.
- Lint/format gates: Ruff + Black (backend), ESLint + Prettier (frontend).

### Pattern Examples

**Good Examples:**
- `POST /v1/process` returns `status`, `request_id`, and `data`.
- `GET /v1/history/{id}` uses consistent envelope and error taxonomy.
- Frontend query key: `["history", id]`.

**Anti-Patterns:**
- Mixing `camelCase` and `snake_case` in API payloads.
- Returning plain strings for errors in one endpoint and objects in another.
- Bypassing shared API client and hardcoding endpoint URLs across components.

## Project Structure & Boundaries

### Complete Project Directory Structure

```text
test-bmad/
├── README.md
├── docker-compose.yml
├── .gitignore
├── .env.example
├── docs/
│   ├── architecture/
│   │   └── decisions.md
│   └── api/
│       └── contracts.md
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   └── errors.py
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       ├── process.py
│   │   │       ├── health.py
│   │   │       ├── metrics.py
│   │   │       └── history.py
│   │   ├── schemas/
│   │   │   ├── common.py
│   │   │   ├── process.py
│   │   │   ├── diagnostics.py
│   │   │   └── history.py
│   │   ├── services/
│   │   │   ├── process_service.py
│   │   │   ├── ocr_service.py
│   │   │   ├── pinyin_service.py
│   │   │   ├── diagnostics_service.py
│   │   │   ├── budget_service.py
│   │   │   └── history_service.py
│   │   ├── adapters/
│   │   │   ├── ocr_provider.py
│   │   │   ├── pinyin_provider.py
│   │   │   ├── telemetry_provider.py
│   │   │   └── storage/
│   │   │       ├── history_repository.py
│   │   │       └── artifact_store.py
│   │   ├── domain/
│   │   │   ├── models.py
│   │   │   └── events.py
│   │   └── middleware/
│   │       ├── request_id.py
│   │       ├── error_handler.py
│   │       └── api_key_optional.py
│   └── tests/
│       ├── unit/
│       │   ├── services/
│       │   └── schemas/
│       ├── integration/
│       │   └── api_v1/
│       └── contract/
│           └── response_envelopes/
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── .env.example
│   ├── Dockerfile
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── app/
│       │   ├── routes.jsx
│       │   └── query-client.js
│       ├── features/
│       │   ├── process/
│       │   │   ├── components/
│       │   │   │   ├── UploadForm.jsx
│       │   │   │   ├── ResultView.jsx
│       │   │   │   └── DiagnosticsPanel.jsx
│       │   │   ├── api.js
│       │   │   ├── hooks.js
│       │   │   └── types.js
│       │   └── history/
│       │       ├── components/
│       │       │   ├── HistoryList.jsx
│       │       │   └── HistoryDetail.jsx
│       │       ├── api.js
│       │       └── hooks.js
│       ├── components/
│       │   ├── layout/
│       │   └── common/
│       ├── lib/
│       │   ├── api-client.js
│       │   ├── errors.js
│       │   └── config.js
│       ├── styles/
│       │   └── index.css
│       └── __tests__/
│           ├── features/
│           └── lib/
└── infra/
    ├── docker/
    │   └── compose.override.example.yml
    └── terraform/
        ├── README.md
        ├── modules/
        │   ├── frontend_s3_cloudfront/
        │   ├── backend_lambda_apigw/
        │   └── shared_observability/
        └── envs/
            ├── dev/
            └── prod/
```

### Architectural Boundaries

**API Boundaries:**
- Public endpoints only under `/v1`.
- `process` is the primary MVP action endpoint.
- `health` and `metrics` are operational boundaries.
- `history` exists as contract surface; implementation can be memory-backed initially.

**Component Boundaries:**
- Frontend feature modules (`process`, `history`) do not call backend directly; all calls go through `lib/api-client.js`.
- Shared UI goes in `components/common`, feature-specific UI stays inside each feature folder.

**Service Boundaries:**
- `process_service` orchestrates OCR + pinyin + diagnostics.
- Provider-specific logic stays in `adapters/*_provider.py`.
- Budget, diagnostics, and history services remain independent cross-cutting units.

**Data Boundaries:**
- MVP uses ephemeral/in-memory storage adapters.
- Repository interfaces in `adapters/storage` define future persistence contract (PostgreSQL/S3-compatible object storage).
- No service directly depends on a concrete cloud SDK in MVP core flow.

### Requirements to Structure Mapping

**Feature Mapping:**
- Image upload + process flow -> `frontend/src/features/process/*`, `backend/app/api/v1/process.py`, `backend/app/services/process_service.py`.
- OCR + language filtering -> `backend/app/services/ocr_service.py`, `backend/app/adapters/ocr_provider.py`.
- Pinyin generation -> `backend/app/services/pinyin_service.py`, `backend/app/adapters/pinyin_provider.py`.
- Diagnostics + traces -> `backend/app/services/diagnostics_service.py`, `frontend/src/features/process/components/DiagnosticsPanel.jsx`.
- Budget guardrail -> `backend/app/services/budget_service.py`.
- Health/metrics -> `backend/app/api/v1/health.py`, `backend/app/api/v1/metrics.py`.
- History API surface -> `backend/app/api/v1/history.py`, `backend/app/services/history_service.py`, `frontend/src/features/history/*`.

**Cross-Cutting Concerns:**
- Request correlation and envelope consistency -> `backend/app/middleware/request_id.py`, `backend/app/core/errors.py`, contract tests.
- Optional API key guard -> `backend/app/middleware/api_key_optional.py`.
- Error taxonomy and client-safe messages -> `backend/app/core/errors.py` + frontend `lib/errors.js`.

### Integration Points

**Internal Communication:**
- Router -> service layer -> adapter interfaces.
- Frontend features -> TanStack Query hooks -> shared API client.

**External Integrations:**
- OCR provider via `ocr_provider.py` (Google Cloud Vision — `DOCUMENT_TEXT_DETECTION`; supports Simplified and Traditional Chinese). AWS Textract was evaluated but does not support Chinese script.
- Pinyin conversion provider via `pinyin_provider.py`.
- Optional telemetry sink via `telemetry_provider.py`.
- Error tracking via Sentry SDKs in backend and frontend.
- Future deployment configuration via `render.yaml` and service-level environment settings.

**Data Flow:**
- Upload from React -> `POST /v1/process` -> process orchestration -> envelope response -> React result + diagnostics.
- Future async compatibility preserved through `request_id` and optional `job_id` response fields.

### File Organization Patterns

**Configuration Files:**
- Root `.env.example` for shared docs.
- App-specific env samples in `backend/.env.example` and `frontend/.env.example`.

**Source Organization:**
- Backend: API, schemas, services, adapters, core, middleware separated.
- Frontend: feature-first modules plus shared libs/components.

**Test Organization:**
- Backend unit/integration/contract split in `backend/tests`.
- Frontend test folders under `src/__tests__`.

**Asset Organization:**
- Frontend static assets and styles under `frontend/src/styles` and standard Vite public paths.

### Development Workflow Integration

**Development Server Structure:**
- `docker compose up` starts frontend and backend for local laptop usage.
- Independent local run still supported for each app.

**Build Process Structure:**
- Frontend built with Vite.
- Backend packaged via Python project config (`pyproject.toml`).

**Deployment Structure:**
- Current local deployment via Docker Compose.
- Hosted deployment target is Render, with frontend and backend split into separate services and Blueprint-based config in `render.yaml`.

**Release Versioning:**
Package versioning is managed by release-please (`googleapis/release-please-action`), configured for a monorepo with two independent packages: `frontend` (node) and `backend` (python). `release-please-config.json` defines both packages. Conventional commits drive semantic version bumps. On merge to main, release-please creates a release PR updating `CHANGELOG.md`, `frontend/package.json`, and `backend/pyproject.toml`; merging the release PR creates a GitHub Release and tags the commit.

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All major choices are compatible: Python/FastAPI backend, React/Vite frontend, REST `/v1` API, Docker Compose local runtime, Render hosting target, and Sentry-based monitoring. Async-ready response contracts are compatible with current synchronous MVP execution.

**Pattern Consistency:**
Implementation patterns (naming, response envelopes, error taxonomy, query-key patterns, and layering boundaries) align with the selected technology stack and with the multi-agent consistency objective.

**Structure Alignment:**
The proposed project tree supports all architectural decisions. Service, adapter, API, schema, middleware, and frontend feature boundaries are explicit and enforce the chosen patterns.

### Requirements Coverage Validation ✅

**Epic/Feature Coverage:**
Feature areas in the PRD are mapped to concrete modules: processing, diagnostics, cost guardrail, health/metrics, and history contract surface.

**Functional Requirements Coverage:**
All FR categories have architectural support:
- image intake/validation
- OCR and language filtering
- pinyin generation and result rendering
- error handling and retry behavior
- diagnostics and observability
- budget/cost governance
- history endpoints and extensibility

**Non-Functional Requirements Coverage:**
NFRs are covered through architecture and constraints:
- correctness-first response design
- performance target support via lean MVP pipeline
- security baseline (CORS, size/type limits, env secrets, TLS when deployed)
- observability and diagnostic structure
- extensibility for Render deployment now and background-job evolution later

### Implementation Readiness Validation ✅

**Decision Completeness:**
Critical and important decisions are documented, including deferred items and rationale.

**Structure Completeness:**
Directory structure, boundaries, and integration points are concrete and implementation-ready.

**Pattern Completeness:**
Conflict-prone areas are addressed with consistent rules and examples suitable for AI-agent implementation handoff.

### Gap Analysis Results

**Critical Gaps:** None identified.

**Important Gaps:** None blocking MVP; deferred by design:
- concrete persistent store selection/implementation
- queue infrastructure activation for async execution
- production-grade auth path implementation

**Nice-to-Have Gaps:**
- explicit API contract test fixture catalog
- standardized observability dashboard template
- Render Blueprint/environment promotion workflow details

### Validation Issues Addressed

No blocking issues were found. Scope-risk concern around async processing was resolved by selecting an async-ready contract with deferred queue implementation.

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**✅ Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**✅ Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- clear MVP scope control with future-ready seams
- strong multi-agent consistency rules
- explicit backend/frontend boundaries and response contracts
- workplace-aligned technology and low-friction Render/Sentry operations path

**Areas for Future Enhancement:**
- activate async queue path
- add persistent history/artifact stores
- production auth and hardened deployment pipeline

### Implementation Handoff

**AI Agent Guidelines:**
- Follow architectural decisions exactly as documented.
- Preserve response envelope and naming conventions.
- Respect project boundaries and adapter interfaces.
- Use this document as the source of truth for architecture questions.

**First Implementation Priority:**
Initialize backend/frontend scaffolds, then implement the synchronous `/v1/process` vertical slice with standard response envelopes and diagnostics payload.
