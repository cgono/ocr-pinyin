# Sprint Change Proposal — Auto-Versioning and render.yaml CI Validation

**Date:** 2026-03-29
**Status:** Approved
**Scope Classification:** Minor

---

## Section 1: Issue Summary

Manual version management in `frontend/package.json` and `backend/pyproject.toml` is error-prone — both files are pinned at `0.1.0` with no automation to increment them or publish GitHub Releases. The project already uses conventional commits (`feat:`, `fix:`) on every merge, which is the exact prerequisite for release-please to drive versioning automatically.

A complementary gap was also identified: `render.yaml` has no CI validation. A malformed blueprint file would only surface at deploy time (on Render), rather than at PR review time. The Render CLI provides a `render blueprints validate` command that requires no authentication and can run in CI.

Both gaps are additive and self-contained; neither requires changes to application logic or existing API contracts.

---

## Section 2: Impact Analysis

**Epic Impact:**
- Epic 4 (UX Polish, Cost Guardrails & Safe Usage Control) is in-progress with all existing stories done. Story 4.7 is added to this epic before close. The CI/infrastructure flavour of Story 4.7 is consistent with Epic 4 (which already absorbed Story 3.6 CI gate improvements and Story 4.0 process documentation).

**Story Impact:**
- No existing stories are affected.
- New Story 4.7 is added to Epic 4.

**Artifact Conflicts:**
- PRD: Versioning Strategy section extended with one bullet noting release-please as the release mechanism.
- Architecture: Deployment Structure section extended with a paragraph describing the release-please monorepo setup.
- CI: `ci.yml` gains a `render-yaml-check` job.

**Technical Impact:**
- Three new files: `.github/workflows/release-please.yml`, `release-please-config.json`, `.release-please-manifest.json`.
- One updated file: `.github/workflows/ci.yml` (new job, no changes to existing jobs).
- No application code changes. No changes to `render.yaml`, `pyproject.toml`, or `package.json` at story creation time (release-please will manage version bumps from this point forward).

---

## Section 3: Recommended Approach

**Option 1 — Direct Adjustment** (selected).

Add Story 4.7 to Epic 4 and implement directly. Low effort, low risk. Conventional commits are already in use, so no process change is required.

**Rationale:** The change is purely additive infrastructure. It does not affect Epic 5 (History) or any application contracts. The Render CLI validate command requires no authentication token, making CI setup straightforward.

**Effort:** Low.
**Risk:** Low. The release-please action creates PRs rather than auto-merging, so the first release cycle is fully observable before any version is actually published.

---

## Section 4: Detailed Change Proposals

### Story 4.7 (New) — Release-Please Versioning + render.yaml CI Validation

Added to Epic 4.

```
As Clint,
I want frontend and backend versions incremented automatically based on
conventional commits with GitHub Releases created on merge, AND I want
render.yaml validated in CI,
So that I never manually bump versions or publish releases, and a malformed
render.yaml is caught before it reaches a deploy.

Acceptance Criteria:

--- Release-Please ---

Given conventional commits have been merged to main
When the release-please workflow runs
Then a "release PR" is opened (or updated) with CHANGELOG.md updated,
frontend/package.json version bumped, and backend/pyproject.toml version bumped

Given the release PR is merged
When release-please runs post-merge
Then a GitHub Release is created automatically with the version tag and
changelog content
And frontend and backend are versioned independently (monorepo)

--- render.yaml Validation ---

Given render.yaml exists in the repo root
When CI runs on pull requests and main/staging branch pushes
Then the Render CLI downloads and runs 'render blueprints validate render.yaml',
failing CI if the file fails Render's own schema validation
And the check runs as a new job in the existing CI workflow

Given render.yaml is valid
When the check runs
Then it passes and does not block merge

Given render.yaml contains an invalid value or missing required field
When the check runs
Then CI fails with Render's validation error output

--- General ---

Given all existing CI checks
When story 4.7 is implemented
Then all existing jobs continue to pass unaffected
```

### PRD — Versioning Strategy

```
OLD:
- API starts at `/v1` from day one.
- Breaking changes require new version path; non-breaking additions stay in `v1`.

NEW:
- API starts at `/v1` from day one.
- Breaking changes require new version path; non-breaking additions stay in `v1`.
- Package releases (frontend and backend) are managed via release-please using
  conventional commits. GitHub Releases are created automatically on merge to main.
```

### Architecture — Deployment Structure

```
OLD:
**Deployment Structure:**
- Current local deployment via Docker Compose.
- Hosted deployment target is Render, with frontend and backend split into
  separate services and optional Blueprint-based config in `render.yaml`.

NEW (append paragraph):
**Release Versioning:**
Package versioning is managed by release-please (googleapis/release-please-action),
configured for a monorepo with two independent packages: `frontend` (node) and
`backend` (python). `release-please-config.json` defines both packages.
Conventional commits drive semantic version bumps. On merge to main, release-please
creates a release PR updating `CHANGELOG.md`, `frontend/package.json`, and
`backend/pyproject.toml`; merging the release PR creates a GitHub Release and tags
the commit. Package version files: `frontend/package.json` (version field) and
`backend/pyproject.toml` ([project].version field).
```

### New Files

- `.github/workflows/release-please.yml` — runs on push to main; calls release-please-action v4 with monorepo config; requires `contents: write` and `pull-requests: write` (scoped to this workflow only, not `ci.yml`).
- `release-please-config.json` — defines `frontend` (node) and `backend` (python) packages.
- `.release-please-manifest.json` — seeded at `0.1.0` for both packages to match current versions.

### Updated: `.github/workflows/ci.yml`

New job `render-yaml-check` added:
- Installs Render CLI via official curl installer.
- Runs `render blueprints validate render.yaml`.
- No authentication required.
- Runs alongside existing `backend-checks`, `frontend-checks`, `contract-checks`.

---

## Section 5: Implementation Handoff

**Scope:** Minor — direct implementation by development team.

**Deliverables:**
1. Story 4.7 added to `epics.md`
2. `sprint-status.yaml` updated with story 4.7 entry
3. PRD versioning section updated
4. Architecture deployment/versioning section updated
5. `.github/workflows/release-please.yml` created
6. `release-please-config.json` created
7. `.release-please-manifest.json` created
8. `.github/workflows/ci.yml` updated with render-yaml-check job

**Success Criteria:**
- Release-please workflow triggers on push to main and opens a release PR.
- Merging the release PR creates a GitHub Release.
- `render blueprints validate render.yaml` passes in CI.
- All existing CI jobs continue to pass.
