# Story 4.7: Release-Please Versioning + render.yaml CI Validation

Status: done

## Story

As Clint,
I want frontend and backend versions incremented automatically based on conventional commits with GitHub Releases created on merge, AND I want render.yaml validated in CI,
so that I never manually bump versions or publish releases, and a malformed render.yaml is caught before it reaches a deploy.

## Acceptance Criteria

1. **Given** conventional commits have been merged to main, **When** the release-please workflow runs, **Then** a "release PR" is opened (or updated) with `CHANGELOG.md` updated, `frontend/package.json` version bumped, and `backend/pyproject.toml` version bumped.

2. **Given** the release PR is merged, **When** release-please runs post-merge, **Then** a GitHub Release is created automatically with the version tag and changelog content **And** frontend and backend are versioned independently (monorepo).

3. **Given** `render.yaml` exists in the repo root, **When** CI runs on pull requests and main/staging branch pushes, **Then** the Render CLI downloads and runs `render blueprints validate render.yaml`, failing CI if the file fails Render's own schema validation **And** the check runs as a new job in the existing CI workflow.

4. **Given** `render.yaml` is valid, **When** the check runs, **Then** it passes and does not block merge.

5. **Given** `render.yaml` contains an invalid value or missing required field, **When** the check runs, **Then** CI fails with Render's validation error output.

6. **Given** all existing CI checks, **When** story 4.7 is implemented, **Then** all existing jobs continue to pass unaffected.

## Tasks / Subtasks

- [x] Verify or create `.github/workflows/release-please.yml` (AC: 1–2)
  - [x] Trigger: `push` to `main` only
  - [x] Permissions: `contents: write`, `pull-requests: write`
  - [x] Single step: `googleapis/release-please-action@v4` with `config-file: release-please-config.json` and `manifest-file: .release-please-manifest.json`

- [x] Verify or create `release-please-config.json` (AC: 1–2)
  - [x] Include `$schema` pointing to the release-please config schema
  - [x] `packages.frontend` → `release-type: node`, `package-name: ocr-pinyin-frontend`
  - [x] `packages.backend` → `release-type: python`, `package-name: ocr-pinyin-backend`

- [x] Verify or create `.release-please-manifest.json` (AC: 1–2)
  - [x] Seed both `frontend` and `backend` at `"0.1.0"` (matching current versions in `frontend/package.json` and `backend/pyproject.toml`)

- [x] Verify `render-yaml-check` job exists in `.github/workflows/ci.yml` (AC: 3–5)
  - [x] Job installs Render CLI via official curl installer
  - [x] Job runs `render blueprints validate render.yaml`
  - [x] Job runs on same triggers as other CI jobs (PRs, main, staging pushes)
  - [x] Existing jobs (`backend-checks`, `frontend-checks`, `contract-checks`) are unchanged

- [x] Smoke-check: confirm `frontend/package.json` has a `"version"` field and `backend/pyproject.toml` has `[project].version` — release-please needs these to exist to apply bumps (AC: 1–2)

## Dev Notes

### Critical: Files May Already Exist in Working Tree

The sprint change proposal (2026-03-29) that created this story also created the implementation artifacts as part of the proposal process. **Before creating any file, check whether it already exists**:

- `.github/workflows/release-please.yml` — may be present (untracked)
- `release-please-config.json` — may be present (untracked)
- `.release-please-manifest.json` — may be present (untracked)
- `.github/workflows/ci.yml` — may already have `render-yaml-check` job added (modified)

**If files exist and look correct, do not recreate them. Verify content and move on.**

### Expected Final State of Each File

**`.github/workflows/release-please.yml`**
```yaml
name: Release Please

on:
  push:
    branches:
      - main

permissions:
  contents: write
  pull-requests: write

jobs:
  release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: googleapis/release-please-action@v4
        with:
          config-file: release-please-config.json
          manifest-file: .release-please-manifest.json
```

**`release-please-config.json`**
```json
{
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "packages": {
    "frontend": {
      "release-type": "node",
      "package-name": "ocr-pinyin-frontend"
    },
    "backend": {
      "release-type": "python",
      "package-name": "ocr-pinyin-backend"
    }
  }
}
```

**`.release-please-manifest.json`**
```json
{
  "frontend": "0.1.0",
  "backend": "0.1.0"
}
```

**`render-yaml-check` job to add/verify in `.github/workflows/ci.yml`**
```yaml
  render-yaml-check:
    runs-on: ubuntu-latest
    env:
      RENDER_API_KEY: ${{ secrets.RENDER_API_KEY }}
      RENDER_WORKSPACE_ID: ${{ vars.RENDER_WORKSPACE_ID }}
      CI: true
    steps:
      - name: Checkout
        uses: actions/checkout@v6

      - name: Validate required secrets
        run: |
          [[ -n "$RENDER_API_KEY" ]] || { echo "ERROR: RENDER_API_KEY secret not configured. See docs/deployment.md for CI setup instructions."; exit 1; }
          [[ -n "$RENDER_WORKSPACE_ID" ]] || { echo "ERROR: RENDER_WORKSPACE_ID variable not configured. See docs/deployment.md for CI setup instructions."; exit 1; }

      - name: Install Render CLI
        run: |
          curl -fsSL https://raw.githubusercontent.com/render-oss/cli/refs/tags/v2.15.0/bin/install.sh | sh
          echo "$HOME/.render/bin" >> $GITHUB_PATH

      - name: Validate render.yaml
        run: render blueprints validate render.yaml --workspace "$RENDER_WORKSPACE_ID" --output text --confirm
```

### How Release-Please Works (Monorepo)

- Runs on every push to `main`; reads `release-please-config.json` for package definitions
- Compares commits since last release tag to determine version bump (major/minor/patch per conventional commit type)
- On first run after this story lands, it will open a "Release PR" updating `CHANGELOG.md`, `frontend/package.json`, and `backend/pyproject.toml`
- **Does not auto-merge** — Clint reviews and merges the Release PR manually
- After merging the Release PR, release-please creates a GitHub Release + tag
- `CHANGELOG.md` files are managed entirely by release-please; do NOT create them manually

### Version Files release-please Will Manage

| Package | File | Field |
|---------|------|-------|
| `frontend` | `frontend/package.json` | `"version"` |
| `backend` | `backend/pyproject.toml` | `[project] version` |

Both are currently at `0.1.0`. The manifest seeds at `0.1.0` to match. release-please will bump from there.

### Render CLI Validation

- `render blueprints validate render.yaml` requires `RENDER_API_KEY` (secret) and `RENDER_WORKSPACE_ID` (variable) — configure both under **Settings → Secrets and variables → Actions** in the GitHub repository (see `docs/deployment.md#ci-setup`)
- CLI is installed from the official install script pinned to a specific release: `https://raw.githubusercontent.com/render-oss/cli/refs/tags/v2.15.0/bin/install.sh`
- The install script places the binary in `~/.render/bin`; the CI job appends this to `$GITHUB_PATH` so subsequent steps can find it
- Validates Render's own blueprint schema, catching errors (missing required fields, invalid service types, etc.) before they reach a deploy
- Runs alongside existing CI jobs (no dependency ordering needed)

### Existing CI Structure (ci.yml)

Current jobs that must remain untouched:
- `backend-checks` — Ruff + Pytest via `uv sync --frozen --dev`
- `frontend-checks` — ESLint + Vite build + Vitest via `npm ci`
- `contract-checks` — API envelope contract tests

All jobs run on: `pull_request` and `push` to `main` or `staging`.

The new `render-yaml-check` job must use the same triggers.

### No Application Code Changes

This story is **CI/configuration only**. Do not touch:
- Any files under `backend/app/` or `frontend/src/`
- `backend/pyproject.toml` (release-please will manage the version field)
- `frontend/package.json` (release-please will manage the version field)
- `render.yaml` (validation target, not modified by this story)
- Any test files

### Architecture Compliance

- Architecture doc (Deployment Structure section): "Render Blueprint via `render.yaml`" and "release-please (`googleapis/release-please-action`) configured for a monorepo with two independent packages"
- PR permissions model: `release-please.yml` uses `contents: write` + `pull-requests: write` scoped to that workflow only; `ci.yml` retains `contents: read` for all existing jobs — do not change `ci.yml` permissions

### Git Intelligence

- `926bf20` — staging env commit: `ci.yml` updated and `render.yaml` validated; this is the context that makes render-yaml-check immediately meaningful
- `9dc7a31` — Story 4-6: last application story; all 164 backend tests pass; no changes to CI workflow structure
- Conventional commits (`feat:`, `fix:`) are in use on every merge — this is the prerequisite for release-please to work correctly

### What Already Exists (Do Not Reinvent)

- `render.yaml` — already present at repo root; this story validates it, does not modify it
- Conventional commit discipline — already established across all merges in this project
- `ci.yml` trigger pattern (`pull_request` + `push` to `main`/`staging`) — replicate exactly for the new job
- `actions/checkout@v6` — version already in use across all CI jobs; use same version

### Verification

After implementing, run locally if possible:
```bash
# Verify render.yaml validates (if Render CLI installed locally)
render blueprints validate render.yaml

# Confirm no yaml syntax errors in CI files
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release-please.yml'))"

# Confirm manifest JSON is valid
python3 -c "import json; json.load(open('.release-please-manifest.json'))"
python3 -c "import json; json.load(open('release-please-config.json'))"
```

The full CI run will validate everything once the PR is opened.

### References

- Sprint change proposal: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-29-versioning.md`
- Epic spec: `_bmad-output/planning-artifacts/epics.md` — Epic 4, Story 4.7
- Architecture: `_bmad-output/planning-artifacts/architecture.md` — Release Versioning section (Deployment Structure)
- Existing CI: `.github/workflows/ci.yml`
- release-please action: `googleapis/release-please-action@v4`
- Render CLI: `render blueprints validate`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References
- 2026-03-29: Verified `.github/workflows/release-please.yml`, `release-please-config.json`, and `.release-please-manifest.json` already matched the story requirements.
- 2026-03-29: Updated `.github/workflows/ci.yml` so `render-yaml-check` passes `RENDER_API_KEY` and `RENDER_WORKSPACE_ID` into Render CLI validation; current Render CLI requires explicit workspace context.
- 2026-03-29: Validated workflow YAML with Ruby `YAML.load_file(...)` and release-please JSON with Python `json.load(...)`.
- 2026-03-29: Local full backend/frontend test execution was not runnable in this sandbox because `node`/`npm` are unavailable and the checked-in backend virtualenv contains incompatible compiled dependencies (`pydantic_core`, `ruff` binary).

### Completion Notes List
- Verified the release-please workflow, monorepo config, and version manifest were already present and aligned with the story.
- Corrected the Render validation job to use authenticated workspace-aware invocation: `render blueprints validate render.yaml --workspace "$RENDER_WORKSPACE_ID" --output text --confirm`.
- Confirmed `frontend/package.json` and `backend/pyproject.toml` both expose version `0.1.0` for release-please manifest seeding.
- Confirmed `.github/workflows/ci.yml` and `.github/workflows/release-please.yml` parse as valid YAML and both release-please JSON files parse cleanly.

### File List
- .github/workflows/ci.yml
- .github/workflows/release-please.yml
- .release-please-manifest.json
- release-please-config.json
- _bmad-output/implementation-artifacts/4-7-release-please-versioning-and-render-yaml-ci-validation.md

## Change Log

- 2026-03-29: Verified release-please monorepo setup artifacts, fixed Render CLI validation to include workspace-aware auth inputs, and marked story complete for review.
