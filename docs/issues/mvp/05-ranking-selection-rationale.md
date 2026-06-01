# MVP: Implement editorial ranking and Selection Rationale

## Problem

The system must choose important items automatically while preserving auditable reasons for inclusion and exclusion.

## Scope

- Score Candidate Items using source trust, event impact, timeliness, corroboration, subscribed sections, and original-material availability.
- Detect duplicate or corroborating coverage with event keys or dedupe logic.
- Produce Selection Rationales for selected and excluded Candidate Items.
- Preserve Related History hooks for repeated or follow-up stories.
- Support low-confidence selected items without hiding uncertainty.

## Out of scope

- Complex recommendation models based on long-term user behavior.
- Full event lifecycle tracking or topic pages.
- Final Chinese briefing wording.

## Acceptance criteria

- Ranking can select and exclude items from golden samples with rationales.
- Duplicate coverage can be merged or treated as corroboration rather than separate push items.
- Low-confidence items retain rationale and confidence level for briefing generation.
- Excluded candidates are available for Archive Metadata.

## Test expectations

- Golden-sample tests for selected, excluded, duplicate coverage, low-confidence, academic, no-media, and source-media items.
- Tests assert rationale structure and source anchors, not exact prose.
- Regression test for duplicate Apple Intelligence sample behavior.

## Relevant docs

- `fixtures/golden-samples/items.json`
- `docs/briefing-style-guide.md`
- `docs/schemas/minimal-contracts.md`
- `docs/adr/0001-push-low-confidence-items-with-notices.md`

## Dependencies

- Live model-provider spike (#5) must prove the model can preserve rationale and confidence constraints before this becomes `ready-for-agent`.

## Triage label

`needs-triage`
