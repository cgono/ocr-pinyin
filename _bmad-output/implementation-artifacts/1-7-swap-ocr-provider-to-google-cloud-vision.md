# Story 1.7: Swap OCR Provider to Google Cloud Vision

Status: done

## Story

As Clint,
I want the OCR backend to use Google Cloud Vision instead of AWS Textract,
So that Chinese text is actually extracted from book pages (Textract does not support Chinese script).

## Acceptance Criteria

1. Given a valid uploaded image containing Chinese text, when POST /v1/process is called with OCR_PROVIDER=google_vision, then Chinese characters are extracted and returned in `data.ocr.segments[]` and status is `success` or `partial` (not error due to provider failure).
2. Given OCR_PROVIDER is unset, when the service starts, then the existing NoOpOcrProvider fallback behavior is unchanged.
3. Given all existing backend tests run, when the new provider is wired in, then all tests continue to pass.

## Tasks / Subtasks

- [x] Create `backend/app/adapters/google_cloud_vision_ocr_provider.py` (AC: 1)
  - [x] Implement `GoogleCloudVisionOcrProvider` class following the `OcrProvider` protocol
  - [x] Use `vision.ImageAnnotatorClient()` with `DOCUMENT_TEXT_DETECTION`
  - [x] Build a LangChain chain: `_gcv_response_to_documents | _documents_to_segments` matching the Textract pattern
  - [x] Iterate `full_text_annotation.pages[].blocks[].paragraphs[]` — paragraph granularity enables Story 2.1 language filtering
  - [x] For each paragraph: extract text by joining symbols (no separator for Chinese), set `language` from `detected_languages[0].language_code` (or `None`), set `confidence` from `paragraph.confidence`
  - [x] Skip non-TEXT blocks (`block.block_type != vision.Block.BlockType.TEXT`)
  - [x] Handle `google.api_core.exceptions.GoogleAPIError` → `OcrExecutionError`; handle missing credentials → `ProviderUnavailableError`
  - [x] Add debug logging matching the Textract pattern (paragraph count, first 40 chars)
- [x] Update `backend/app/adapters/ocr_provider.py` factory (AC: 1, 2)
  - [x] Apply the `get_ocr_provider()` change from sprint-change-proposal-2026-03-22.md §4.3
  - [x] Add `google_vision` branch that imports and returns `GoogleCloudVisionOcrProvider`
  - [x] Keep `textract` branch intact (legacy, will fail at import if boto3 removed)
  - [x] Update docstring to list `google_vision` as production, `textract` as legacy
- [x] Update `backend/pyproject.toml` (AC: 1, 3)
  - [x] Replace `boto3==1.37.26` with `google-cloud-vision>=3.7,<4.0`
  - [x] Keep `langchain-core` — still used for `RunnableLambda` chain pattern
  - [x] Run `uv sync --dev` from `backend/` to regenerate `uv.lock`
- [x] Update `backend/.env.example` (AC: 1)
  - [x] Apply change from sprint-change-proposal-2026-03-22.md §4.4
  - [x] Replace AWS vars with `OCR_PROVIDER=google_vision` and `GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type":"service_account",...}'`
- [x] Update `docker-compose.yml` (AC: 1)
  - [x] Remove the obsolete credentials file volume mount; embedded JSON credentials are supplied via `env_file`
- [x] Run full test suite and verify all tests pass (AC: 3)
  - [x] `cd backend && uv run pytest` — all 59 existing tests must remain green
  - [x] `uv run ruff check .` — zero lint issues

## Dev Notes

### Story Foundation

- Source: Epic 1, Story 1.7 in `_bmad-output/planning-artifacts/epics.md`; added via approved sprint-change-proposal-2026-03-22.md
- Root cause: AWS Textract `DetectDocumentText` does not support Chinese script. Confirmed during integration testing post-Epic 1. GCV `DOCUMENT_TEXT_DETECTION` explicitly supports Simplified (`zh-Hans`) and Traditional (`zh-Hant`) Chinese with per-character confidence scores.
- Scope: New adapter file + factory update + dependency swap + env/infra updates. Zero changes to `ocr_service.py`, route handlers, schemas, or any test file. The `OcrProvider` protocol boundary was designed for exactly this swap.

### Architecture Compliance

- The `OcrProvider` protocol in `backend/app/adapters/ocr_provider.py` defines the exact interface: `extract(*, image_bytes: bytes, content_type: str) -> list[RawOcrSegment]`. New provider must satisfy this protocol; no other changes required.
- Architecture doc explicitly states: "OCR provider via `ocr_provider.py` (Google Cloud Vision — DOCUMENT_TEXT_DETECTION; supports Simplified and Traditional Chinese)."
- Architecture layering rule: provider implementation details stay in `adapters/`; `ocr_service.py` (services layer) must NOT change.
- Backend project structure: `backend/app/adapters/google_cloud_vision_ocr_provider.py` (matches `textract_ocr_provider.py` placement).

### Technical Requirements

**`google-cloud-vision` API specifics:**
- Client: `vision.ImageAnnotatorClient(credentials=...)` when `GOOGLE_APPLICATION_CREDENTIALS_JSON` is set; otherwise falls back to Application Default Credentials
- Call: `client.document_text_detection(image=vision.Image(content=image_bytes))`
- Response structure: `response.full_text_annotation` → pages → blocks → paragraphs → words → symbols
- Paragraph-level granularity is preferred over block-level because: paragraphs are smaller/more language-homogeneous, enabling Story 2.1's language filtering to operate at finer resolution
- Language: `paragraph.property.detected_languages[0].language_code` → e.g., `"zh-Hans"`, `"zh-Hant"`, `"en"`. **This is the critical difference from Textract** — GCV returns actual language codes that the OCR service's `_is_usable_chinese_segment()` uses for `zh` prefix matching.
- Confidence: `paragraph.confidence` — already in `0.0-1.0` range (no normalization needed, but `_normalize_confidence()` in ocr_service.py handles it anyway)

**Implementation pattern (follow textract_ocr_provider.py exactly):**

```python
"""Google Cloud Vision OCR provider.

LangChain is used for the extraction chain that transforms the raw GCV API
response (full_text_annotation) into normalised RawOcrSegment values.  The
chain is composed of two RunnableLambda steps:

  1. _gcv_response_to_documents – iterates TEXT blocks at paragraph granularity,
     extracts text by joining symbols, and wraps each paragraph in a LangChain
     Document carrying confidence and language metadata.
  2. _documents_to_segments – maps LangChain Documents to the adapter's
     RawOcrSegment dataclass.

Environment variables
---------------------
OCR_PROVIDER=google_vision        Activates this provider.
GOOGLE_APPLICATION_CREDENTIALS_JSON    GCP service account JSON embedded as a string value.
GOOGLE_CLOUD_PROJECT                   Optional; only needed if not encoded in the credentials.
"""
```

**Text extraction from a GCV paragraph:**
```python
def _paragraph_text(paragraph) -> str:
    return "".join(
        "".join(symbol.text for symbol in word.symbols)
        for word in paragraph.words
    )
```
- Do NOT add spaces between words — Chinese characters flow without separators; this matches natural sentence structure.

**Chain steps:**
```python
def _gcv_response_to_documents(response) -> list[Document]:
    docs = []
    for page in (response.full_text_annotation.pages or []):
        for block in page.blocks:
            if block.block_type != vision.Block.BlockType.TEXT:
                continue
            for paragraph in block.paragraphs:
                text = _paragraph_text(paragraph)
                if not text.strip():
                    continue
                langs = list(paragraph.property.detected_languages)
                language = langs[0].language_code if langs else None
                docs.append(Document(
                    page_content=text,
                    metadata={"confidence": paragraph.confidence, "language": language},
                ))
    return docs

def _documents_to_segments(docs: list[Document]) -> list[RawOcrSegment]:
    return [
        RawOcrSegment(
            text=doc.page_content,
            language=doc.metadata.get("language"),
            confidence=doc.metadata["confidence"],
        )
        for doc in docs
    ]
```

**`GoogleCloudVisionOcrProvider` class:**
```python
class GoogleCloudVisionOcrProvider:
    def __init__(self) -> None:
        try:
            creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
            if creds_json:
                info = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                self._client = vision.ImageAnnotatorClient(credentials=credentials)
            else:
                self._client = vision.ImageAnnotatorClient()
        except Exception as exc:
            raise ProviderUnavailableError(
                "Could not initialise Google Cloud Vision client. "
                "Check GOOGLE_APPLICATION_CREDENTIALS_JSON."
            ) from exc

    def extract(self, *, image_bytes: bytes, content_type: str) -> list[RawOcrSegment]:
        try:
            response = self._client.document_text_detection(
                image=vision.Image(content=image_bytes)
            )
        except google.api_core.exceptions.GoogleAPIError as exc:
            raise OcrExecutionError(f"GCV API error: {exc}") from exc
        except Exception as exc:
            raise OcrExecutionError(f"Unexpected GCV error: {exc}") from exc

        paragraphs = sum(
            len(block.paragraphs)
            for page in (response.full_text_annotation.pages or [])
            for block in page.blocks
        )
        logger.debug("GCV returned %d paragraph(s)", paragraphs)
        return _extraction_chain.invoke(response)
```

**Imports needed:**
```python
import json
import google.api_core.exceptions
from google.cloud import vision
from google.oauth2 import service_account
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from app.adapters.ocr_provider import OcrExecutionError, ProviderUnavailableError, RawOcrSegment
```

### Dependency Change Details

**pyproject.toml:**
- Remove: `"boto3==1.37.26"`
- Add: `"google-cloud-vision>=3.7,<4.0"`
- Keep: `"langchain-core==0.3.61"` — used for `RunnableLambda`
- After editing: run `uv sync --dev` from `backend/` to regenerate `uv.lock`

**Note on boto3 removal and textract_ocr_provider.py:** Removing boto3 means `textract_ocr_provider.py` will throw `ImportError` if `OCR_PROVIDER=textract` is used. This is acceptable — Textract cannot process Chinese anyway. The file is retained as documentation/legacy reference. Add a comment to the top of `textract_ocr_provider.py`: `# LEGACY: Requires boto3. Does not support Chinese script. Use google_vision instead.`

### File Structure Requirements

**New file:**
- `backend/app/adapters/google_cloud_vision_ocr_provider.py`

**Modified files:**
- `backend/app/adapters/ocr_provider.py` — factory update (see §4.3 of sprint-change-proposal-2026-03-22.md)
- `backend/pyproject.toml` — dependency swap
- `backend/uv.lock` — regenerated by `uv sync`
- `backend/.env.example` — AWS vars → GCV vars
- `docker-compose.yml` — remove obsolete credentials file volume mount
- `backend/app/adapters/textract_ocr_provider.py` — add legacy comment at top

**Files NOT to touch:**
- `backend/app/services/ocr_service.py` — no changes needed; `_is_usable_chinese_segment()` already handles `zh` prefix language codes
- `backend/app/api/v1/process.py` — no changes needed
- `backend/app/schemas/process.py` — no changes needed
- Any test files — must remain green; do not modify

### Environment Variable Changes

**`backend/.env.example` (replace AWS vars):**
```
APP_NAME=ocr-pinyin-api
APP_ENV=development
OCR_PROVIDER=google_vision
GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type":"service_account","project_id":"your-project-id","private_key_id":"private_key_id","private_key":"private_key","client_email":"service-account@your-project-id.iam.gserviceaccount.com","client_id":"client_id","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/service-account%40your-project-id.iam.gserviceaccount.com","universe_domain":"googleapis.com"}'
# Optional — only needed if not encoded in the embedded credentials JSON:
# GOOGLE_CLOUD_PROJECT=your-project-id
```

**Developer local setup (not committed):**
1. Download a GCP service account key JSON from the Google Cloud Console (project with Vision API enabled)
2. Minify or otherwise serialize that JSON into a single-line string value
3. Set `GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type":"service_account",...}'` in `backend/.env`
4. The provider loads this env var, builds `service_account.Credentials`, and passes them to `ImageAnnotatorClient`

### docker-compose.yml Update

No credentials volume mount is required under the `backend` service:
```yaml
volumes:
  - ./backend:/app
```
The backend reads `GOOGLE_APPLICATION_CREDENTIALS_JSON` from `env_file`, so the same embedded credential value is available inside and outside Docker without mounting a host file.

### Testing Requirements

**No new test files are required.** The existing 59 tests already cover:
- `ocr_service.py` via `backend/tests/unit/services/test_ocr_service.py` (uses mock provider)
- Route integration via `backend/tests/integration/api_v1/test_process_route.py` (uses `StubOcrProvider`)
- Contract tests via `backend/tests/contract/response_envelopes/test_process_envelopes.py`
- `ocr_provider.py` NoOp path is exercised by existing tests

**The new provider is NOT exercised by automated tests** — integration with a live GCV endpoint requires real credentials and is verified manually via `POST /v1/process` with a Chinese book photo.

**Verification checklist (manual):**
1. `uv run pytest` → all 59 tests pass
2. `uv run ruff check .` → zero issues
3. Start backend with `OCR_PROVIDER=google_vision` and `GOOGLE_APPLICATION_CREDENTIALS_JSON='{"type":"service_account",...}'`
4. POST a Chinese book page image to `POST /v1/process`
5. Verify `status: "success"` and `data.ocr.segments[]` contains Chinese characters
6. Verify segments have `language` values starting with `"zh"` (not `"und"`)

### Previous Story Intelligence

From Stories 1.4–1.6 patterns:
- Keep `GoogleCloudVisionOcrProvider` thin — no business logic; raw API call + chain only
- Match the module docstring structure from `textract_ocr_provider.py` exactly
- Use `logger.debug` (not `logger.info`) for response detail logs — same as Textract
- The `run_in_executor` pattern for blocking I/O is already handled in `ocr_service.py` (line 33) — the provider `extract()` method is called inside the executor, so the GCV client call (which is synchronous) is safe
- `_extraction_chain` must be module-level (same as Textract) — not instantiated per-call

### Git Intelligence Summary

- Commit `1421507`: "feat: correct course — swap OCR provider from Textract to Google Cloud Vision" — updated `architecture.md`, `epics.md`, `sprint-status.yaml`, added `sprint-change-proposal-2026-03-22.md`. No code was changed — this story implements the code changes.
- Commit `a645403`: "feat: new story 1-6, fix backend, bruno, debug settings" — 59 tests passing baseline

### Project Context Reference

No `project-context.md` in repository. Primary context sources:
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-22.md` — authoritative spec for this story
- `_bmad-output/planning-artifacts/architecture.md` — GCV as chosen provider, OcrProvider protocol boundary
- `backend/app/adapters/textract_ocr_provider.py` — exact pattern to follow for new provider
- `backend/app/adapters/ocr_provider.py` — protocol definition + factory to update
- `backend/app/services/ocr_service.py` — upstream consumer; must NOT be modified

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-22.md]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.7]
- [Source: _bmad-output/planning-artifacts/architecture.md#External-Integrations]
- [Source: backend/app/adapters/textract_ocr_provider.py — pattern reference]
- [Source: backend/app/adapters/ocr_provider.py — protocol and factory]
- [Source: backend/app/services/ocr_service.py — upstream consumer]
- [GCV Python client: https://cloud.google.com/python/docs/reference/vision/latest]
- [GCV DOCUMENT_TEXT_DETECTION: https://cloud.google.com/vision/docs/handwriting]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None_

### Completion Notes List

- Created `GoogleCloudVisionOcrProvider` in `backend/app/adapters/google_cloud_vision_ocr_provider.py` following the exact Textract pattern: module-level `_extraction_chain`, two `RunnableLambda` steps, paragraph-granularity extraction, language code from `detected_languages[0].language_code`, no word separators for Chinese.
- Updated `get_ocr_provider()` factory to add `google_vision` branch (checked first) and updated docstring; `textract` branch retained as legacy.
- Swapped `boto3==1.37.26` out of production dependencies; added `google-cloud-vision>=3.7,<4.0` as production dep. boto3 moved to dev dependencies to keep the existing textract test suite green (test file imports botocore directly — cannot modify test files per story constraints).
- Pre-existing E402 lint issue in `textract_ocr_provider.py` (logger placed before boto3 imports) fixed by moving logger assignment after all imports. All 59 tests pass; `ruff check .` — zero issues.

### File List

- `backend/app/adapters/google_cloud_vision_ocr_provider.py` (new)
- `backend/app/adapters/ocr_provider.py` (modified — factory updated)
- `backend/app/adapters/textract_ocr_provider.py` (modified — legacy comment added, pre-existing lint fixed)
- `backend/pyproject.toml` (modified — dependency swap)
- `backend/uv.lock` (regenerated by `uv sync --dev`)
- `backend/.env.example` (modified — AWS vars replaced with GCV vars)
- `docker-compose.yml` (modified — credentials volume mount added)

## Change Log

- 2026-03-22: Story created — OCR provider swap from Textract to Google Cloud Vision, triggered by sprint-change-proposal-2026-03-22.md
- 2026-03-22: Implementation complete — GoogleCloudVisionOcrProvider created, factory updated, deps swapped, env/infra updated; all 59 tests green, zero lint issues
- 2026-03-22: Amended — credentials loading changed from file-path (`GOOGLE_APPLICATION_CREDENTIALS`) to embedded JSON (`GOOGLE_APPLICATION_CREDENTIALS_JSON`); docker-compose credentials volume mount removed; all 59 tests green, zero lint issues
- 2026-03-22: Reviewed complete — embedded credential docs aligned, provider now tolerates quoted env-file JSON values, and story status moved to done
