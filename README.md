# OCR Pinyin

A mobile-first web app for reading Chinese books. Upload a photo of a page, get Hanyu Pinyin back — aligned to the source text — so you can keep reading without interruption.

Built for iPhone Safari. No account required.

## How it works

1. Capture or upload a photo of a Chinese book page
2. The backend validates the image and runs OCR via Google Cloud Vision
3. Chinese text is extracted and converted to Hanyu Pinyin (tone marks)
4. The result view shows the uploaded image alongside the pinyin output

## Stack

- **Backend:** Python / FastAPI, Google Cloud Vision (OCR), `pypinyin`
- **Frontend:** React / Vite, TanStack Query
- **API:** Versioned REST under `/v1`, structured JSON envelope (`success | partial | error`)
- **Infra:** Docker Compose for local parity

## Quick start

```bash
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

See [CONTRIBUTING.md](CONTRIBUTING.md) for manual setup and developer tooling.

## API

`POST /v1/process` — upload an image, receive pinyin

```
GET  /openapi.json   — OpenAPI 3.x spec (auto-updated)
GET  /docs           — Swagger UI
```

A Bruno developer collection is available in `docs/bruno/` for interactive testing.

## Project status

| Epic | Focus | Status |
|------|-------|--------|
| 1 | Foundation — capture to pinyin vertical slice | Done |
| 2 | OCR quality, mixed-language handling, partial results | In progress |
| 3 | Diagnostics, observability, health/metrics endpoints | Backlog |
| 4 | Cost guardrails and safe usage controls | Backlog |
| 5 | History, reuse, and future evolution | Backlog |
