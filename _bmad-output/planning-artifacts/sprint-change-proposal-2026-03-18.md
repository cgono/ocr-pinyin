# Sprint Change Proposal — 2026-03-18

**Type:** Defect (Configuration) — no epic or story changes required  
**Status:** Resolved — fixes applied directly  
**Triggered by:** Post-Epic 1 integration testing of `/v1/process` with live AWS Textract

---

## 1. Change Trigger & Context

### 1.1 Triggering Story
All Epic 1 stories (1-1 through 1-5) are marked **done**, but end-to-end testing with a real image revealed that the endpoint always returns `ocr_provider_unavailable` instead of performing OCR.

### 1.2 Core Problem
**Configuration defect**: `docker-compose.yml` had no `env_file` directive for the backend service, so the `backend/.env` file (containing `OCR_PROVIDER`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) was never loaded into the container. The backend therefore saw `OCR_PROVIDER` as unset and fell back to `NoOpOcrProvider`, which is hardcoded to raise `ProviderUnavailableError` immediately.

A secondary defect was also present: `AWS_REGION=ap-southeast-1   # or your chosen supported region` — an inline comment left over from the `.env.example` template. Docker Compose's `env_file` parser does **not** strip inline comments, so the region value would have been `ap-southeast-1   # or your chosen supported region`, causing Textract client initialisation to fail even once `env_file` was added.

Additionally, unhandled exceptions in the OCR service were silently swallowed — only the mapped error code was visible in API responses, making root cause identification difficult.

### 1.3 Evidence
```json
{
    "status": "error",
    "request_id": "66bf9be1-7db2-43f1-8f06-f72ea7eb4a64",
    "error": {
        "category": "ocr",
        "code": "ocr_provider_unavailable",
        "message": "Text extraction is temporarily unavailable. Please try again."
    }
}
```
AWS credential verification: `<redacted IAM user ARN>` — credentials **valid**, Textract permission **confirmed** (`UnsupportedDocumentException` returned on dummy payload, not `AccessDeniedException`).

---

## 2. Impact Assessment

| Area | Impact |
|---|---|
| Epic 1 stories | No changes — all stories remain done |
| Epic 2+ stories | No changes needed |
| PRD / Architecture / UX | No changes needed |
| Deployment configuration | Fixed (see changes below) |

---

## 3. Changes Applied

### 3.1 `docker-compose.yml` — Add `env_file` for backend service
```yaml
# BEFORE
    environment:
      APP_NAME: ocr-pinyin-api
      APP_ENV: development

# AFTER
    env_file:
      - ./backend/.env
```

**Rationale:** The `.env` file must be loaded into the container so `OCR_PROVIDER=textract` and the AWS credentials are available at runtime.

### 3.2 `backend/.env` and `backend/.env.example` — Remove inline comment from `AWS_REGION`
```
# BEFORE
AWS_REGION=ap-southeast-1   # or your chosen supported region

# AFTER
AWS_REGION=ap-southeast-1
```

**Rationale:** Docker Compose `env_file` parsing does not strip inline `#` comments — the comment would have been included as part of the region string value, causing Textract to reject the request.

### 3.3 `backend/app/main.py` — Add basic logging configuration
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
)
```

**Rationale:** Without a logging configuration, Python defaults to WARNING level and no formatter, making it impossible to see INFO-level diagnostics from the application.

### 3.4 `backend/app/services/ocr_service.py` — Log stack traces on OCR failures
```python
# Added to both except clauses:
logger.exception("OCR provider unavailable: %s", exc)
logger.exception("OCR execution error: %s", exc)
```

**Rationale:** Before this change, all exception detail (including the root cause from boto3/botocore) was silently discarded when the exception was mapped to an `OcrServiceError`. The `logger.exception()` call logs the full chained traceback so the actual error is visible in container logs.

---

## 4. Checklist Status

| # | Item | Status |
|---|---|---|
| 1.1 | Identify triggering story | [x] Done |
| 1.2 | Define core problem | [x] Done — config defect, not design or requirement issue |
| 1.3 | Gather evidence | [x] Done — error response + credential verification |
| 2.1 | Evaluate current epic | [x] Done — Epic 1 stories unaffected |
| 2.2 | Determine epic-level changes | [N/A] No epic changes required |
| 3.x | PRD / Architecture / UX impacts | [N/A] No planning artifact changes needed |

---

## 5. Verification Steps

After restarting the Docker stack (`docker-compose down && docker-compose up`):

1. Submit a valid image with Chinese text — expect `status: success` with `data.ocr.segments[]` populated.
2. If an error still occurs, check container logs (`docker logs test-bmad-backend`) — stack traces will now appear, pinpointing the exact failure.
3. If `ocr_execution_failed` appears instead of `ocr_provider_unavailable`, the credentials/permissions are the issue — verify the IAM user policy includes `textract:DetectDocumentText`.
