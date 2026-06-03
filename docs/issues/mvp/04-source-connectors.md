# MVP: Implement first-version source connectors

## Problem

The MVP needs reliable ingestion from controlled source types without global crawling or full text storage.

## Scope

- Implement public feed/RSS ingestion.
- Implement academic source ingestion for arXiv-style metadata.
- Implement manual URL metadata ingestion.
- Normalize every source result into `CandidateItem`.
- Record connector status, failures, timeouts, and late connector behavior.
- Respect source eligibility notes, conservative rate limits, and metadata-only storage.
- Load `fixtures/source-ingestion/source-access-policy.json` and prevent `needs_review` sources from production auto-ingestion.

## Out of scope

- X, Facebook, LinkedIn, commercial news APIs, and global web crawling.
- Saving complete article bodies by default.
- Ranking or briefing generation.

## Acceptance criteria

- At least one source from each First-Version Source type produces normalized Candidate Items.
- Connector failures are recorded and do not abort the whole run.
- Late connectors can be cut off at the Delivery Deadline.
- Candidate Items preserve Original Source Anchors and do not store complete copyrighted article bodies.
- Sources with `production_auto_ingestion: false` are skipped, probe-only, or manual-only according to their policy row.

## Test expectations

- Unit tests with fixture feed/API/manual URL inputs.
- Integration-style test using recorded metadata fixtures where network is not required.
- Test for timeout/late connector behavior.
- Validation against `fixtures/source-ingestion/candidate-items.json`.

## Relevant docs

- `docs/spikes/source-ingestion.md`
- `docs/source-registry.md`
- `docs/source-eligibility-checklist.md`
- `fixtures/source-ingestion/source-access-policy.json`
- `docs/schemas/minimal-contracts.md`

## Dependencies

- Source ingestion spike is complete, but implementation should still wait for readiness gate approval.

## Triage label

`needs-triage`
