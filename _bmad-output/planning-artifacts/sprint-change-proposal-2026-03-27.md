# Sprint Change Proposal — 2026-03-27

## Section 1: Issue Summary

**Problem statement:** The existing CI pipeline (established in Story 1.2) is missing two quality gates that leave regressions undetected:

1. **`uv.lock` can silently go out of sync.** The current `uv sync --dev` command in CI will regenerate `uv.lock` on the fly if it is stale. This means a developer can update `pyproject.toml` without committing an updated lockfile, CI will pass, and the committed lockfile no longer reflects the resolved dependencies that were actually tested.

2. **The frontend production build is never verified.** CI runs ESLint and Vitest but never executes `vite build`. A JSX syntax error, a missing import, or a broken asset reference would pass CI and only surface at deploy time.

**Discovery context:** Identified during code review of the `feat/epic-3` branch at the close of Epic 3.

**Note on `package-lock.json`:** No equivalent change is needed for the frontend lockfile. `npm ci` (already in the workflow) already fails hard if `package-lock.json` is out of sync with `package.json` — this is a design property of `npm ci`, unlike `uv sync`.

---

## Section 2: Impact Analysis

**Epic Impact:**
- Epic 3 (`in-progress`, all stories done) — add Story 3.6 before closing.
- Epics 4 and 5 (`backlog`) — unaffected; benefit from stronger CI gates before those stories begin.

**Story Impact:**
- Story 1.2 acceptance criteria are updated to match what CI now actually enforces.
- New Story 3.6 is added to Epic 3 to carry the implementation.

**Artifact Conflicts:**
| Artifact | Change |
|---|---|
| `.github/workflows/ci.yml` | Add `--frozen` to `uv sync`; add `npm run build` step |
| `_bmad-output/planning-artifacts/epics.md` | Update Story 1.2 AC; add Story 3.6 |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | Add story 3.6 entry |

**Technical Impact:** Additive CI changes only. No application code changes.

---

## Section 3: Recommended Approach

**Selected path:** Option 1 — Direct Adjustment.

**Rationale:** The issue is a narrow CI gap with no architectural implications. Two targeted changes resolve it fully:

1. Change `uv sync --dev` → `uv sync --frozen --dev` in all CI jobs that install backend dependencies. This causes CI to fail immediately if `uv.lock` is stale rather than silently regenerating it.
2. Add `npm run build --prefix frontend` to the `frontend-checks` job after ESLint, so a broken production bundle fails CI before merge.

Backend build check is explicitly skipped — Ruff + Pytest already provide sufficient signal for Python code correctness.

**Effort:** Low
**Risk:** Low
**Timeline impact:** None — no sprint re-sequencing required

---

## Section 4: Detailed Change Proposals

### Change 1: `ci.yml` — Lock file enforcement

**File:** `.github/workflows/ci.yml`

**`backend-checks` job:**
```
OLD: uv sync --dev
NEW: uv sync --frozen --dev
```

**`contract-checks` job:**
```
OLD: uv sync --dev
NEW: uv sync --frozen --dev
```

**Rationale:** `--frozen` makes `uv sync` fail with a non-zero exit code if `uv.lock` would need to be updated, instead of updating it silently.

---

### Change 2: `ci.yml` — Frontend build check

**File:** `.github/workflows/ci.yml`

**`frontend-checks` job** — add after the ESLint step:
```
NEW step:
  - name: Build
    run: npm run build --prefix frontend
```

**Rationale:** Vite build exercises the full module graph, TypeScript/JSX compilation, and asset resolution. ESLint and Vitest do not catch broken imports or missing assets.

---

### Change 3: `epics.md` — Update Story 1.2 acceptance criteria

**File:** `_bmad-output/planning-artifacts/epics.md`

**Story 1.2, add to acceptance criteria:**
```
OLD:
**Then** backend lint/test checks execute (Ruff and backend tests)
**And** frontend lint/test checks execute (ESLint and frontend tests).

NEW:
**Then** backend lint/test checks execute (Ruff and backend tests)
**And** frontend lint/test checks execute (ESLint, Vite production build, and frontend tests)
**And** backend dependency lockfile is verified in sync (`uv.lock` matches `pyproject.toml`).
```

---

### Change 4: `epics.md` — Add Story 3.6

**File:** `_bmad-output/planning-artifacts/epics.md`

Add after Story 3.5:

```
### Story 3.6: Strengthen CI Build and Lock File Checks

As Clint,
I want the CI pipeline to verify the frontend production build and enforce lockfile
integrity on the backend,
So that broken builds and dependency drift are caught before merge rather than at deploy time.

**Acceptance Criteria:**

**Given** the frontend has JavaScript/JSX source files
**When** CI runs the frontend-checks job
**Then** `vite build` executes after ESLint
**And** CI fails if the production bundle cannot be generated.

**Given** backend dependencies are declared in pyproject.toml
**When** CI runs any job that installs backend dependencies
**Then** `uv sync --frozen` is used instead of plain `uv sync`
**And** CI fails if `uv.lock` is out of sync with `pyproject.toml`.

**Given** any required quality check fails
**When** CI completes
**Then** the pipeline status is failed and merge is blocked.
```

---

## Section 5: Implementation Handoff

**Scope classification:** Minor — development team implements directly.

**Handoff:** Dev agent.

**Deliverables:**
- Updated `.github/workflows/ci.yml`
- Updated `epics.md` (Story 1.2 AC + Story 3.6)
- Updated `sprint-status.yaml` (Story 3.6 entry)

**Success criteria:**
- `uv sync --frozen --dev` is used in all backend CI jobs
- `npm run build --prefix frontend` step exists in `frontend-checks`
- CI passes on the current branch with the new steps in place
