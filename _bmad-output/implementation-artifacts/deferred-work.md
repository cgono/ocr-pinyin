# Deferred Work

## Deferred from: code review of 4-8-track-google-translate-cost-for-pasted-text-requests (2026-04-01)

- Direct `os.environ.get()` in `estimate_text_processing_cost` bypasses app config layer — pre-existing pattern, `estimate_request_cost` uses the same approach
- `_GOOGLE_TRANSLATE_USD_PER_MILLION_CHARS` constant and `.env.example` value can drift independently — pre-existing, same situation as `_GCV_USD_PER_IMAGE`

## Deferred from: code review of 6-6-add-direct-pasted-text-study-mode (2026-04-01)

- Private helper imports from `process.py` (`_build_validation_error_response`, `_make_diagnostics` etc.) across modules — refactoring to a shared helpers module requires touching `process.py`, separate concern
- Budget-warn Sentry outcome tag set to `"success"` before being overridden by `"partial"` response — same pattern exists in image endpoint
- `pinyin_ms` timer excludes `enrich_translations` and `build_reading_projection` duration — pre-existing diagnostic style from image endpoint
- `file_size_bytes` counted on pre-normalization `source_text` bytes — minor diagnostic inaccuracy
- No budget-block integration test for `/v1/process-text` — follows same test gap as image endpoint
- `textarea` change during pending mutation can desync `inputMode`/`lastSubmittedMode` — submit button is disabled while pending so no functional impact
- **[Story candidate] Track Google Translate API cost in budget system** — `cost_estimate` for `/v1/process-text` is hardcoded to 0.0 USD/SGD because `budget_service.estimate_request_cost` is OCR-only. Text requests do call Google Translate (billed per character). A follow-on story should add `estimate_text_processing_cost(char_count)` to `budget_service` using Google Translate pricing, wire it into `process_text.py`, and record it via `record_request_cost` so the daily budget tracks all spend (not just OCR).

## Deferred from: code review of 6-2-add-per-line-pronunciation-playback-controls (2026-03-30)

- `cancelPlaybackIfActiveRef.current` reassigned on every render (stable-ref-callback pattern) — works correctly but any future non-ref closure dependency will silently break cleanup without a linter warning
- No `:active` CSS press state on `.pinyin-playback-button` — touch users see no press feedback while holding
- No test for `voiceschanged` event firing during active playback — unlikely but untested state transition
- `lineKey` includes `groupIndex` alongside `line_id` — could mismatch if group order shifts; unlikely in practice given deterministic `groupSegmentsByLine` output
- Fallback message not shown before first successful result — `speechFallbackMessage` is set on mount but the `<p>` is gated inside `pinyinSegments.length > 0`; acceptable for current story scope

## Deferred from: code review of 6-5-improve-reading-heuristic-with-clause-final-particle-detection (2026-03-31)

- `clause_length` counts all characters including spaces, punctuation, and mixed-script glyphs without reset — inflates the preceding-char count for the minimum-length guard on mixed-content OCR output; unlikely to matter for typical Chinese text
- Early-return on terminal punctuation skips all particle processing — `_derive_display_text` returns unchanged text for already-punctuated input, so mid-string particles are never processed; intentional per AC 4 but asymmetric and undocumented
- Interior CJK punctuation (、…—) does not reset `clause_length` — a particle appearing just after `、` has an inflated preceding-char count; edge case for OCR content

## Deferred from: code review of 6-4-add-optional-auto-punctuation-and-sentence-aware-reading-groups (2026-03-31)

- `_derive_display_text` appends 。 to text ending in closing brackets/quotes (e.g., `「好。」` → `「好。」。`) — v1 heuristic known limitation; improve terminal-punctuation detection in a future reading service iteration
- `line_id=None` mid-sequence creates non-adjacent group indexes for same line_id — `[line_id=2, None, line_id=2]` produces two groups with non-consecutive indexes; frontend adjacency check rejects them; resolution tied to the all-or-nothing validation decision
- Hardcoded confidence values 0.78/0.64 have no documentation — add inline comment explaining the rationale in next pass
- `_concat_source_text` strips whitespace but frontend searches raw `source_text` — whitespace in source_text causes `buildDisplayParts` to silently return null and fall back; unlikely in practice
- `current_line_id or 0` semantically misleading but never fires — replace with `0 if current_line_id is None else current_line_id` for clarity
- Missing test: `build_reading_projection(PinyinData(segments=[]))` — returns None correctly but untested
- Missing test: `line_id=None` mid-sequence flush path in `_group_segments_by_line` — `[line_id=0, line_id=None, line_id=1]` exercises the flush-on-None branch but no test covers it

## Deferred from: code review of 6-3-add-full-page-sequential-pronunciation-playback (2026-03-30)

- `onSequenceEnd` closes over render-scope `lineGroups` — safe via session guard but fragile; future weakening of session guard would silently break sequence advancement
- `buildLineKey` still embeds `groupIndex` — violates Story 6.2 "stable identifiers" deferred note; not worsened but not resolved
- Cancel/`onend` race on Safari — simultaneous `onend` + stop click can cause spurious extra `speak` call before cancel runs; session guard ultimately recovers
- Backend regression unverified — pre-existing local `pytest` environment failure; story makes no backend changes
- `handlePagePlayback` skips `!speechSynthesis` guard — benign since `startUtterance` catches it, but `cancelPlayback` fires unnecessarily in unsupported browsers
