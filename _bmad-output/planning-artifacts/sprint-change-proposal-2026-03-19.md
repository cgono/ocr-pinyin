# Sprint Change Proposal — 2026-03-19

**Type:** Enhancement — new story added to Epic 1  
**Status:** Approved  
**Triggered by:** Post-Epic 1 developer experience review — OpenAPI/Swagger spec and Bruno testing tooling

---

## 1. Issue Summary

### 1.1 Problem Statement
The backend architecture explicitly planned for *"FastAPI OpenAPI + Swagger UI/ReDoc defaults"* (architecture.md), but no implementation story was ever created. Additionally, the `POST /v1/process` endpoint uses a raw `Request` object for body streaming, which FastAPI cannot auto-introspect — so the generated OpenAPI spec shows no request body schema. This makes the `/docs` Swagger UI non-functional for interactive testing and prevents Bruno from importing a useful API collection.

Three concrete gaps:

1. **Request body invisible in spec** — `openapi_extra` is needed to manually inject the binary image content-types.
2. **CORS blocks `GET /openapi.json`** — `allow_methods=["POST", "OPTIONS"]` prevents Swagger UI and Bruno (when accessing from the frontend dev server origin) from fetching the spec.
3. **No Bruno collection in repo** — Clint wants Bruno to auto-import from `http://localhost:8000/openapi.json` with a pre-wired collection for immediate use.

### 1.2 Discovery Context
Identified proactively after Epic 1 completion during tooling review. No code regression — purely additive change.

### 1.3 Evidence
- `architecture.md` line 159: `"API docs: FastAPI OpenAPI + Swagger UI/ReDoc defaults"` — planned but not implemented.
- `process.py` route: `async def process_image(request: Request)` — raw `Request` type; FastAPI cannot infer body shape.
- `main.py` CORS: `allow_methods=["POST", "OPTIONS"]` — `GET` not permitted cross-origin; blocks spec fetching.
- No Bruno collection or dev-tooling documentation exists in the repo.

---

## 2. Impact Analysis

| Area | Impact | Detail |
|---|---|---|
| Epic 1 stories 1.1–1.5 | ✅ None — all remain done | Additive change only |
| Epic 2 stories | ✅ None | No dependency |
| Epics 3–5 | ✅ None | No dependency |
| PRD | ✅ Strengthened | NFR8 (versioned API backward compat) reinforced |
| Architecture | ⚠️ Minor addendum | Bruno noted as dev-time API client tool |
| UX spec | ✅ None | Backend-only change |
| CI pipeline | ✅ None | Existing tests unaffected |
| `main.py` | ⚠️ Action needed | OpenAPI metadata + CORS `GET` added |
| `process.py` | ⚠️ Action needed | `openapi_extra` for binary body schema |
| `docs/bruno/` | ⚠️ Action needed | New Bruno collection files |
| `epics.md` | ⚠️ Action needed | Story 1.6 added |
| `sprint-status.yaml` | ⚠️ Action needed | Story 1.6 entry added |

---

## 3. Recommended Approach

**Option 1: Direct Adjustment** — Add Story 1.6 to Epic 1.

**Rationale:**
- No completed work is broken or reversed.
- The change is entirely additive: two small code edits and two new files.
- Effort is Low; Risk is Low.
- Aligns exactly with what was already planned in the architecture document.
- No resequencing, no scope reduction, no epic restructuring needed.

**Effort:** Low (estimated single dev session)  
**Risk:** Low — no runtime behaviour changes; only metadata/tooling additions  
**Timeline impact:** None to Epics 2–5

---

## 4. Detailed Change Proposals

### 4.1 `backend/app/main.py` — OpenAPI metadata + CORS GET fix

```
OLD:
app = FastAPI(title="OCR Pinyin API", version="0.1.0")
...
    allow_methods=["POST", "OPTIONS"],

NEW:
app = FastAPI(
    title="OCR Pinyin API",
    version="0.1.0",
    description="Processes uploaded images to extract Chinese text and generate Hanyu Pinyin.",
    openapi_tags=[{"name": "process", "description": "Image OCR and Pinyin generation"}],
)
...
    allow_methods=["GET", "POST", "OPTIONS"],
```

**Rationale:** Swagger UI and Bruno both issue `GET /openapi.json`. The prior CORS config silently blocked cross-origin GET (e.g., from Vite dev server on port 5173). Metadata improves Swagger UI and Bruno collection readability.

---

### 4.2 `backend/app/api/v1/process.py` — Document binary request body in OpenAPI spec

```
OLD:
@router.post('/process', response_model=ProcessResponse, response_model_exclude_none=True)

NEW:
@router.post(
    '/process',
    response_model=ProcessResponse,
    response_model_exclude_none=True,
    tags=["process"],
    summary="Process an image for Chinese OCR and Pinyin",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
                "image/png":  {"schema": {"type": "string", "format": "binary"}},
                "image/webp": {"schema": {"type": "string", "format": "binary"}},
            },
        }
    },
)
```

**Rationale:** FastAPI cannot auto-introspect a raw `Request` parameter. The `openapi_extra` field injects the correct binary body schema without changing runtime behaviour.

---

### 4.3 New `docs/bruno/` — Bruno developer collection

New files:
- `docs/bruno/bruno.json` — collection metadata pointing to `http://localhost:8000/openapi.json`
- `docs/bruno/Process Image.bru` — pre-configured request for `POST /v1/process`

**Rationale:** Bruno can import from the live OpenAPI URL so the collection auto-updates when endpoints change. The collection file gives Clint a ready-to-use request without manual setup.

---

### 4.4 `_bmad-output/planning-artifacts/epics.md` — Add Story 1.6

```
### Story 1.6: Expose OpenAPI Spec and Add Bruno Developer Collection

As Clint,
I want the backend API spec automatically available at /openapi.json and a Bruno
collection pre-configured in the repo,
So that I can test endpoints interactively and have the API contract update
automatically as new endpoints are added.

Acceptance Criteria:
- GET /openapi.json returns a valid OpenAPI 3.x schema listing all /v1 endpoints
- Swagger UI is accessible at GET /docs with POST /v1/process fully documented
  (including binary request body content-types)
- A Bruno collection in docs/bruno/ imports cleanly from
  http://localhost:8000/openapi.json
- CORS allows GET from localhost dev origins so Swagger UI can fetch the spec
- All existing tests continue to pass
```

---

## 5. Implementation Handoff

**Scope classification:** Minor — direct implementation by development team.

| Deliverable | Owner | Action |
|---|---|---|
| `main.py` code change | Dev | Apply Proposal 4.1 |
| `process.py` code change | Dev | Apply Proposal 4.2 |
| Bruno collection files | Dev | Create `docs/bruno/` per Proposal 4.3 |
| `epics.md` update | SM/Dev | Add Story 1.6 per Proposal 4.4 |
| `sprint-status.yaml` update | SM/Dev | Add story 1.6 entry under Epic 1 |

**Success criteria:**
- `curl http://localhost:8000/openapi.json` returns a valid OpenAPI 3.x JSON document
- Swagger UI at `http://localhost:8000/docs` shows `POST /v1/process` with binary body content-types
- Bruno opens `docs/bruno/` collection and can send a live test request with a JPEG file
- All existing backend tests pass (`pytest backend/`)

---

*Generated by: Correct Course workflow — 2026-03-19*
