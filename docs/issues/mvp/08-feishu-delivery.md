# MVP: Implement Feishu delivery

## Problem

The MVP requires scheduled Push Briefing delivery to both Feishu users and Feishu groups.

## Scope

- Implement internal app bot delivery for user and group recipients.
- Render Push Briefings as the chosen Feishu card/message format.
- Preserve section headers, source links, Confidence Notices, and archive/deep-dive links.
- Record per-recipient delivery status and failure details.
- Keep custom group bot support only as a group-chat fallback if live spike evidence requires it.

## Out of scope

- Publishing to channels other than Feishu.
- Making custom group bot the primary path.
- Full message-interaction workflow beyond opening archive/deep-dive links.

## Acceptance criteria

- One real Feishu user receives the test Push Briefing.
- One real Feishu group receives the test Push Briefing.
- Delivery status is recorded per recipient.
- Failure responses can be stored without exposing secrets.
- ADR-0002 is accepted or superseded based on spike evidence.

## Test expectations

- Unit tests for card/message payload generation.
- Contract test against `fixtures/feishu-delivery/`.
- Live smoke test for one user and one group in the configured tenant.
- Failure-path test or recorded redacted failure example.

## Relevant docs

- `docs/spikes/feishu-delivery.md`
- `fixtures/feishu-delivery/`
- `docs/adr/0002-feishu-internal-app-bot-first.md`
- `docs/secrets.md`

## Dependencies

- Feishu delivery spike (#3) has live user/group delivery evidence recorded in ignored local evidence.

## Triage label

`ready-for-agent`
