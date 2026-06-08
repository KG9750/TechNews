# MVP: End-to-end acceptance run

## Problem

The MVP is only done when the whole daily briefing loop works from source collection through Feishu delivery and archive creation.

## Scope

- Run a complete Automatic Briefing Run on the Briefing Host.
- Use one source from each First-Version Source type.
- Enforce Delivery Deadline behavior when a connector is late or unavailable.
- Generate Push Briefing, Deep-Dive Detail, Archive Package, and Archive Metadata.
- Deliver to one Feishu user and one Feishu group.
- Show run, delivery, and sync status in the Operations Console.

## Out of scope

- Post-MVP social media connectors.
- AI chat.
- Full event lifecycle tracking.
- Multi-domain production rollout.

## Acceptance criteria

- The MVP acceptance checklist in `docs/MVP-SCOPE.md` passes end to end.
- The same run id ties together Candidate Items, Briefing Items, Archive Metadata, model usage, and delivery status.
- A low-confidence item appears with a Confidence Notice.
- Source Media attribution appears when source media exists.
- A no-media item uses a non-misleading structured fallback.
- Local archive exists and remote sync status is recorded.

## Test expectations

- Automated e2e or scripted acceptance test where practical.
- Manual smoke evidence for real Feishu delivery and real archive sync.
- Fixture-backed tests for deterministic paths.
- Record all external evidence in redacted form.

## Relevant docs

- `docs/MVP-SCOPE.md`
- `docs/PRD.md`
- `docs/PRE-DEVELOPMENT-PLAN.md`
- `docs/ARCHITECTURE-NOTES.md`
- `docs/schemas/minimal-contracts.md`

## Dependencies

- All core MVP implementation issues are complete.
- Readiness live evidence is complete.

## Triage label

`ready-for-agent`
