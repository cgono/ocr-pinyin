# Sprint Change Proposal — Auto-Punctuation for Reading Flow

**Date:** 2026-03-31
**Scope:** Moderate — additive reading feature with cross-artifact updates
**Status:** Approved

---

## Section 1: Issue Summary

**Trigger:** Live reading usage after Epic 6 pronunciation work.

The current result view preserves OCR line layout and supports line/page pronunciation playback, but some Chinese source material arrives without punctuation. That creates three practical problems in the current product:

1. **Reading friction:** unpunctuated Chinese is harder to scan quickly during live reading.
2. **Playback pacing:** browser speech synthesis currently speaks concatenated Hanzi per line with no inferred pauses, so dictation sounds flatter than natural sentence rhythm.
3. **Wraparound pressure:** the current UI renders one `<ruby>` per `PinyinSegment`, and each `PinyinSegment` is still generated one-for-one from an OCR segment. When OCR returns a long line or paragraph-sized segment, the visual unit is too coarse, so wrapping remains suboptimal even after Story 4.2 preserved `line_id`.

Evidence from the current codebase and artifacts:

- The UX spec repeatedly describes the desired output as **sentence-level pinyin**, while the implementation still groups purely by `line_id`.
- `backend/app/services/pinyin_service.py` returns exactly one `PinyinSegment` per OCR segment.
- `frontend/src/features/process/components/UploadForm.jsx` renders one `<ruby>` per `PinyinSegment` and builds playback text by concatenating `source_text` for each line group.
- Stories 6.2 and 6.3 improved playback controls, but they intentionally reuse the existing grouped line model, so missing punctuation still propagates directly into speech pacing.

Problem statement:

> The app currently preserves OCR lines, not reading sentences. For punctuationless Chinese pages, that is sufficient for raw fidelity but not for assisted reading. A best-effort sentence/punctuation layer is needed if the product is to better support natural reading, speech pauses, and long-line readability.

---

## Section 2: Impact Analysis

**Epic Impact:**

- Epic 6 is the correct home for this change. The feature is tightly coupled to translation/pronunciation output and the already-completed line/page playback stories.
- Epic 5 remains unaffected and should stay behind Epic 6 in priority.
- No existing epic becomes invalid.

**Story Impact:**

- No completed story needs rollback.
- Add one new story after 6.3:
  - `6-4-add-optional-auto-punctuation-and-sentence-aware-reading-groups`
- Existing Stories 6.1, 6.2, and 6.3 remain done, but the new story builds on their output model.

**Artifact Conflicts / Updates Needed If Approved:**

- `epics.md`: add Story 6.4 under Epic 6.
- `prd.md`: add a new functional requirement for optional inferred punctuation in reading output.
- `ux-design-specification.md`: clarify that sentence-level readability may be assisted by inferred punctuation when source text lacks punctuation.
- `architecture.md`: document a derived reading-text layer or post-processing step so raw OCR data remains unchanged while display/playback text can be enhanced.
- `sprint-status.yaml`: add Story 6.4 as `backlog` after approval.

**Technical Impact:**

- Backend:
  - Add a best-effort post-processing stage after OCR/pinyin alignment that can infer sentence/clause boundaries for Chinese text lacking punctuation.
  - Preserve raw OCR segments and existing diagnostics; inferred punctuation must be additive, not destructive.
  - Add a separate `data.reading` projection rather than mutating `data.pinyin.segments`.
- Frontend:
  - Render derived reading groups that improve scanability and wrapping without removing access to the original segment-aligned output.
  - Feed punctuated text into pronunciation playback when available.
- API/schema:
  - Introduce explicit derived reading fields/groups instead of rewriting existing `PinyinSegment.source_text`.
  - Make the reading-provider boundary explicit in the API so the UI can communicate when auto-punctuation was applied and which engine produced it.

**Affected areas that should remain unchanged:**

- OCR provider contracts
- Existing raw diagnostics payloads
- Translation behavior from Story 6.1, except where translation later chooses to reuse punctuated text for quality

---

## Section 3: Recommended Approach

**Selected approach:** Direct adjustment, but scope it as an **optional, best-effort derived reading layer**, not a rewrite of raw OCR content.

**Recommendation details:**

1. Keep raw OCR and aligned pinyin segments as the source of truth.
2. Add a new `data.reading` representation for reading:
   - inferred punctuation when the source lacks it
   - sentence/clause-aware reading groups for display and playback
   - optional fallback to the current raw line-group rendering when inference is unavailable or low-confidence
3. Use the derived representation only for:
   - the main reading view
   - pronunciation playback text
   - wrap-friendly grouping
4. Continue exposing the raw OCR/pinyin segments in diagnostics or details so the enhancement remains transparent and reversible.

**Why this is the correct tradeoff:**

- It addresses the real user value: easier reading and better pauses.
- It avoids corrupting the raw OCR record, which matters for debugging and trust.
- It contains risk: if punctuation inference is wrong, the user can still fall back to the raw result.
- It aligns with the UX’s sentence-level goal better than the current line-only grouping.

**Effort:** Medium

**Risk:** Medium

**Timeline impact:** Low to Medium. This is likely one focused implementation story, but the acceptance criteria need to be explicit because the wrap issue and punctuation issue are related but not identical.

**Important caveat:**

Auto-punctuation alone is unlikely to fully solve long-line wrap problems if the UI still renders one oversized ruby unit per OCR segment. The story should therefore cover both inferred punctuation and sentence-aware regrouping/chunking for the reading projection. Otherwise the feature will improve pauses but only partially improve layout.

---

## Section 4: Detailed Change Proposals

### PRD addition

Add a new functional requirement:

```
FR43: System can optionally infer punctuation and sentence/clause boundaries for Chinese reading output when source text lacks punctuation.
```

Rationale: this is a new user-visible capability, not just an implementation detail.

### Epic 6 addition

Add a new story after Story 6.3:

```
### Story 6.4: Add Optional Auto-Punctuation and Sentence-Aware Reading Groups

As Clint,
I want the app to infer punctuation and sentence/clause grouping for Chinese text that arrives without punctuation,
So that the reading result is easier to follow, wraps more naturally, and spoken playback includes more natural pauses.

Acceptance Criteria:

1. Given OCR and pinyin succeed for Chinese text that contains little or no punctuation,
When the result is displayed,
Then the main reading view can show a derived punctuated version of the text
And the original raw OCR-aligned data remains available unchanged for diagnostics/details.

2. Given punctuation inference is available,
When the UI renders the reading result,
Then the display is grouped into shorter sentence/clause-aware reading units rather than only raw OCR line units
And long content wraps more naturally than the current one-ruby-per-long-segment behavior.

3. Given pronunciation playback is triggered for a derived reading unit or for the full page,
When inferred punctuation exists,
Then the spoken text uses the punctuated reading form so pauses are more natural
And playback controls otherwise keep their current behavior.

4. Given punctuation inference fails, is disabled, or returns low-confidence output,
When the result is displayed,
Then the app falls back to the current line-group rendering and playback behavior
And no existing OCR/pinyin result is lost.

5. Given existing backend and frontend tests run,
When the additive reading-layer schema and rendering changes are introduced,
Then current raw-segment contracts remain backward compatible
And the new behavior is covered by targeted tests for fallback, grouping, and playback text selection.
```

### Schema direction

Add a separate reading projection under `ProcessData`:

```json
{
  "data": {
    "ocr": { "segments": [] },
    "pinyin": { "segments": [] },
    "reading": {
      "mode": "derived",
      "provider": {
        "kind": "heuristic",
        "name": "built_in_rules",
        "version": "v1",
        "applied": true,
        "confidence": 0.78,
        "request_id": null,
        "warnings": []
      },
      "groups": [
        {
          "group_id": "rg_0",
          "line_id": 0,
          "raw_text": "老师叫同学们好我们开始上课了",
          "display_text": "老师叫同学们好，我们开始上课了。",
          "playback_text": "老师叫同学们好，我们开始上课了。",
          "confidence": 0.78,
          "segment_indexes": [0, 1, 2]
        }
      ]
    }
  }
}
```

Schema rules:

- `data.ocr` and `data.pinyin` remain unchanged as raw source-of-truth data.
- `data.reading.provider` is explicit and future-ready for `heuristic`, `remote_service`, or `llm`.
- `data.reading.groups` contains derived reading text only, not duplicated ruby-ready token structures.
- Each reading group references canonical `pinyin.segments` through `segment_indexes`.
- A reading group may span multiple adjacent raw segments, but only within the same `line_id`.
- No cross-line grouping, no segment reordering, and no mutation of raw OCR/pinyin text.

Rationale:

- This keeps alignment and diagnostics anchored to one canonical representation.
- It still allows semantically useful grouping when OCR splits a clause across multiple adjacent raw segments.
- It preserves a clean upgrade path to a future remote service or LLM-backed punctuation provider without changing the frontend contract again.

### Architecture note

Add a small derived-reading layer in the processing/rendering model:

```
Raw OCR/Pinyin Segments  ->  Derived Reading Projection  ->  Main Reading UI / Playback
                           (optional punctuation +       (diagnostics still use raw data)
                            sentence/clause grouping)
```

Rationale: this keeps the trustworthy raw data model separate from assistive presentation logic.

### UX specification note

Clarify that the product’s existing “sentence-level pinyin” goal may be achieved by an assistive punctuation/grouping layer when source pages omit punctuation, while preserving a path to inspect the original extracted form.

---

## Section 5: Implementation Handoff

**Scope classification:** Moderate

**Handoff target:** Scrum Master / planning owner for approval, then Dev agent for implementation

**Deliverables after approval:**

1. Update `prd.md` with FR43.
2. Update `epics.md` with Story 6.4.
3. Update `architecture.md` and `ux-design-specification.md` with the derived reading-layer note.
4. Update `sprint-status.yaml` with Story 6.4 as `backlog`.
5. Create the Story 6.4 implementation artifact.

**Success criteria:**

- Punctuationless Chinese pages become easier to read in the default view.
- Playback uses more natural pauses where inferred punctuation exists.
- Long reading output wraps more cleanly than the current coarse line-only rendering.
- Raw OCR/pinyin data remains inspectable and unchanged as the system of record.
- The API explicitly reports whether auto-punctuation was applied and by which provider type.
- Fallback to the current behavior is preserved when inference is unavailable or incorrect.

**Approval status:** Approved by user on 2026-03-31
