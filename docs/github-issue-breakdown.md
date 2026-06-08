# GitHub Issue Breakdown

Status: Readiness gate passed; MVP issues ready for post-readiness triage
Last updated: 2026-06-08

Use this breakdown to keep GitHub issue labels aligned after the readiness gate. The external spike blockers are complete, source-owner narrowing is applied, and decision-complete implementation issues can move to `ready-for-agent`.

## Pre-Development Issues

| GitHub issue | Status | Relevant docs |
| --- | --- | --- |
| #2 Prepare minimum contracts | Closed | `docs/schemas/minimal-contracts.md` |
| #3 Run Feishu delivery spike | Ready to close after copy-safe update | `docs/spikes/feishu-delivery.md`, `docs/secrets.md` |
| #4 Run source ingestion spike | Closed | `docs/spikes/source-ingestion.md`, `docs/source-registry.md` |
| #5 Run model provider spike | Ready to close after copy-safe update | `docs/spikes/model-provider.md`, `fixtures/model-provider/` |
| #6 Run archive and storage spike | Ready to close after copy-safe update | `docs/spikes/archive-storage.md`, `fixtures/archive-storage/` |
| #7 Review technology taxonomy and briefing style guide | Closed | `docs/taxonomy/technology-domain-template.md`, `docs/briefing-style-guide.md` |
| #8 Review golden samples | Closed | `fixtures/golden-samples/` |
| #9 Record required ADRs before MVP issue execution | Closed | `docs/adr/` |
| #21 Resolve source owner eligibility approvals | Ready to close after copy-safe update | `docs/source-owner-review-runbook.md`, `fixtures/source-ingestion/source-owner-review-queue.json` |

## MVP Issue Drafts

Every draft below contains the required sections: Problem, Scope, Out of scope, Acceptance criteria, Test expectations, Relevant docs, Dependencies, and Triage label.
`python3 scripts/check_readiness.py` verifies this mapping, the required draft sections, relevant doc paths, dependency sections, post-readiness labels, and the acceptance coverage map.
Use `python3 scripts/readiness_action_packet.py --write-mvp-issue-packets` to generate ignored per-issue triage packets under `evidence/mvp-issue-packets/` before changing any MVP issue label.

Issues #10, #11, #12, #13, #14, #15, and #16 are implemented and closed by PRs #24, #26, #28, #30, #32, #34, and #36. Issues #17 through #19 remain `ready-for-agent`; issue #20 remains `needs-triage` until core MVP implementation completes.

| Module | GitHub issue | Draft | Initial label | Main blockers |
| --- | --- | --- | --- | --- |
| Repo and CI | #10 | `docs/issues/mvp/01-repo-ci-foundation.md` | `ready-for-agent` | None after readiness gate |
| Contracts | #11 | `docs/issues/mvp/02-contract-schemas.md` | `ready-for-agent` | Live model/archive/Feishu spike feedback incorporated |
| Taxonomy and source registry | #12 | `docs/issues/mvp/03-taxonomy-source-registry.md` | `ready-for-agent` | Source owner approvals (#21) resolved by narrowing |
| Source connectors | #13 | `docs/issues/mvp/04-source-connectors.md` | `ready-for-agent` | Source owner approvals (#21), source-owner narrowing, and source access policy applied |
| Ranking and Selection Rationale | #14 | `docs/issues/mvp/05-ranking-selection-rationale.md` | `ready-for-agent` | Model provider spike complete |
| Briefing generation and Confidence Notices | #15 | `docs/issues/mvp/06-briefing-generation-confidence.md` | `ready-for-agent` | Model provider and Feishu evidence complete |
| Archive Package | #16 | `docs/issues/mvp/07-archive-package.md` | `ready-for-agent` | Archive sync evidence complete |
| Feishu delivery | #17 | `docs/issues/mvp/08-feishu-delivery.md` | `ready-for-agent` | Live Feishu delivery spike complete |
| Operations Console | #18 | `docs/issues/mvp/09-operations-console.md` | `ready-for-agent` | Storage and auth defaults confirmed |
| Deployment and secrets | #19 | `docs/issues/mvp/10-deployment-secrets.md` | `ready-for-agent` | Runtime input names and secret surfaces confirmed |
| End-to-end MVP acceptance | #20 | `docs/issues/mvp/11-e2e-mvp-acceptance.md` | `needs-triage` | All core implementation issues |

## Acceptance Coverage Map

| MVP acceptance item | Primary issue draft |
| --- | --- |
| Configure one source in each First-Version Source type | `04-source-connectors`, `03-taxonomy-source-registry` |
| Run complete Automatic Briefing Run to Feishu delivery | `11-e2e-mvp-acceptance` |
| Late Source Connector does not block Delivery Deadline | `04-source-connectors`, `11-e2e-mvp-acceptance` |
| Push Briefing reaches one Feishu user and one Feishu group | `08-feishu-delivery`, `11-e2e-mvp-acceptance` |
| Produce Archived Briefing for the same run | `07-archive-package`, `11-e2e-mvp-acceptance` |
| Open Deep-Dive Detail from an archived item | `06-briefing-generation-confidence`, `07-archive-package` |
| Show low-confidence item with Confidence Notice | `06-briefing-generation-confidence` |
| Show Source Media with attribution when available | `06-briefing-generation-confidence`, `07-archive-package` |
| Show item without source media using structured fallback | `06-briefing-generation-confidence` |
| Show Related History for a repeated or follow-up item | `05-ranking-selection-rationale`, `06-briefing-generation-confidence` |
| Show run status and delivery status in Operations Console | `09-operations-console` |

## Creation Rule

After the readiness gate passes, #10 through #19 can move to `ready-for-agent`. Keep #20 as `needs-triage` until the core MVP implementation issues are complete.
The ignored MVP issue triage packets are comment-ready context only; they do not replace `python3 scripts/check_readiness.py --require-live --require-evidence` or `python3 scripts/check_readiness.py --require-github`.
