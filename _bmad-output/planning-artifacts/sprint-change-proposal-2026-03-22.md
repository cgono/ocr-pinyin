# Sprint Change Proposal — 2026-03-22

**Type:** Technical limitation — OCR provider replacement
**Status:** Approved
**Triggered by:** Story 1.4 post-implementation finding — AWS Textract does not support Chinese script

---

## 1. Issue Summary

### 1.1 Problem Statement

AWS Textract's `DetectDocumentText` API does not support Chinese (Simplified or Traditional) script. Stories 1.1–1.5 of Epic 1 are marked done and the adapter infrastructure is correctly implemented, but the core product requirement — extracting Chinese text from a children's book photo — cannot be met with the current provider.

### 1.2 Discovery Context

Discovered during integration testing after Epic 1 completion. The 2026-03-18 sprint change proposal confirmed AWS credentials and Textract permissions were valid. The blocker is the service itself: Textract simply does not process CJK characters.

### 1.3 Evidence

- AWS Textract language support matrix excludes Chinese from `DetectDocumentText`
- Prior credentials debugging (2026-03-18) confirmed `arn:aws:iam::135263544996:user/ReadingAssistantDevUser` has valid Textract permissions — the service, not the credentials, is the limitation
- Google Cloud Vision `DOCUMENT_TEXT_DETECTION` explicitly supports Simplified and Traditional Chinese and returns per-character confidence scores
- The existing `OcrProvider` protocol in `backend/app/adapters/ocr_provider.py` is provider-agnostic; no upstream code changes are required

---

## 2. Impact Analysis

| Area | Impact | Detail |
|---|---|---|
| Stories 1.1–1.3, 1.5–1.6 | ✅ None | Unaffected |
| Story 1.4 | ⚠️ Provider replaced | Adapter infrastructure stays; Textract impl superseded by GCV |
| Epic 1 | ⚠️ Story 1.7 added | Additive only — no stories removed or reverted |
| Epics 2–5 | ✅ None | All remain backlog; Epic 2 quality work becomes more valuable once Chinese text is live |
| PRD | ✅ None | Provider-agnostic; MVP scope unchanged |
| Architecture doc | ⚠️ Update needed | Record GCV as chosen OCR provider and reason Textract was not used |
| UX spec | ✅ None | Provider-agnostic |
| `ocr_provider.py` | ⚠️ Action needed | Add `google_vision` branch to `get_ocr_provider()` |
| `textract_ocr_provider.py` | ✅ Kept as legacy | File retained; Textract path still accessible via `OCR_PROVIDER=textract` |
| `pyproject.toml` | ⚠️ Action needed | Remove `boto3`/`botocore`; add `google-cloud-vision>=3.7` |
| `backend/.env.example` | ⚠️ Action needed | Replace AWS vars with GCV credential vars |
| `docker-compose.yml` | ⚠️ Action needed | Remove credentials file volume mount; rely on embedded JSON env var |
| `epics.md` | ⚠️ Action needed | Add Story 1.7 |
| `sprint-status.yaml` | ⚠️ Action needed | Add Story 1.7 entry under Epic 1 |

---

## 3. Recommended Approach

**Option 1: Direct Adjustment** — Add Story 1.7 to Epic 1.

**Rationale:**
- The `OcrProvider` protocol adapter boundary exists precisely for this scenario — a new provider slots in with zero changes to `ocr_service.py`, `process_service.py`, or any route handler
- No completed work needs to be reverted; all Epic 1 infrastructure is valid and reusable
- Google Cloud Vision's response shape (per-block text + confidence) maps cleanly to `RawOcrSegment` following the same LangChain extraction chain pattern already established in the Textract provider
- Effort: **Low** — one focused implementation session
- Risk: **Low** — no runtime behaviour changes to existing code paths; Textract path preserved as fallback

**Effort:** Low
**Risk:** Low
**Timeline impact:** None to Epics 2–5; Epic 1 closes after Story 1.7

---

## 4. Detailed Change Proposals

### 4.1 New Story 1.7 — `epics.md`

```
### Story 1.7: Swap OCR Provider to Google Cloud Vision

As Clint,
I want the OCR backend to use Google Cloud Vision instead of AWS Textract,
So that Chinese text is actually extracted from book pages (Textract does not
support Chinese script).

**Acceptance Criteria:**

**Given** a valid uploaded image containing Chinese text
**When** POST /v1/process is called with OCR_PROVIDER=google_vision
**Then** Chinese characters are extracted and returned in data.ocr.segments[]
**And** status is success or partial (not error due to provider failure)

**Given** OCR_PROVIDER is unset
**When** the service starts
**Then** the existing NoOpOcrProvider fallback behavior is unchanged

**Given** all existing backend tests run
**When** the new provider is wired in
**Then** all tests continue to pass
```

---

### 4.2 Architecture doc update — `architecture.md`

```
Section: External Integrations

OLD:
- OCR provider via `ocr_provider.py`.

NEW:
- OCR provider via `ocr_provider.py` (Google Cloud Vision —
  DOCUMENT_TEXT_DETECTION; supports Simplified and Traditional Chinese).

Section: Core Architectural Decisions > Technology Stack (addendum)

ADD:
OCR Provider: Google Cloud Vision (DOCUMENT_TEXT_DETECTION) selected over
AWS Textract; Textract does not support Chinese script. GCV plugs directly
into the OcrProvider protocol adapter with no upstream code changes.
```

---

### 4.3 `ocr_provider.py` — factory function update

```python
OLD:
def get_ocr_provider() -> OcrProvider:
    """...
    Supported values:
      textract  – AWS Textract via LangChain extraction chain (production)
      (unset)   – NoOpOcrProvider (raises ProviderUnavailableError on use)
    """
    provider = os.environ.get("OCR_PROVIDER", "").lower()
    if provider == "textract":
        from app.adapters.textract_ocr_provider import TextractOcrProvider
        return TextractOcrProvider()
    return NoOpOcrProvider()

NEW:
def get_ocr_provider() -> OcrProvider:
    """...
    Supported values:
      google_vision  – Google Cloud Vision DOCUMENT_TEXT_DETECTION (production)
      textract       – AWS Textract (legacy; does not support Chinese script)
      (unset)        – NoOpOcrProvider (raises ProviderUnavailableError on use)
    """
    provider = os.environ.get("OCR_PROVIDER", "").lower()
    if provider == "google_vision":
        from app.adapters.google_cloud_vision_ocr_provider import GoogleCloudVisionOcrProvider
        return GoogleCloudVisionOcrProvider()
    if provider == "textract":
        from app.adapters.textract_ocr_provider import TextractOcrProvider
        return TextractOcrProvider()
    return NoOpOcrProvider()
```

---

### 4.4 Environment variable changes

```
backend/.env.example

OLD:
OCR_PROVIDER=textract
AWS_REGION=ap-southeast-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key

NEW:
OCR_PROVIDER=google_vision
GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type":"service_account","project_id":"your-project-id","private_key_id":"private_key_id","private_key":"private_key","client_email":"service-account@your-project-id.iam.gserviceaccount.com","client_id":"client_id","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/service-account%40your-project-id.iam.gserviceaccount.com","universe_domain":"googleapis.com"}'
# Optional — only needed if not encoded in the embedded credentials JSON:
# GOOGLE_CLOUD_PROJECT=your-project-id
```

```yaml
docker-compose.yml backend service

NO CHANGE REQUIRED:
The backend reads `GOOGLE_APPLICATION_CREDENTIALS_JSON` directly from `env_file`,
so no credentials file volume mount is needed.
```

---

### 4.5 `pyproject.toml` dependency change

```
OLD:
boto3>=1.34
botocore>=1.34

NEW:
google-cloud-vision>=3.7
```

---

## 5. Implementation Handoff

**Scope classification:** Minor — direct implementation by development team.

| Deliverable | Owner | Action |
|---|---|---|
| `google_cloud_vision_ocr_provider.py` | Dev | New file; implement `OcrProvider` protocol using `DOCUMENT_TEXT_DETECTION` via LangChain chain pattern matching `textract_ocr_provider.py` |
| `ocr_provider.py` | Dev | Apply Proposal 4.3 |
| `pyproject.toml` | Dev | Apply Proposal 4.5 |
| `backend/.env.example` | Dev | Apply Proposal 4.4 |
| `docker-compose.yml` | Dev | Remove obsolete credentials file volume mount; keep env-file-only setup |
| `epics.md` | SM/Dev | Add Story 1.7 per Proposal 4.1 |
| `architecture.md` | SM/Dev | Apply Proposal 4.2 |
| `sprint-status.yaml` | SM/Dev | Add `1-7-swap-ocr-provider-to-google-cloud-vision: ready-for-dev` under Epic 1 |

**Success criteria:**
- `POST /v1/process` with a real Chinese book page photo returns `status: success` and populated `data.ocr.segments[]` containing Chinese characters
- `OCR_PROVIDER=google_vision` configured in `backend/.env` with `GOOGLE_APPLICATION_CREDENTIALS_JSON` set to embedded service-account JSON
- All existing backend tests pass (`pytest backend/`)
- `OCR_PROVIDER` unset still falls through to `NoOpOcrProvider`

---

*Generated by: Correct Course workflow — 2026-03-22*
