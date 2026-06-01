# GitHub Issue Breakdown

Status: Ready as issue-body drafts; live MVP issues must stay `needs-triage` until the readiness gate passes
Last updated: 2026-06-01

Use this breakdown to create GitHub issues after the remaining external spike evidence is available, or earlier as `needs-triage` placeholders if the maintainer wants the MVP backlog visible. Do not mark implementation issues `ready-for-agent` until the relevant blockers in each issue are cleared.

## Pre-Development Issues

| GitHub issue | Status | Relevant docs |
| --- | --- | --- |
| #2 Prepare minimum contracts | Closed | `docs/schemas/minimal-contracts.md` |
| #3 Run Feishu delivery spike | Open, `needs-info` | `docs/spikes/feishu-delivery.md`, `docs/secrets.md` |
| #4 Run source ingestion spike | Closed | `docs/spikes/source-ingestion.md`, `docs/source-registry.md` |
| #5 Run model provider spike | Open, `needs-info` | `docs/spikes/model-provider.md`, `fixtures/model-provider/` |
| #6 Run archive and storage spike | Open, `needs-info` | `docs/spikes/archive-storage.md`, `fixtures/archive-storage/` |
| #7 Review technology taxonomy and briefing style guide | Closed | `docs/taxonomy/technology-domain-template.md`, `docs/briefing-style-guide.md` |
| #8 Review golden samples | Closed | `fixtures/golden-samples/` |
| #9 Record required ADRs before MVP issue execution | Closed | `docs/adr/` |

## MVP Issue Drafts

Every draft below contains the required sections: Problem, Scope, Out of scope, Acceptance criteria, Test expectations, Relevant docs, Dependencies, and Triage label.

| Module | Draft | Initial label | Main blockers |
| --- | --- | --- | --- |
| Repo and CI | `docs/issues/mvp/01-repo-ci-foundation.md` | `needs-triage` | Readiness gate |
| Contracts | `docs/issues/mvp/02-contract-schemas.md` | `needs-triage` | Live model/archive/Feishu spike feedback |
| Taxonomy and source registry | `docs/issues/mvp/03-taxonomy-source-registry.md` | `needs-triage` | Source registry owner review |
| Source connectors | `docs/issues/mvp/04-source-connectors.md` | `needs-triage` | Source connector acceptance from source spike |
| Ranking and Selection Rationale | `docs/issues/mvp/05-ranking-selection-rationale.md` | `needs-triage` | Model provider spike |
| Briefing generation and Confidence Notices | `docs/issues/mvp/06-briefing-generation-confidence.md` | `needs-triage` | Model provider spike and Feishu card verification |
| Archive Package | `docs/issues/mvp/07-archive-package.md` | `needs-triage` | Archive sync target |
| Feishu delivery | `docs/issues/mvp/08-feishu-delivery.md` | `needs-triage` | Live Feishu delivery spike |
| Operations Console | `docs/issues/mvp/09-operations-console.md` | `needs-triage` | Storage and auth defaults confirmed |
| Deployment and secrets | `docs/issues/mvp/10-deployment-secrets.md` | `needs-triage` | Briefing Host paths and secrets |
| End-to-end MVP acceptance | `docs/issues/mvp/11-e2e-mvp-acceptance.md` | `needs-triage` | All core implementation issues |

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

If these drafts are created as GitHub issues before the readiness gate passes, add milestone `mvp` and label `needs-triage`. After #3, #5, and #6 have live evidence, each issue can be reviewed individually and only decision-complete issues should move to `ready-for-agent`.
