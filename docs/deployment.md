# Deployment Guide - Render

This project deploys to Render using a Blueprint (`render.yaml` at the repository root).

## One-Time Setup

### 1. Connect Repository

1. Log in to [render.com](https://render.com) and create a new Blueprint service.
2. Connect your GitHub repository.
3. Render will detect `render.yaml` and propose creating both services.

### 2. Set Dashboard Environment Variables

> **Important — set these before any traffic testing.** When the Blueprint is first applied both services deploy immediately. The backend starts with no `CORS_ALLOW_ORIGINS` set, which means it falls back to localhost-only CORS and every real browser request will fail until you set the value. Set all secrets in the table below as soon as both service URLs are known, then verify the deployment.

After Render creates the services, set the following secrets in each service's Environment tab.

#### Backend (`ocr-pinyin-backend`)

| Variable | Where to get it |
| --- | --- |
| `SENTRY_DSN` | Sentry project -> Settings -> Client Keys |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | GCP Console -> IAM -> Service Accounts -> your key -> JSON (paste as a single line) |
| `CORS_ALLOW_ORIGINS` | Set to `https://<frontend-service-name>.onrender.com` after the frontend is deployed |

#### Frontend (`ocr-pinyin-frontend`)

| Variable | Where to get it |
| --- | --- |
| `VITE_API_BASE_URL` | Set to `https://<backend-service-name>.onrender.com` after the backend is deployed |
| `VITE_SENTRY_DSN` | Same Sentry project DSN as the backend, or a separate frontend project |

`VITE_*` variables are baked into the frontend bundle at build time. After setting them, manually redeploy the frontend service so Vite includes the updated values.

### 3. Verify CORS Wiring

The backend `CORS_ALLOW_ORIGINS` must match the exact frontend origin, including scheme and host, with no trailing slash:

```dotenv
CORS_ALLOW_ORIGINS=https://ocr-pinyin-frontend.onrender.com
```

If the frontend URL changes, update this value and redeploy the backend.

## Verify The Deployment

1. Check backend health at `https://<backend>.onrender.com/v1/health` and confirm it returns `{"status": "healthy"}`.
2. Open `https://<frontend>.onrender.com` in a browser and confirm the upload form renders.
3. Submit a test image and confirm the frontend receives pinyin output without CORS errors.

## Staging Environment

The project runs two environments: **staging** (from the `staging` branch) and **production** (from `main`).

### Branch Strategy

```
feature branches  →  staging  →  main (production)
```

- Merge feature branches into `staging` to validate before going live.
- Merge `staging` into `main` to promote to production.
- Render auto-deploys each environment on push to its branch.

### Staging Services

| Service | Render name |
|---------|-------------|
| Backend | `ocr-pinyin-backend-staging` |
| Frontend | `ocr-pinyin-frontend-staging` |

### Staging Environment Variables (set in Render dashboard)

Set these in each staging service's Environment tab after the Blueprint creates the services.

#### Backend (`ocr-pinyin-backend-staging`)

| Variable | Value |
|----------|-------|
| `SENTRY_DSN` | Same DSN as production (Sentry separates environments by tag) |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | Same GCP service account key as production |
| `CORS_ALLOW_ORIGINS` | `https://ocr-pinyin-frontend-staging.onrender.com` |

#### Frontend (`ocr-pinyin-frontend-staging`)

| Variable | Value |
|----------|-------|
| `VITE_API_BASE_URL` | `https://ocr-pinyin-backend-staging.onrender.com` |
| `VITE_SENTRY_DSN` | Same DSN as the backend |

`APP_ENV: staging` and `VITE_APP_ENV: staging` are set in `render.yaml` and flow automatically to
the Sentry `environment` tag — no manual action needed for Sentry tagging.

### Verify Staging

1. Check backend health at `https://ocr-pinyin-backend-staging.onrender.com/v1/health`.
2. Open `https://ocr-pinyin-frontend-staging.onrender.com` and confirm the upload form renders.
3. Submit a test image and confirm pinyin output arrives without CORS errors.

### Sentry Environment Filtering

In the Sentry dashboard, use the **Environment** dropdown to filter issues and traces by
`staging` or `production` independently.

---

## Redeploy

Render auto-deploys on every push to the connected branch, typically `main`.

To trigger a manual redeploy without a code push, open the service in the Render dashboard and choose `Manual Deploy` -> `Deploy latest commit`.

## Rollback

1. Open the service in the Render dashboard.
2. Go to the `Deploys` tab.
3. Find the last successful deploy.
4. Open the overflow menu and choose `Redeploy` to restore that version.

Rollback takes effect immediately and does not require reverting git history.
