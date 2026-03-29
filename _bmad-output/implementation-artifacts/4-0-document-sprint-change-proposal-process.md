# Story 4.0: Document Sprint Change Proposal Process

Status: done

## Story

As Clint,
I want a clear reference document describing the sprint change proposal process,
So that any agent or collaborator can trigger, write, and apply a sprint change proposal consistently without relying on institutional memory.

## Acceptance Criteria

1. **Given** a developer or agent needs to propose a mid-sprint scope change, **When** they consult the process document, **Then** they find clear guidance on when to trigger a proposal, the required sections, and how to apply the outcome.

2. **Given** a sprint change proposal is approved, **When** the implementation handoff occurs, **Then** the document describes exactly which artifacts get updated (`sprint-status.yaml`, `epics.md`) and how.

3. **Given** the document exists, **When** it is reviewed, **Then** it is consistent with the four existing sprint change proposals in `_bmad-output/planning-artifacts/` and does not contradict any of them.

## Tasks / Subtasks

- [x] Create `docs/sprint-change-proposal-process.md` (AC: 1, 2, 3)
  - [x] Section: When to trigger — criteria for raising a proposal vs. handling inline
  - [x] Section: Proposal format — required sections with brief description of each
  - [x] Section: Review and approval — who reviews, what the decision options are
  - [x] Section: Applying the outcome — which artifacts to update and how (sprint-status.yaml, epics.md, story files)
  - [x] Section: Scope classifications — Minor / Moderate / Major and their handoff paths

- [x] Verify document is consistent with all four existing proposals:
  - [x] `sprint-change-proposal-2026-03-01.md`
  - [x] `sprint-change-proposal-2026-03-18.md`
  - [x] `sprint-change-proposal-2026-03-19.md`
  - [x] `sprint-change-proposal-2026-03-22.md`
  - [x] `sprint-change-proposal-2026-03-26.md`
  - [x] `sprint-change-proposal-2026-03-27.md`

## Dev Notes

### Story Foundation

- **Why this story exists:** The sprint change proposal process has been used six times across three epics. It works. But it lives only in example files — no canonical reference document exists. This story creates one so any future agent or collaborator can follow the process without needing to reverse-engineer it from examples.
- **No backend or frontend changes** — this story is documentation only. The deliverable is a single markdown file in `docs/`.
- **Source material:** All six existing sprint change proposals in `_bmad-output/planning-artifacts/`. Read all of them before writing the document. The process has evolved slightly — the 2026-03-01 proposal uses a slightly different section format than the later ones. The later format (Sections 1–5) is the canonical one.

### Canonical Proposal Format (from proposals 2026-03-18 onward)

The five-section structure used in all recent proposals:

1. **Issue Summary** — Problem statement, trigger context, evidence
2. **Impact Analysis** — Epic impact, story impact, artifact conflicts, technical impact
3. **Recommended Approach** — Selected path, rationale, effort/risk/timeline assessment
4. **Detailed Change Proposals** — File-by-file changes with old/new diffs where applicable
5. **Implementation Handoff** — Scope classification, handoff target, deliverables, success criteria

### Scope Classifications

Derived from existing proposals:

| Classification | Description | Handoff |
|---|---|---|
| Minor | Additive changes, no architectural implications, low effort | Dev agent implements directly |
| Moderate | Cross-story impacts, some design decisions | SM reviews with PO, then Dev agent |
| Major | Architectural changes, significant re-sequencing | Full team review before handoff |

### When to Trigger

A sprint change proposal is appropriate when:
- A gap or error is discovered that affects acceptance criteria of an existing story
- New work is identified that belongs in the current epic but has no story
- A story's scope needs to expand or contract in a way that affects other stories
- An external dependency (library, platform, provider) forces a design deviation

A proposal is **not** needed for:
- Implementation detail decisions within the bounds of an existing story spec
- Bug fixes discovered during testing that are clearly within story scope
- Minor clarifications that don't change acceptance criteria

### Applying the Outcome

After a proposal is approved:

1. **`_bmad-output/planning-artifacts/epics.md`** — update affected story ACs; add new stories if any
2. **`_bmad-output/implementation-artifacts/sprint-status.yaml`** — add new story keys with `backlog` status; update `last_updated`
3. **Affected story files** — if an existing story file exists and its scope changed, note the change at the top under a `## Change Log` section
4. **New story files** — run `bmad-create-story` for any newly added stories

### File Structure Requirements

**New file:**
- `docs/sprint-change-proposal-process.md`

**Files NOT to touch:**
- Any existing sprint change proposal files — they are historical records
- Any backend or frontend source files

**Note on `epics.md`:** This story's dev session also applied `sprint-change-proposal-2026-03-28.md` (Epic 4 restructuring triggered by live MVP testing), which required changes to `epics.md`. Those changes are separate in scope from Story 4-0 but were applied in the same working-tree pass. The Story 4-0 deliverable (`docs/sprint-change-proposal-process.md`) required no `epics.md` changes.

### Previous Story Intelligence

- The most recent proposals (2026-03-26 and 2026-03-27) represent the current canonical format. Use these as the primary reference.
- The 2026-03-01 proposal predates the five-section format — it's useful context but not the template to follow.
- Story 3.6 (from the 2026-03-27 proposal) is a good example of a "Minor" classification handled cleanly end-to-end.

### Git Intelligence

- `d54209b` — render.yaml fixes (post-merge infrastructure iteration)
- `4586b23` — Epic 3 merged (includes Story 3.6 CI improvements from the 2026-03-27 proposal)
- `674f74a` — course correction (applied 2026-03-22 and 2026-03-26 proposals)

## Dev Agent Record

### Agent Model Used

- GPT-5 Codex

### Completion Notes List

- Added `docs/sprint-change-proposal-process.md` as the canonical process reference for when to raise, structure, review, and apply a sprint change proposal.
- Derived the document from the six historical proposal records listed in Dev Notes and aligned the template guidance to the five-section format used from 2026-03-18 onward.
- Documented both the inline-fix path for narrow defects and the full proposal path for backlog or artifact changes so the process matches how the repo has actually been operated.
- Recorded the artifact application order for `_bmad-output/planning-artifacts/epics.md`, `_bmad-output/implementation-artifacts/sprint-status.yaml`, existing story files, and newly created story files.
- Performed manual validation by checking the new document's required sections, artifact references, and source-reference coverage against the six historical proposals.
- Repo automation validation could not be run in this shell because `npm`, `node`, and `uv` are not installed; no application code changed in this story.

### File List

- `docs/sprint-change-proposal-process.md`
- `_bmad-output/implementation-artifacts/4-0-document-sprint-change-proposal-process.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md` (Epic 4 restructuring from sprint-change-proposal-2026-03-28 + Story 4.0 entry + Story 4.1/4.2 AC updates from code review)
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-28.md`
- `_bmad-output/implementation-artifacts/epic-3-retro-2026-03-27.md`

## Change Log

- 2026-03-27: Story 4-0 created — document sprint change proposal process; carried from Epic 1 retro action item, formally created as Story 4-0 after Epic 3 retrospective
- 2026-03-28: Story implemented — added canonical sprint change proposal process documentation and validated it against six historical proposal records
- 2026-03-28: Code review patches applied — fixed five-section format attribution (2026-03-18→2026-03-19), added inline path artifact steps, Approved-with-adjustments guidance, Architect to Moderate handoff, retrospective trigger condition, proposal file placement and sequencing guidance, scope classification note, multi-epic guidance, story file creation boundary; AC updates for Stories 4.1 and 4.2 (cancel/dismiss, ping error handling, fallback baseline, schema change, visual gap); epics 1/2/3 closed; Story 4.0 added to epics.md; story marked done
