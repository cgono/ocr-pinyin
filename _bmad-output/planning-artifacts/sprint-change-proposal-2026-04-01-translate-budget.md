# Sprint Change Proposal — Budget Text-Translation Spend in Cost Guardrails

**Date:** 2026-04-01
**Scope:** Minor — additive backlog correction across existing cost-governance artifacts
**Status:** Approved

---

## Section 1: Issue Summary

**Trigger:** Deferred code-review follow-up from Story 6.6 on 2026-04-01.

The new pasted-text study flow introduced `POST /v1/process-text`, and that endpoint does call Google Translate for English translation. But the budget system still treats pasted-text requests as zero-cost because `budget_service.estimate_request_cost` only models OCR-oriented spend. As a result, request diagnostics and daily budget accounting undercount real provider usage whenever text-study requests are processed.

Problem statement:

> The product already promises request-level cost estimation and daily budget tracking, but pasted-text translation spend is currently omitted. Budget guardrails therefore under-report real spend and can give false confidence that the app is still under the daily threshold.

Evidence:

- `_bmad-output/implementation-artifacts/deferred-work.md` records the gap explicitly after Story 6.6 code review.
- Epic 4 already owns FR29, FR30, and FR31, which require per-request estimation, daily aggregate tracking, and budget-threshold enforcement.
- Epic 6 Story 6.6 added the pasted-text flow, so the new path now exercises Google Translate without the matching budget-service update.

---

## Section 2: Impact Analysis

**Epic Impact:**

- Epic 4 is the correct home for the follow-on work because the missing behavior is budget governance, not a new translation capability.
- Epic 4 should be reopened with one additive story:
  - `4-8-track-google-translate-cost-for-pasted-text-requests`
- Epic 6 remains valid as implemented; no Epic 6 story needs rollback.

**Story Impact:**

- Story 4.3 remains valid but was too image-centric in implementation.
- Story 4.4 and Story 4.5 are also affected indirectly because daily totals and threshold checks depend on complete cost accounting.
- Story 6.6 remains done, but it exposed the budgeting blind spot.

**Artifact Conflicts / Updates Needed:**

- `epics.md`: add a follow-on Epic 4 story covering text-request translation cost estimation and recording.
- `architecture.md`: clarify that budget guardrails apply to both `/v1/process` and `/v1/process-text`, with separate provider-pricing inputs as needed.
- `prd.md`: tighten operations-cost language so it explicitly includes translation/provider spend, not just OCR-oriented costs.
- `sprint-status.yaml`: reopen Epic 4 and add Story 4.8 as backlog.

**Technical Impact:**

- Backend:
  - extend `budget_service` with text-processing cost estimation based on Google Translate pricing and character count
  - wire `/v1/process-text` to record request cost using the same accounting path as image requests
  - ensure daily totals and budget-threshold checks include both image and text requests
- Tests:
  - add coverage that pasted-text requests update request diagnostics and daily budget totals correctly

---

## Section 3: Recommended Approach

**Selected approach:** Direct adjustment.

This is a bounded backlog correction against already-approved budget requirements. The cleanest path is to add one explicit cost-governance story rather than retroactively redefining Story 6.6 or reopening broader MVP scope.

**Option review:**

- Option 1, Direct adjustment: Viable. Low effort, low risk.
- Option 2, Potential rollback: Not viable. The pasted-text feature is valuable and does not need removal.
- Option 3, PRD MVP review: Not needed. MVP scope is unchanged; this is a compliance gap inside existing scope.

**Effort:** Low

**Risk:** Low

**Timeline impact:** Low. This should fit as a focused follow-on story with targeted backend and test changes.

---

## Section 4: Detailed Change Proposals

### Epic change

Add a new story under Epic 4:

```md
### Story 4.8: Track Google Translate Cost for Pasted-Text Requests

As Clint,
I want pasted-text translation requests included in request-cost estimation and daily budget accounting,
So that the budget system reflects actual Google Translate spend instead of treating text study as free.
```

Acceptance direction:

1. Estimate translation cost for `/v1/process-text` from submitted text size using configured Google Translate pricing rules.
2. Record text-request cost through the same accounting path used by image requests.
3. Include pasted-text spend in daily totals and budget-threshold decisions.
4. Preserve fallback behavior when translation is disabled or pricing metadata is unavailable.
5. Add targeted regression coverage for request diagnostics and aggregate accounting.

### Architecture change

Clarify the budget-service boundary from:

```md
- Budget guardrail -> `backend/app/services/budget_service.py`.
```

to:

```md
- Budget guardrail for both `/v1/process` and `/v1/process-text` -> `backend/app/services/budget_service.py`, including OCR/image estimation and text-translation estimation from provider pricing inputs.
```

### PRD wording change

Clarify the operations journey so cost observability explicitly includes translation spend:

```md
He monitors per-request timings, error rates, and cost estimates for OCR, translation, and other tool/provider calls.
```

### Sprint tracking change

Reopen Epic 4 and add Story 4.8 as `backlog` until the implementation artifact is created.

---

## Section 5: Implementation Handoff

**Scope classification:** Minor

**Route to:** Development team for direct implementation, with Scrum Master/backlog owner updating the new story artifact first

**Planning artifacts updated in this proposal:**

1. `prd.md`
2. `epics.md`
3. `architecture.md`
4. `sprint-status.yaml`

**Execution handoff for development:**

1. Create the Story 4.8 implementation artifact.
2. Add `estimate_text_processing_cost(char_count)` or equivalent budget-service entrypoint using Google Translate pricing.
3. Wire `/v1/process-text` cost estimation and `record_request_cost` into the text-processing path.
4. Add backend tests for text-request cost estimation, aggregate totals, and budget-threshold behavior.

**Success criteria:**

- Pasted-text requests no longer report zero estimated cost by default when translation runs.
- Daily budget totals include both OCR and text-translation spend.
- Budget warnings/blocks are based on complete spend, not only image-processing spend.

**Approval status:** Approved by user request on 2026-04-01
