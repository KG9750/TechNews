# MVP: Implement Archive Package creation and sync status

## Problem

Each daily run must produce a durable local archive and record sync status without losing the local output on remote failure.

## Scope

- Write `briefing.html`, `briefing.md`, `metadata.json`, and `media/` into a date/domain Archive Package.
- Persist selected items, excluded candidates, delivery status, media inventory, sync status, and model usage summary.
- Record local write success and remote sync success/failure.
- Preserve local-first behavior from ADR-0006.
- Prepare retry state for failed sync attempts.

## Out of scope

- Full retention policy automation.
- Historical search index.
- Direct cloud-only archive storage.

## Acceptance criteria

- A complete Archive Package can be written locally for a run.
- `metadata.json` validates against the implemented ArchiveMetadata model.
- Remote sync failure is recorded while local files remain readable.
- Successful sync to the configured target is recorded when `ARCHIVE_SYNC_TARGET` is available.

## Test expectations

- Unit tests for archive path construction and metadata serialization.
- Fixture test using `fixtures/archive-storage/local-archive/2026-06-01/technology/`.
- Failure-path test for unavailable sync target.
- Integration test against the real sync target before readiness completion.

## Relevant docs

- `docs/spikes/archive-storage.md`
- `fixtures/archive-storage/`
- `docs/adr/0006-local-first-archive-sync.md`
- `docs/schemas/minimal-contracts.md`

## Dependencies

- Archive/storage spike (#6) still needs real `ARCHIVE_SYNC_TARGET` success evidence.

## Triage label

`needs-triage`
