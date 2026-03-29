# Sprint Change Proposal Process

This document defines the working process for proposing, reviewing, and applying a sprint change in this repository. It is based on the approved proposal history in `_bmad-output/planning-artifacts/` and is intended to replace ad hoc memory with a single reference.

## Purpose

Use a sprint change proposal when a new finding changes the planned story set, acceptance criteria, sequencing, or implementation direction for work that belongs to the current project roadmap. The goal is to preserve a clear decision trail before backlog or artifact updates are made.

## When To Trigger

Create a sprint change proposal when at least one of these conditions is true:

- A gap or error changes the acceptance criteria or intended outcome of an existing story.
- New work is discovered that belongs in the current epic but does not have a story yet.
- Story scope needs to expand, contract, split, or be renumbered in a way that affects other stories.
- An external dependency, platform constraint, or provider limitation forces a design change.
- Planning artifacts are no longer aligned with the implementation direction and need an approved correction.
- A retrospective or epic-close review uncovers a gap in process, tooling, or artifact quality that requires backlog or planning changes.

Do not create a proposal for work that stays inside the current story boundary, such as:

- Routine implementation detail choices that do not change acceptance criteria.
- Bug fixes that are clearly already inside the active story scope.
- Small clarifications that do not affect backlog structure or planning artifacts.

### Inline vs. Proposal

Use the lighter inline path when the issue is a narrow defect or configuration fix and all of these remain true:

- No epic or story definitions need to change.
- No new story needs to be added.
- No existing story needs to be renumbered, re-sequenced, or rewritten.
- PRD, architecture, and UX artifacts remain materially unchanged.

The proposal on `2026-03-18` is the example of this lighter path: the issue was documented, fixes were applied directly, and no backlog restructuring was required.

For the inline path, after applying the fix: update `last_updated` in `sprint-status.yaml` with a brief comment describing the change. No other artifact updates are required unless a story status changed.

If any backlog, acceptance-criteria, or planning-artifact change is required, use the full proposal path.

## Proposal Format

The canonical format is the five-section structure used from `2026-03-19` onward. The older `2026-03-01` proposal is useful background, but it predates the current template. The `2026-03-18` proposal uses a different four-section structure (Change Trigger, Impact Assessment, Changes Applied, Verification Steps) and is the example of the inline path, not the five-section template.

### 1. Issue Summary

Capture the trigger, the concrete problem, and the evidence.

Include:

- What triggered the proposal.
- Which story, epic, or review uncovered it.
- The problem statement in plain language.
- Evidence such as failing behavior, source references, test findings, or constraints from external systems.

### 2. Impact Analysis

Describe exactly what changes if the proposal is accepted.

Include:

- Epic impact.
- Story impact.
- Artifact conflicts or required updates.
- Technical impact.

State both affected and unaffected areas so future readers can see the blast radius quickly.

If the proposal affects stories in more than one epic, list each epic separately under Epic Impact and document any cross-epic sequencing constraints.

### 3. Recommended Approach

Record the chosen path and why it is the correct tradeoff.

Include:

- Selected approach, typically a direct adjustment when rollback is unnecessary.
- Rationale.
- Effort, risk, and timeline impact.

This section is the decision summary reviewers should be able to approve or reject.

### 4. Detailed Change Proposals

Translate the recommendation into concrete artifact updates.

Include:

- File-by-file or artifact-by-artifact changes.
- Old/new wording when story text or planning docs change.
- New stories, rewritten acceptance criteria, renumbering, or configuration changes.
- Brief rationale where it prevents ambiguity.

This section should be specific enough that another agent can apply the approved outcome without guessing.

### 5. Implementation Handoff

Define who acts next and what “done” looks like.

Include:

- Scope classification.
- Handoff target.
- Deliverables.
- Success criteria.

If the change adds new implementation stories, this section should say which artifacts must be updated and which story files must be created next.

## Review And Approval

The proposal author assembles the evidence and recommended approach, but the decision is a planning decision, not an implementation decision.

**Sequencing:** Draft the proposal file and write it to `_bmad-output/planning-artifacts/sprint-change-proposal-YYYY-MM-DD.md` before seeking approval. The approval decision is recorded in the proposal itself (typically in the Section 5 handoff or an explicit Approval record appended at the end). Do not apply artifact updates until approval is recorded.

### Reviewers

- Minor changes: Scrum Master or planning owner confirms the proposal and routes directly to development.
- Moderate changes: Scrum Master reviews with Product Owner (and Architect if architecture artifacts are affected) before handoff.
- Major changes: full team review before any backlog rewrite or implementation handoff.

The exact people may vary by session, but the approval should always be explicit and recorded in the proposal itself.

### Decision Options

Every proposal should end in one of these outcomes:

- Approved: apply the documented changes and proceed with the stated handoff path.
- Approved with adjustments: record the adjustments as a revision note within the proposal before applying artifacts, so the final approved state is traceable. Do not leave adjustments implicit.
- Rejected: keep current artifacts unchanged.
- Deferred: no immediate change; revisit later with more evidence or after current sprint work.

If the proposal is approved, it becomes the source of truth for the follow-on artifact updates.

## Applying The Outcome

After approval, update artifacts in this order.

### 1. Update `_bmad-output/planning-artifacts/epics.md`

Apply the planning change first.

Examples:

- Add a new story.
- Rewrite story acceptance criteria.
- Renumber or re-sequence stories.
- Amend epic goal text if the epic itself changed.

### 2. Update `_bmad-output/implementation-artifacts/sprint-status.yaml`

Reflect the approved backlog state operationally.

Rules:

- Add new story keys with `backlog` unless work is already in-flight or completed at proposal time, in which case use the actual current status.
- Rename or renumber story keys if the proposal changed story numbering.
- Preserve existing comments and status definitions.
- Update `last_updated` with the proposal application date.

### 3. Update existing story files when scope changed

If a story file already exists and the approved proposal changed its scope:

- Add a note in that story's `## Change Log`.
- Keep the story aligned with the approved artifact language.
- Do not silently leave an older story file contradicting `epics.md`.

### 4. Create story files for newly added stories

If the proposal adds a story that does not yet have an implementation artifact:

- Run the story-creation workflow to generate the new story file.
- Ensure its initial sprint status exists in `sprint-status.yaml`.
- Story file creation must be completed in the same PR or working-tree commit as the `epics.md` and `sprint-status.yaml` updates. Do not leave story keys in `sprint-status.yaml` at `backlog` with no corresponding story file indefinitely.

### 5. Commit the proposal file alongside the artifact updates

The proposal file itself (`sprint-change-proposal-YYYY-MM-DD.md`) must be committed in the same PR as the artifact changes it authorizes. A proposal referenced in `sprint-status.yaml` comments or `epics.md` notes but not committed breaks the audit trail.

### 6. Do not rewrite the historical proposal file

Approved sprint change proposal files are historical records. Apply the outcome in the target artifacts instead of editing the original proposal after the fact.

## Scope Classifications

Use the following classification when routing the approved proposal.

| Classification | Meaning | Typical Handoff |
|---|---|---|
| Minor | Additive or narrow corrective change with low effort and no architectural replan | Dev agent implements directly |
| Moderate | Cross-story or cross-artifact change needing planning coordination | SM reviews with PO (and Architect if architecture artifacts are affected), then handoff to Dev |
| Major | Architectural change, major re-sequencing, or significant scope reset | Full team review before handoff |

**Note on classification judgment:** The boundary between Minor and Moderate requires judgment. Adding two or more stories and renumbering existing ones is on the Minor/Moderate boundary — the deciding factor is whether planning coordination is needed before implementation begins. When in doubt, use Moderate.

## Working Conventions From Existing Proposals

The approved proposal history shows a few stable conventions:

- Use the five-section structure for new proposals.
- Be explicit about whether the change is additive, corrective, or a re-sequencing.
- Name the affected artifacts directly instead of referring to them abstractly.
- Record the scope classification and handoff path in the proposal.
- Treat `epics.md` as the planning source of truth and `sprint-status.yaml` as the operational tracking view.
- When new stories are introduced, create or update their implementation artifacts in the same PR as the approval artifact updates — not in a follow-up session — so the backlog and story files stay aligned.

## Source References

This process document was derived from these proposal records:

- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-01.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-18.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-19.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-22.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-26.md`
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-27.md`
