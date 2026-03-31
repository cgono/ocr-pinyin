# Deferred Work

## Deferred from: code review of 6-2-add-per-line-pronunciation-playback-controls (2026-03-30)

- `cancelPlaybackIfActiveRef.current` reassigned on every render (stable-ref-callback pattern) — works correctly but any future non-ref closure dependency will silently break cleanup without a linter warning
- No `:active` CSS press state on `.pinyin-playback-button` — touch users see no press feedback while holding
- No test for `voiceschanged` event firing during active playback — unlikely but untested state transition
- `lineKey` includes `groupIndex` alongside `line_id` — could mismatch if group order shifts; unlikely in practice given deterministic `groupSegmentsByLine` output
- Fallback message not shown before first successful result — `speechFallbackMessage` is set on mount but the `<p>` is gated inside `pinyinSegments.length > 0`; acceptable for current story scope

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
