# MVP: Convert minimum contracts into application schemas

## Problem

The current minimum contracts are documented in markdown, but implementation needs executable schemas or models for validation.

## Scope

- Convert `CandidateItem`, `BriefingItem`, `ArchiveMetadata`, and `BriefingRun` into Python data models.
- Preserve field names and required/optional status from the minimum contracts.
- Add validation for confidence notices, source anchors, media attribution, delivery status, sync status, and model usage metadata.
- Export JSON Schema if needed for fixtures or future non-Python clients.

## Out of scope

- Changing product semantics without updating `docs/schemas/minimal-contracts.md`.
- Building source connectors, model provider adapters, or Feishu dispatchers.

## Acceptance criteria

- Existing source-ingestion, model-provider, archive-storage, and Feishu fixtures can be validated or intentionally mapped to the models.
- Low or medium confidence `BriefingItem` without `confidence_notice` fails validation.
- Source media displayed without `media_attribution` fails validation.
- Sync and delivery failures can be represented without relying only on logs.

## Test expectations

- Unit tests for required fields and cross-field rules.
- Fixture validation against `fixtures/source-ingestion/`, `fixtures/model-provider/`, `fixtures/archive-storage/`, and `fixtures/feishu-delivery/`.
- Regression test for no full article body field in `CandidateItem`.

## Relevant docs

- `docs/schemas/minimal-contracts.md`
- `docs/spikes/source-ingestion.md`
- `docs/spikes/model-provider.md`
- `docs/spikes/archive-storage.md`
- `docs/spikes/feishu-delivery.md`

## Dependencies

- Live spike feedback from #3, #5, and #6 has been captured; keep schema adjustments scoped to implementation findings.

## Triage label

`ready-for-agent`
