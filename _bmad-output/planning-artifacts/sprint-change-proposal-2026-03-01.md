# Sprint Change Proposal

## 1. Issue Summary

### Trigger
During implementation (Story 1.1 project setup/bootstrap), a tooling gap was identified: backend dependency management currently uses `pip` with `requirements.txt`/`requirements-dev.txt`.

### Problem Statement
Current setup does not provide the preferred repo-local, lockfile-driven workflow for reproducible backend environments and does not optimize install/sync speed. The requested correction is to adopt the `uv` package manager for backend dependency management and runtime commands.

### Evidence
- Backend dependency files currently present:
  - `backend/requirements.txt`
  - `backend/requirements-dev.txt`
- Backend tooling file currently lacks dependency declarations:
  - `backend/pyproject.toml` (tooling-only currently)
- Startup docs currently use `pip`:
  - `README.md` backend instructions use `pip install -r requirements.txt`
- Container startup currently uses `pip`:
  - `docker-compose.yml` backend command runs `pip install -r requirements.txt`
- No `backend/uv.lock` currently exists.

## 2. Impact Analysis

### Epic Impact
- Affected epic: **Epic 1: Foundation & Capture-to-Result Vertical Slice**
- Impact type: refinement of setup/tooling implementation details.
- Outcome: Epic remains valid and in-sequence; no new epic needed.

### Story Impact
- Primary impacted story: **Story 1.1 Set Up Initial Project from Starter Template**
- Secondary impact: all backend implementation stories should use consistent `uv` commands for local dev/CI/docs.

### Artifact Conflicts
- PRD: no conflict (no product requirement change).
- Architecture: initialization command guidance currently shows `pip`; requires update to `uv`.
- UX: no impact.
- Technical artifacts needing updates:
  - `backend/pyproject.toml`
  - `backend/requirements.txt` and `backend/requirements-dev.txt` (replace or deprecate)
  - `backend/uv.lock` (new)
  - `README.md`
  - `docker-compose.yml`

### Technical Impact
- Code/runtime behavior of `/v1` endpoints unchanged.
- Build/run workflow changes for backend contributors and local containers.
- Improves reproducibility and install/sync performance.

## 3. Recommended Approach

### Selected Path
**Direct Adjustment** (Option 1)

### Why
- Lowest-effort, lowest-risk path.
- Directly addresses stated goals (repo-local environment + faster installs).
- No product-scope or UX changes required.

### Effort / Risk / Timeline
- Effort: **Low**
- Risk: **Low**
- Timeline impact: **Minimal** (same sprint, no resequencing required)

## 4. Detailed Change Proposals

### 4.1 Story Change (Approved)

Story: **1.1 Set Up Initial Project from Starter Template**
Section: setup and implementation details

OLD:
- Backend setup references `python -m venv`, `pip install -r requirements.txt`
- Dependency source is `requirements.txt` + `requirements-dev.txt`
- Docker backend startup installs with `pip install -r requirements.txt`

NEW:
- Backend setup uses `uv`-managed project environment and sync flow.
- Dependencies are declared in `backend/pyproject.toml` (project + groups).
- Lockfile is committed as `backend/uv.lock`.
- Local setup uses `uv sync`; runtime uses `uv run ...`.
- Docker backend startup uses `uv sync` then `uv run uvicorn ...`.

Rationale:
- Enforces repo-local reproducibility and improves install/sync speed.

### 4.2 PRD Change (Approved)

Artifact: **PRD**
Section: none

OLD:
- No explicit backend package-manager requirement.

NEW:
- No PRD text changes.

Rationale:
- Package manager choice is implementation-level, not product requirement.

### 4.3 Architecture Change (Approved)

Artifact: **Architecture**
Section: Starter Template Evaluation -> Initialization Command

OLD:
```bash
# backend
python -m venv .venv
source .venv/bin/activate
pip install "fastapi[standard]"
```

NEW:
```bash
# backend
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Additional architecture note:
- Backend dependency management standard is `uv` with `pyproject.toml` + committed `uv.lock`.

Rationale:
- Aligns architecture guidance with desired and implemented workflow.

## 5. Implementation Handoff

### Scope Classification
**Minor** change scope.

### Route
- **Development team / implementation agent** for direct execution.

### Deliverables
- Migrate backend dependency management to `uv`.
- Update relevant docs and compose command.
- Preserve existing backend behavior and tests.

### Success Criteria
- Backend installs/syncs via `uv` from repo without manual pip workflow.
- `backend/uv.lock` committed.
- README and compose reflect `uv` commands.
- Existing backend smoke tests continue to pass.

## Checklist Status Snapshot

### Section 1: Understand Trigger and Context
- 1.1 Trigger story identified: `[x] Done`
- 1.2 Core problem defined: `[x] Done`
- 1.3 Evidence gathered: `[x] Done`

### Section 2: Epic Impact Assessment
- 2.1 Current epic evaluated: `[x] Done`
- 2.2 Epic-level changes determined: `[x] Done`
- 2.3 Remaining epics reviewed: `[x] Done`
- 2.4 Future epic invalidation/new epic check: `[x] Done`
- 2.5 Priority/order review: `[x] Done`

### Section 3: Artifact Conflict and Impact
- 3.1 PRD conflict: `[N/A]`
- 3.2 Architecture conflict: `[x] Done`
- 3.3 UX conflict: `[N/A]`
- 3.4 Other artifacts impact: `[x] Done`

### Section 4: Path Forward Evaluation
- 4.1 Direct Adjustment: `[x] Viable`
- 4.2 Potential Rollback: `[x] Not viable`
- 4.3 PRD MVP Review: `[x] Not viable`
- 4.4 Recommended path selected: `[x] Done`

### Section 5: Sprint Change Proposal Components
- 5.1 Issue summary: `[x] Done`
- 5.2 Impact and adjustments documented: `[x] Done`
- 5.3 Recommended path with rationale: `[x] Done`
- 5.4 MVP impact and action plan: `[x] Done`
- 5.5 Handoff plan: `[x] Done`

## Approval and Handoff Record

- User approval status: **Approved** (`yes`)
- Approval date: 2026-03-01
- Scope classification: **Minor**
- Route: **Development team / implementation agent**
- Handoff deliverables confirmed:
  - Apply backend `uv` migration changes
  - Preserve API behavior and test outcomes
  - Keep docs and compose commands aligned with `uv`

### Workflow Execution Log

- Correct-course workflow completed through final approval.
- Handoff recorded to Minor-scope implementation path.
- No epic/story renumbering required; sprint-status structural updates not required.
