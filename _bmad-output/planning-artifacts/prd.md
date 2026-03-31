---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
inputDocuments: []
documentCounts:
  briefCount: 0
  researchCount: 0
  brainstormingCount: 0
  projectDocsCount: 0
workflowType: 'prd'
classification:
  projectType: api_backend
  domain: general
  complexity: low
  projectContext: greenfield
---

# Product Requirements Document - test-bmad

**Author:** Clint
**Date:** 2026-02-28T13:14:32Z

## Executive Summary

This product is a personal, learning-driven LangChain backend with a lightweight phone-accessible web interface that converts photos of Chinese children's story books into Hanyu Pinyin. The primary user is you. The immediate user outcome is faster, repeatable Chinese reading practice from real books; the parallel outcome is hands-on understanding of how LangChain orchestrates tools, optional toolsets, and skills in a practical workflow.

The core problem is not only text conversion. The deeper need is building credible, experience-based LangChain knowledge that can be applied in workplace technical discussions. The product intentionally ties language practice to agent-system learning so each usage session produces both linguistic and technical value.

### What Makes This Special

The differentiator is end-to-end integration in one app: capture photo, process, and receive pinyin output without manual copy-paste across OCR and chat tools. This reduces friction and supports frequent use on mobile.

A second differentiator is pedagogical transparency for the builder: the architecture is designed so the workflow itself teaches LangChain implementation patterns (tool invocation boundaries, orchestration flow, and extensibility for future capabilities such as pronunciation audio generation). The product is intentionally scoped as a weekend project to maximize learning velocity while still delivering a useful daily workflow.

## Project Classification

- Project Type: `api_backend` with companion `web_app`
- Domain: `general`
- Complexity: `low` (domain), with moderate technical orchestration complexity
- Project Context: `greenfield`

## Success Criteria

### User Success

The user can upload a single photo of a Chinese story book page and receive:
- detected Chinese characters from the image
- correct Hanyu Pinyin for those characters

Primary success priority is correctness over speed, because output is used for live reading with a child and must avoid teaching incorrect pronunciation. Secondary priority is fast response during reading flow.

### Business Success

For this personal project, success is measured by capability transfer:
- Within 1 month, you can explain LangChain architecture, tool use, and orchestration tradeoffs with concrete examples from this app.
- Within 3 months, you can contribute meaningfully in workplace technical discussions with implementation-grounded insights rather than theoretical familiarity.

### Technical Success

- OCR + pinyin pipeline output quality is consistently high for typical phone photos of children's Chinese books.
- End-to-end response time target is under 2 seconds in normal conditions, while preserving accuracy-first behavior.
- Failure modes are handled clearly (for example: low-quality image, uncertain recognition, partial extraction), with actionable feedback instead of silent or incorrect output.

### Measurable Outcomes

- Accuracy: pinyin output is correct for the vast majority of recognized characters on typical input pages.
- Speed: median end-to-end processing time < 2 seconds on target runtime.
- Usability: one-step capture/upload to pinyin result, without manual copy-paste across apps.
- Learning objective: you can walk through the implemented LangChain pipeline and justify major design decisions.

## Product Scope

### MVP - Minimum Viable Product

- Backend service using LangChain orchestration.
- Web UI accessible from phone for image upload.
- Image parsing/OCR to extract Chinese characters.
- Pinyin generation from extracted characters.
- Basic response presentation in UI.

### Growth Features (Post-MVP)

- Audio pronunciation generation for pinyin output.
- English translation for extracted text — **planned (Epic 6, Story 6.1)**.
- Quality enhancements for harder images/pages (lighting, skew, layout variation).

### Vision (Future)

- Personal "book compilation" capability:
  - store processed pages/translations/audio results
  - organize them as a reusable personal reading collection
  - save and reload completed books for re-reading sessions
- Explicitly personal-use workflow, with no public distribution.

## User Journeys

### Journey 1: Primary User Success Path (Live Reading Flow)

Clint is reading a Chinese story book with his daughter and hits an unfamiliar character sequence. He opens a phone shortcut to the app, taps `Upload Photo`, and captures the page. The system validates image quality first (focus, lighting, framing), then runs OCR for Chinese text extraction, filters out non-Chinese content when possible, and generates Hanyu Pinyin. The result screen shows the original uploaded image and the generated pinyin directly below it so he can continue reading immediately.

The key value moment is continuity: no switching apps, no copy-paste, and no interrupted story flow. Accuracy is the primary expectation; speed supports the experience once accuracy is acceptable.

### Journey 2: Primary User Edge Case (Recognition and Mixed Content Errors)

Clint uploads a page containing mixed Chinese/English text and stylized typography. OCR extraction returns uncertain segments. The system highlights low-confidence output, ignores English text by default, and provides a clear fallback: ask for retake or proceed with marked uncertainty. If OCR appears wrong, the system displays diagnostics (raw extracted text, confidence/timing/tool trace) in a collapsible section above results so Clint can quickly understand whether the issue is image quality, OCR extraction, or conversion logic.

A second edge case appears when the source page already includes Chinese characters plus pinyin. The system still supports pronunciation assistance by preserving both forms and allowing downstream pronunciation support (future audio feature).

### Journey 3: Admin/Operations Journey (Cost and Usage Control)

In admin mode (same user, different role), Clint reviews a lightweight ops panel to understand usage, latency, and cost. He monitors per-request timings, error rates, and cost estimates for OCR/LLM/tool calls. The immediate objective is to keep the weekend prototype affordable while learning observability patterns using Sentry for error and performance monitoring. Later, this same path expands to saved book management and deployment health checks.

Success in this journey is operational confidence: the app is cheap enough to run, issues are observable, and system behavior is measurable.

### Journey 4: Support/Troubleshooting Journey (Self-Debug Loop)

When output quality is questionable, Clint opens diagnostics on the same page and inspects step-level details: upload metadata, OCR text output, confidence indicators, LangChain/tool execution trace, and total processing time. He can quickly decide whether to retry with a better image, adjust extraction handling, or tune prompt/tool logic. This short feedback loop supports reliability and learning goals.

Success here means fast root-cause identification without leaving the main reading interface.

### Journey 5: API/Integration Journey (Near-Term Developer Path)

For tonight's target, Clint uses a simple upload mechanism via web UI. In the near term, the same backend exposes a basic upload endpoint to support automation or alternate clients (shortcut, script, or future app surface). The developer experience priority is minimal integration friction: one endpoint, clear request/response shape, and stable pinyin output contract.

This journey ensures MVP can evolve into reusable LangChain-backed services without redesigning core flow.

### Journey Requirements Summary

These journeys imply capability requirements in five areas:
- Core processing: photo upload, quality validation, OCR, Chinese-text filtering, pinyin generation, result rendering.
- Error handling: confidence-aware output, mixed-language filtering, explicit fallback paths for wrong OCR and low-quality images.
- Observability: request timing, error tracking, cost/usage instrumentation, and Sentry integration.
- Diagnostics UX: collapsible same-page debug block with raw OCR + trace + timings for self-support.
- Extensibility: architecture that cleanly adds audio pronunciation, translation, and saved-book compilation later.

## API Backend Specific Requirements

### Project-Type Overview

The product is an API-first backend with LangChain orchestration plus a phone-friendly web interface. MVP prioritizes a reliable pipeline for image upload, OCR extraction, and pinyin conversion. The API must also expose operational visibility (health/metrics) and basic result history.

### Technical Architecture Considerations

- LangChain runs in the backend service as the orchestration layer for OCR-to-pinyin flow.
- Web frontend consumes backend APIs and also renders HTML views for direct phone usage.
- API design starts with explicit versioning (`/v1`) to avoid migration friction later.
- System design prioritizes correctness first, then speed, with measurable latency and quality diagnostics.

### Endpoint Specifications

MVP endpoint groups:
- Processing:
  - `POST /v1/process` for upload + OCR + pinyin in a single call (primary path)
  - Optionally internal split flow for `upload`, `ocr`, `pinyin` stages while keeping one public MVP entrypoint
- Operations:
  - `GET /v1/health` for service health
  - `GET /v1/metrics` for usage/cost/performance metrics
- History:
  - `GET /v1/history` for recent processed sessions/pages
  - `GET /v1/history/{id}` for a specific prior result record

### Authentication Model

- MVP: no authentication required (single-user personal deployment context).
- Future-ready note: Apple ID based authentication is the preferred direction if auth is later introduced for family/shared usage.

### Data Formats and Schemas

- API responses: JSON for programmatic use.
- Web interface: rendered HTML response/view for phone UX.
- Core payloads include:
  - uploaded image reference/metadata
  - extracted Chinese text
  - generated pinyin output
  - confidence/diagnostic indicators
  - processing timings and estimated request cost

### Rate Limits and Cost Controls

- Hard daily budget target: approximately `1 SGD/day`.
- MVP enforcement approach:
  - request-level cost estimation and tracking
  - daily budget guardrail that blocks or warns when threshold is reached
  - lightweight per-request size constraints to avoid accidental high-cost uploads

### Versioning Strategy

- API starts at `/v1` from day one.
- Breaking changes require new version path; non-breaking additions stay in `v1`.
- Package releases (frontend and backend) are managed via release-please using conventional commits. GitHub Releases are created automatically on merge to main.

### Implementation Considerations

- Keep MVP minimal: basic HTTP API + frontend only; no SDK.
- Prioritize deterministic response structure and clear failure responses.
- Include diagnostics in response model to support self-debug workflow.
- Ensure health/metrics endpoints are useful enough for Sentry-backed troubleshooting and lightweight dashboarding.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-solving plus validated-learning MVP.
Deliver one reliable reading-assist workflow while exposing enough internals (diagnostics and metrics) to teach practical LangChain orchestration.

**Resource Requirements:** Solo builder, full-stack delivery with orchestration and basic observability instrumentation.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Primary user success path (live reading flow)
- Primary user edge path (wrong OCR, mixed language, low confidence)
- Self-support diagnostics path

**Must-Have Capabilities:**
- Phone-friendly web UI with image upload
- Backend `/v1` processing endpoint for OCR plus pinyin
- Chinese-text-focused extraction with English filtering behavior
- Accuracy-first response handling with confidence/error messaging
- JSON plus rendered HTML output showing image and pinyin
- Health and metrics endpoints
- Daily budget guardrail around `1 SGD/day`
- Basic history retrieval

### Post-MVP Features

**Phase 2 (Post-MVP):**
- Audio pronunciation output
- English translation
- Better image robustness (lighting, skew, layout)
- Deeper Sentry dashboarding and alerting

**Phase 3 (Expansion):**
- Personal book compilation workflow (save/reload full books)
- Optional family access with Apple ID authentication
- Richer management for saved books and reading sessions

### Risk Mitigation Strategy

**Technical Risks:** OCR inaccuracies, mixed-language extraction errors, latency variance.
Mitigation: confidence indicators, retry guidance, diagnostics trace, and accuracy-first fallback behavior.

**Market Risks:** Low external market relevance (personal project).
Mitigation: measure success by direct utility and workplace knowledge transfer.

**Resource Risks:** Weekend time constraint and solo implementation bandwidth.
Mitigation: single public processing endpoint, minimal auth, no SDK, strict MVP boundary.

## Functional Requirements

### Image Intake & Validation

- FR1: Primary user can upload a photo from phone to start processing.
- FR2: System can validate uploaded image quality before OCR processing.
- FR3: System can reject invalid or unreadable images with actionable feedback.
- FR4: System can retain upload metadata for diagnostics and history.

### Text Extraction & Language Handling

- FR5: System can extract Chinese characters from uploaded images.
- FR6: System can detect and ignore non-Chinese text when generating pinyin.
- FR7: System can preserve extracted source text for user review.
- FR8: System can indicate uncertain extraction segments to the user.
- FR9: User can resubmit or retry processing when extraction quality is insufficient.

### Pinyin Generation & Result Presentation

- FR10: System can generate Hanyu Pinyin from extracted Chinese text.
- FR11: System can return pinyin output aligned to extracted source text.
- FR12: System can display uploaded image and generated pinyin in one result view.
- FR13: System can return results as JSON for API consumers.
- FR14: System can render HTML response for direct phone web usage.
- FR15: System can provide clear processing status and completion outcome.

### Error Handling & Recovery

- FR16: System can communicate processing failures with explicit reason categories.
- FR17: System can provide fallback guidance when OCR confidence is low.
- FR18: System can handle mixed Chinese/English page inputs without failing the whole request.
- FR19: System can return partial results when full extraction is not possible.
- FR20: System can allow user-initiated retry from the same interface flow.

### Diagnostics & Observability

- FR21: User can view diagnostics in a collapsible section on the result page.
- FR22: System can expose raw OCR output for troubleshooting.
- FR23: System can expose confidence indicators for extracted text.
- FR24: System can expose request timing details for each processing run.
- FR25: System can expose LangChain/tool execution trace data for debugging.
- FR26: System can emit usage and error telemetry suitable for Sentry error and performance monitoring.
- FR27: System can provide service health status via API endpoint.
- FR28: System can provide operational metrics via API endpoint.
- FR41: System can be deployed to Render using a static frontend service and web-service backend.

### Cost Control & Usage Governance

- FR29: System can estimate per-request processing cost.
- FR30: System can track daily aggregate cost usage.
- FR31: System can enforce or warn on a configurable daily budget threshold.
- FR32: System can restrict oversized or potentially expensive inputs.

### History & Personal Reuse

- FR33: User can retrieve recent processing history.
- FR34: User can retrieve a specific historical result by identifier.
- FR35: System can store result artifacts required for later review.
- FR36: System can support future extension to saved-book compilation workflows.

### Translation & Pronunciation

- FR42: System can return English translation for extracted Chinese text segments.
- FR43: System can optionally infer punctuation and sentence/clause boundaries for Chinese reading output when source text lacks punctuation.

### API Lifecycle & Access Model

- FR37: System can expose processing capabilities through versioned `/v1` endpoints.
- FR38: System can expose history capabilities through versioned `/v1` endpoints.
- FR39: System can operate in MVP without user authentication.
- FR40: System can support future migration to Apple ID based authentication.

## Non-Functional Requirements

### Performance

- End-to-end processing from upload acceptance to pinyin result should complete within 2 seconds for typical phone photos under normal operating conditions.
- The system should prioritize output correctness over response speed when tradeoffs occur.
- Health and metrics endpoints should respond quickly enough to support live troubleshooting.

### Reliability

- The processing pipeline should return a structured outcome for every request: success, partial success, or clear failure.
- The system should fail gracefully on low-quality images, OCR uncertainty, or provider/tool errors, with retry guidance.
- History and diagnostics data should be persisted reliably for recent sessions.

### Security

- All network traffic should use TLS in transit.
- Uploaded images and derived text artifacts should be stored with access controls appropriate for personal/private usage.
- Secrets should be managed outside source code (environment variables or secret store).
- The system should support future addition of Apple ID authentication without re-architecting core flows.

### Cost & Resource Governance

- The system should track per-request and daily estimated processing cost.
- The system should enforce or warn at a daily budget threshold of approximately `1 SGD/day`.
- The system should apply request size and input constraints to prevent accidental high-cost usage.

### Observability & Diagnostics

- The system should expose request timings, OCR confidence indicators, and processing traces for debugging.
- The system should emit telemetry and error events compatible with Sentry monitoring.
- Error events should include reason categories to support rapid root-cause identification.

### Integration

- API contracts should be versioned under `/v1` and remain backward compatible for non-breaking changes.
- The backend should provide JSON responses for API consumers and support rendered HTML flow for phone web usage.
- The design should preserve extensibility for future audio, translation, and personal book-compilation integrations.
- The hosted production target should be Render, while local development continues to use Docker Compose.
