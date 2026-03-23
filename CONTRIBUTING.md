# Contributing

## Prerequisites

Install these tools before cloning or running anything.

### Python — uv

[uv](https://docs.astral.sh/uv/) manages the Python version and all backend dependencies.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify: `uv --version`

### Node.js and npm

Install Node.js 24+ (includes npm 11+). Use [nvm](https://github.com/nvm-sh/nvm) or download directly from [nodejs.org](https://nodejs.org).

Verify: `node --version` and `npm --version`

### BMAD (AI workflow tooling)

This project uses [BMAD](https://github.com/bmadcode/bmad-method) for sprint planning, story generation, and AI-assisted development workflows. Install the latest version after cloning:

```bash
npx bmad-method install
```

BMAD files are not committed to this repo — always install from the latest release.

---

## Local setup (without Docker)

### Backend

```bash
cd backend
uv sync --dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`.

### Environment variables

Copy the example files and fill in your credentials:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

The key backend variable is `GOOGLE_APPLICATION_CREDENTIALS_JSON` — set this to your Google Cloud Vision service account JSON to enable OCR. Without it, the service falls back to a no-op provider.

---

## Running tests

### Backend

```bash
cd backend
uv run pytest
uv run ruff check .
```

### Frontend

```bash
cd frontend
npm test
npm run lint
```

---

## CI quality gates

CI runs on pull requests and pushes to `main`. Three jobs must pass before merge:

| Job | What it checks |
|-----|---------------|
| `backend-checks` | Ruff lint + full pytest suite |
| `frontend-checks` | ESLint + Vitest suite |
| `contract-checks` | `/v1/process` response envelope contract tests |

---

## Making changes

### Scope changes and technology substitutions

If you want to change a technology, add a story, or adjust scope mid-sprint, open a **sprint change proposal** before implementing. This keeps story specs and implementations aligned.

See `_bmad-output/implementation-artifacts/` for examples (e.g., `sprint-change-proposal-2026-03-22.md`).

### Adding a new external provider

Before committing to any external provider in architecture or story specs, validate it against real target content. A quick manual spike is enough — don't skip this step.

### Bruno developer collection

A Bruno collection for interactive API testing lives in `docs/bruno/`. Open the `docs/bruno/` folder in [Bruno](https://www.usebruno.com/) and select the `local` environment to get started.
