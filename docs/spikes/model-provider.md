# Model Provider Spike

Status: Prompt contract and fixture outputs ready; live provider call pending
Owner: Briefing Administrator

## Goal

Prove that the first Model Provider can generate structured briefing output from CandidateItems while preserving source anchors, selection rationale, confidence notices, and usage metadata.

## Inputs

- Minimal contracts: `docs/schemas/minimal-contracts.md`
- Golden samples: `fixtures/golden-samples/items.json`
- Briefing style guide: `docs/briefing-style-guide.md`

Fixture inputs and expected outputs:

- Prompt contract draft: `fixtures/model-provider/prompt-contract.md`
- High-confidence news output shape: `fixtures/model-provider/outputs/high-confidence-news.json`
- Low-confidence output shape: `fixtures/model-provider/outputs/low-confidence-news.json`
- Academic paper output shape: `fixtures/model-provider/outputs/academic-paper.json`
- Usage metadata shape: `fixtures/model-provider/usage-log.json`

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

- [ ] One high-confidence news item produces a valid BriefingItem from a live provider call.
- [ ] One low-confidence item produces a valid BriefingItem with Confidence Notice from a live provider call.
- [ ] One academic item produces a valid BriefingItem from a live provider call.
- [x] Fixture output references source anchors from inputs only.
- [x] Fixture output does not invent source media or citations.
- [x] Usage metadata shape is recorded for every model task.

## Evidence To Attach

- Prompt draft: `fixtures/model-provider/prompt-contract.md`.
- Structured output examples: `fixtures/model-provider/outputs/`.
- Usage metadata shape: `fixtures/model-provider/usage-log.json`.
- Pending: redacted live request and response examples.
- Pending: live notes on schema or style-guide changes required by model behavior.

## Current Finding

The model-provider boundary in ADR-0007 has enough fixture evidence to start live validation. The spike is not complete because `MODEL_PROVIDER`, `MODEL_DEFAULT_MODEL`, and `MODEL_API_KEY` are not configured in the current environment, so no real provider output, token usage, or latency evidence has been produced.
