# Model Provider Spike

Status: Not started
Owner: Briefing Administrator

## Goal

Prove that the first Model Provider can generate structured briefing output from CandidateItems while preserving source anchors, selection rationale, confidence notices, and usage metadata.

## Inputs

- Minimal contracts: `docs/schemas/minimal-contracts.md`
- Golden samples: `fixtures/golden-samples/items.json`
- Briefing style guide: `docs/briefing-style-guide.md`

## Required Tasks

- Classify CandidateItems into Briefing Sections and Section Subcategories.
- Generate Chinese one-sentence titles.
- Generate three to four concise Chinese bullets.
- Produce Selection Rationales.
- Produce Confidence Notices when confidence is medium or low.
- Preserve Original Source Anchors.
- Avoid invented source media, citations, or article facts.

## Usage Metadata

Record at minimum:

- `run_id`
- provider and model name
- task type
- request count
- token usage when available
- latency
- failure reason when present

This is observability only. It does not introduce budget caps or automatic low-cost mode.

## Verification Checklist

- One high-confidence news item produces a valid BriefingItem.
- One low-confidence item produces a valid BriefingItem with Confidence Notice.
- One academic item produces a valid BriefingItem.
- Output references source anchors from inputs only.
- Output does not invent source media or citations.
- Usage metadata is recorded for every model task.

## Evidence To Attach

- Prompt draft.
- Redacted request and response examples.
- Structured output examples.
- Notes on schema or style-guide changes required by the model behavior.
