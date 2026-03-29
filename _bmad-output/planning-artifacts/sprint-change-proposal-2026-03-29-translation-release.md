# Sprint Change Proposal — Translation Feature + Release Strategy

**Date:** 2026-03-29
**Scope:** Moderate — new epic + story, one-time repo configuration
**Status:** Approved

---

## Section 1: Issue Summary

Two proactive improvements proposed between Epic 4 (complete) and Epic 5 (backlog).

**1A — Translation Feature:** The PRD lists "English translation for extracted text" as a Growth Feature. Now that line-layout is stable (Story 4.2 introduced `line_id` on segments), a per-line translation layer is architecturally straightforward and high personal value. Requested display format: `pinyin / characters / translation` stacked per line group.

**1B — Release Strategy:** render.yaml already has staging and production services configured (four services: two on `main`, two on `staging`). What is missing is a documented git branch flow and the `staging` branch itself in the remote. Without this, all PRs merge directly to `main` with no staging gate.

---

## Section 2: Impact Analysis

**Epic Impact:**
- Epic 4: done, unaffected
- Epic 5 (History): remains backlog; **deprioritized below new Epic 6** at user's direction — Epic 6 will be worked first
- **New Epic 6: Translation & Pronunciation Output** — Story 6.1 added; Story 6.2+ reserved for future audio pronunciation
- Epic 5 stories unchanged; they follow Epic 6 completion

**Story Impact:**
- No existing stories modified
- New Story 6.1 added (see Section 4)

**Artifact Conflicts:**
- `epics.md`: Epic 6 section added; epic priority note added
- `prd.md`: FR42 added; "English translation" promoted from Growth Feature to Planned (Epic 6); NFR9 reference to translation confirmed active
- `sprint-status.yaml`: Epic 6 and Story 6.1 added; priority ordering noted
- `architecture.md`: New translation provider component noted (implementation detail deferred to story)
- `render.yaml`: No change — staging services already configured
- `.github/workflows/ci.yml`: No change — already runs on `staging` branch pushes
- `.github/workflows/release-please.yml`: No change — correctly fires only on `main`

**Technical Impact:**
- New dependency: `google-cloud-translate>=3.0,<4.0` (same GCP project and credentials as `google-cloud-vision`)
- Schema change: `PinyinSegment` gains `translation_text: str | null` (null when translation disabled/unavailable — backwards compatible)
- New env var: `TRANSLATION_ENABLED=true` (default `true` in production; tests set `false` to avoid live API calls)
- Cost: negligible — Google Translate free tier is 500k chars/month; personal usage will not exceed this

---

## Section 3: Recommended Approach

**Direct Adjustment — both changes**

**Translation:** Add Epic 6 with Story 6.1. Google Cloud Translation API selected as provider (same GCP credentials as Cloud Vision, cheapest option at ~$0.000004/request vs ~$0.000015 for LLM alternatives, ~100ms latency add, no new account or billing setup needed).

**Release strategy:** Formalize the branch flow that render.yaml already supports:

```
feat/* ──PR──▶ staging ──promote PR──▶ main
                 │                        │
         Render auto-deploys         Render auto-deploys
         staging services            production services
                                          │
                                   release-please fires
                                   → release PR → tag
```

- Feature PRs target `staging` (set as default target in GitHub repo settings)
- CI must pass before merge to staging
- Promote PR (`staging → main`) is a squash-or-merge; no new review required for solo dev
- release-please continues to fire only on `main` (version tags belong to production)

---

## Section 4: Detailed Change Proposals

### Epic 6: Translation & Pronunciation Output (new)

Added to `epics.md` after Epic 5.

```
### Epic 6: Translation & Pronunciation Output
Add English translation for extracted Chinese text, with architecture extensibility
for future audio pronunciation output.
Depends on: Epic 2 (segment alignment), Epic 4 (line_id layout)
FRs covered: FR42
```

### Story 6.1: Add English Translation Below Chinese Characters (new)

```
As Clint,
I want an English translation displayed below each line of Chinese characters in the result,
So that I can understand the meaning without switching to another app.

Display format per line group:
  lǎo shī jiào        ← pinyin (existing)
  老师叫               ← characters (existing)
  Teacher calls out   ← translation (new, smaller/muted style)

Acceptance Criteria:

Given a successful OCR + pinyin result
When TRANSLATION_ENABLED=true
Then each PinyinSegment in the API response includes translation_text (non-null string)
And the frontend renders translation_text below the character row in smaller, muted styling.

Given TRANSLATION_ENABLED=false or the translation call fails
When the result is returned
Then translation_text is null
And the existing display is unchanged with no regression.

Given all existing backend and frontend tests run
When the schema change is applied
Then all existing tests continue to pass.

Schema change:
OLD PinyinSegment: { source_text, pinyin_text, alignment_status, reason_code, line_id }
NEW PinyinSegment: { source_text, pinyin_text, alignment_status, reason_code, line_id, translation_text }

translation_text is null when TRANSLATION_ENABLED=false or translation unavailable.
translation_text is translated at the line level (one translation per line group, not per character).
```

### FR42 (new, added to prd.md)

```
FR42: System can return English translation for extracted Chinese text segments.
```

### Release Flow Convention

One-time setup (not a new story):
1. `git push origin HEAD:staging` — create the staging branch from current main
2. GitHub repo Settings → General → Default branch: set to `staging`
3. Create `docs/release-flow.md` documenting the convention (can be done inline during Epic 6 or as Story 6.0)

---

## Section 5: Implementation Handoff

**Scope: Moderate**

| Action | Who | When |
|---|---|---|
| Write Sprint Change Proposal (this document) | SM | Now |
| Update `epics.md`, `prd.md`, `sprint-status.yaml` | SM | Now |
| Create `staging` branch + set GitHub default PR target | Dev (Clint) | Before next feature PR |
| Story 6.1 implementation | Dev agent | Next sprint (Epic 6) |
| Epic 5 stories | Dev agent | After Epic 6 |

**Success criteria for Story 6.1:**
- Three-layer format renders correctly on result page
- `TRANSLATION_ENABLED=false` / null `translation_text` produces zero regression on existing tests
- No new GCP project, account, or billing setup required
- Google Translate cost per request is under $0.0001
