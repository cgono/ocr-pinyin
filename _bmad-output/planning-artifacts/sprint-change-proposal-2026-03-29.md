# Sprint Change Proposal — 2026-03-29

**Status:** Approved
**Classification:** Minor — direct implementation by development team
**Proposed by:** Clint
**Date:** 2026-03-29

---

## Section 1: Issue Summary

The project currently deploys only to production (`main` → Render). There is no intermediate
environment to validate changes before they reach users. Adding a `staging` environment lets us
catch integration or deployment issues before the final merge to `main`.

Render's Blueprint model and the existing `APP_ENV`/`VITE_APP_ENV` → Sentry `environment` tag
wiring already support this with no application code changes. The Sentry `environment` field is
already read from `APP_ENV` in `backend/app/core/sentry.py` and from `VITE_APP_ENV` in
`frontend/src/main.jsx` — setting `APP_ENV: staging` in the staging services is sufficient.

---

## Section 2: Impact Analysis

**Epic Impact:** None. All stories in Epics 1–4 are done. Epic 5 is backlog and unaffected.

**Story Impact:** No story additions or removals. Pure infrastructure and documentation change.

**Artifact Conflicts / Updates Required:**

| Artifact | Change |
|----------|--------|
| `render.yaml` | Append staging service blocks (backend + frontend) with `branch: staging` and `APP_ENV: staging` |
| `.github/workflows/ci.yml` | Add `staging` to push trigger branches |
| `docs/deployment.md` | Add staging environment section |

**Technical Impact:**
Two new Render services (`ocr-pinyin-backend-staging`, `ocr-pinyin-frontend-staging`) created from
the same Blueprint, each tracking the `staging` branch. No application code changes required.

---

## Section 3: Recommended Approach

**Option 1 — Direct Adjustment** (selected)

Append staging services to `render.yaml`, extend CI to verify `staging` branch pushes, and
document the two-environment workflow in `docs/deployment.md`.

- Effort: Low
- Risk: Low
- Timeline impact: None

---

## Section 4: Detailed Change Proposals

### Change 1 — `render.yaml`: Append staging services

Append the following after the existing production services:

```yaml
  - type: web
    name: ocr-pinyin-backend-staging
    runtime: python
    plan: free
    rootDir: backend
    branch: staging
    buildCommand: pip install "uv==0.10.11" && uv sync --no-dev --frozen
    startCommand: APP_VERSION=$(python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['project']['version'])") uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /v1/health
    envVars:
      - key: APP_ENV
        value: staging
      - key: OCR_PROVIDER
        value: google_vision
      - key: SENTRY_DSN
        sync: false
      - key: SENTRY_TRACES_SAMPLE_RATE
        value: "1.0"
      - key: GOOGLE_APPLICATION_CREDENTIALS_JSON
        sync: false
      - key: PYTHON_VERSION
        value: "3.12.10"
      - key: UV_VERSION
        value: "0.10.11"
      - key: CORS_ALLOW_ORIGINS
        sync: false

  - type: web
    name: ocr-pinyin-frontend-staging
    runtime: static
    rootDir: frontend
    branch: staging
    buildCommand: npm ci && VITE_APP_VERSION=$(node -p "require('./package.json').version") npm run build
    staticPublishPath: dist
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
    envVars:
      - key: VITE_APP_ENV
        value: staging
      - key: VITE_API_BASE_URL
        sync: false
      - key: VITE_SENTRY_DSN
        sync: false
      - key: VITE_SENTRY_TRACES_SAMPLE_RATE
        value: "1.0"
```

**Rationale:** `APP_ENV: staging` flows to `sentry_sdk.init(environment=...)` (no code change
needed). Staging uses `SENTRY_TRACES_SAMPLE_RATE: 1.0` to capture all traces for debugging, vs
production's `0.2`.

### Change 2 — `.github/workflows/ci.yml`: Add staging to push trigger

```
OLD:
  push:
    branches:
      - main

NEW:
  push:
    branches:
      - main
      - staging
```

**Rationale:** CI currently runs on PRs and `main` pushes only. Staging branch pushes should also
be verified before Render deploys them.

### Change 3 — `docs/deployment.md`: Add staging environment section

Add a **Staging Environment** section documenting:
- `staging` branch as the pre-production integration buffer
- Staging service names and URLs
- Env vars to set in the Render dashboard for staging services
- Promotion workflow: merge `staging` → `main` to deploy to production
- Sentry environment filtering instructions

---

## Section 5: Implementation Handoff

**Scope:** Minor — development team implements directly.

**Files to update:**
1. `render.yaml` — append staging services
2. `.github/workflows/ci.yml` — add `staging` to push branches
3. `docs/deployment.md` — add staging workflow section

**Post-implementation steps (manual, in Render dashboard):**

After pushing the `render.yaml` changes, Render will detect the new services in the Blueprint.
Set the following secrets in each staging service's Environment tab:

| Service | Variable | Value |
|---------|----------|-------|
| `ocr-pinyin-backend-staging` | `SENTRY_DSN` | Same DSN as production (or a separate Sentry project) |
| `ocr-pinyin-backend-staging` | `GOOGLE_APPLICATION_CREDENTIALS_JSON` | Same GCP key as production |
| `ocr-pinyin-backend-staging` | `CORS_ALLOW_ORIGINS` | `https://ocr-pinyin-frontend-staging.onrender.com` |
| `ocr-pinyin-frontend-staging` | `VITE_API_BASE_URL` | `https://ocr-pinyin-backend-staging.onrender.com` |
| `ocr-pinyin-frontend-staging` | `VITE_SENTRY_DSN` | Same DSN as above |

**Success criteria:**
- Staging services auto-deploy on push to `staging`
- `GET https://ocr-pinyin-backend-staging.onrender.com/v1/health` returns healthy
- Sentry dashboard shows `staging` as a selectable environment filter (distinct from `production`)
- Merging `staging` → `main` triggers a production deploy
