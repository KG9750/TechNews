# MVP: Implement Operations Console

## Problem

The Briefing Administrator needs a lightweight private console to configure and observe the daily briefing system.

## Scope

- Add single-admin login using username, password hash, and signed sessions.
- Show source configuration and connector health.
- Show taxonomy, recipient whitelist, recipient subscriptions, and Delivery Deadline configuration.
- Show current and historical run status, delivery status, sync status, and archive links.
- Provide retry entry points for failed delivery or sync where the underlying service supports retry.

## Out of scope

- Full reader-facing web app.
- Multi-user roles, SSO, or OAuth.
- AI chat or rich analytics dashboards.

## Acceptance criteria

- Console access is protected by the single Briefing Administrator model.
- Admin can view and edit first-version configuration needed for a run.
- Admin can inspect run status, source health, selected/excluded item summaries, delivery status, and archive links.
- Secrets are not displayed in plaintext.

## Test expectations

- Unit tests for auth/session behavior and secret redaction.
- View/controller tests for key console pages.
- Integration test with seeded SQLite data.
- Manual smoke test on the Briefing Host deployment.

## Relevant docs

- `docs/adr/0005-sqlite-operational-store.md`
- `docs/adr/0008-single-admin-console-access.md`
- `docs/ARCHITECTURE-NOTES.md`
- `docs/secrets.md`

## Dependencies

- Storage schema from contracts issue.
- Deployment and secrets issue for host configuration.

## Triage label

`needs-triage`
