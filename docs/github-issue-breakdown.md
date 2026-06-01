# GitHub Issue Breakdown

Status: Draft
Last updated: 2026-06-01

Use this breakdown after the baseline is pushed. Issues that still depend on external credentials, spike results, or ADRs should stay `needs-triage`.

## Pre-Development Issues

| Title | Milestone | Label | Relevant docs |
| --- | --- | --- | --- |
| Prepare minimum contracts for briefing spikes | pre-development | ready-for-agent | `docs/schemas/minimal-contracts.md` |
| Run Feishu delivery spike | pre-development | needs-info | `docs/spikes/feishu-delivery.md`, `docs/secrets.md` |
| Run source ingestion spike | pre-development | ready-for-agent | `docs/spikes/source-ingestion.md`, `docs/source-registry.md` |
| Run model provider spike | pre-development | needs-info | `docs/spikes/model-provider.md`, `docs/secrets.md` |
| Run archive and storage spike | pre-development | needs-info | `docs/spikes/archive-storage.md`, `docs/secrets.md` |
| Review technology taxonomy and briefing style guide | pre-development | ready-for-human | `docs/taxonomy/technology-domain-template.md`, `docs/briefing-style-guide.md` |
| Review golden samples | pre-development | ready-for-human | `fixtures/golden-samples/items.json` |
| Record required ADRs before MVP issue execution | pre-development | needs-triage | `docs/PRE-DEVELOPMENT-PLAN.md` |

## MVP Implementation Issue Groups

Create these after the readiness gate passes and relevant ADRs exist.

| Group | Initial label | Blocking inputs |
| --- | --- | --- |
| Repo and CI | needs-triage | Application stack ADR |
| Source connectors | needs-triage | Source ingestion spike |
| Candidate normalization and deduplication | needs-triage | Minimal contracts, source spike |
| Editorial Importance and Selection Rationale | needs-triage | Golden samples, model spike |
| Briefing generation | needs-triage | Style guide, model spike |
| Confidence Notice handling | needs-triage | ADR-0001, model spike |
| Archive Package creation | needs-triage | Archive/storage spike |
| Feishu delivery | needs-triage | Feishu spike, ADR-0002 |
| Operations Console | needs-triage | Console access ADR, storage ADR |
| Deployment and secrets | needs-triage | Host/deployment ADR, secrets doc |
| End-to-end MVP acceptance | needs-triage | All core implementation issues |

## Required Issue Body Sections

Every issue should contain:

- Problem
- Scope
- Out of scope
- Acceptance criteria
- Test expectations
- Relevant docs
- Dependencies
