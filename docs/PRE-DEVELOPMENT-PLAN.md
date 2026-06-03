# Pre-Development Plan

Status: Draft
Last updated: 2026-06-03

This plan replaces the earlier preparation plan. Its main correction is ordering: define the minimum contracts first, then run Feishu, source, model, and archive spikes against those contracts. Implementation work must not start until the readiness gate passes.

## Readiness Goal

Start product implementation only after the project has:

- A committed and pushed documentation baseline in `KG9750/TechNews`.
- GitHub labels, milestones, and a pre-development tracking issue.
- Minimum contracts for `CandidateItem`, `BriefingItem`, `ArchiveMetadata`, and `BriefingRun`.
- Feishu delivery path proven for one real user and one real group.
- First-Version Sources listed, classified, and checked for source eligibility.
- Technology Domain Template and briefing style guide drafted.
- Golden samples covering at least 20 real-world items without storing full article bodies.
- Secrets inventory and `.env.example` in place.
- ADRs recorded for hard-to-reverse choices before MVP issues are marked agent-ready.

## Phase 0: Repository Baseline

Purpose: make the planning work durable before external setup begins.

Tasks:

- Confirm `gh auth status` succeeds for an account with push and issue-management access.
- Confirm `git remote -v` points to `KG9750/TechNews` through a canonical HTTPS or SSH remote URL.
- Commit `AGENTS.md`, `CONTEXT.md`, docs, ADRs, schemas, spike templates, source registry, and fixtures.
- Push the baseline to GitHub.
- Create labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.
- Create milestones: `pre-development`, `mvp`, `post-mvp`.
- Create a pre-development tracking issue linking this plan and the PRD.

Verification:

- `git status` is clean after commit and push.
- The GitHub repo contains the pushed baseline.
- Labels and milestones exist.
- The tracking issue links to `docs/PRE-DEVELOPMENT-PLAN.md` and `docs/PRD.md`.
- `python3 scripts/check_readiness.py --require-github` passes when run by a maintainer with `gh` access, confirming auth, origin remote, default branch, push-capable permission, labels, milestones, and tracker issue state.

## Phase 1: Minimum Contracts First

Purpose: remove schema-ordering risk before integration spikes.

Deliverable:

- `docs/schemas/minimal-contracts.md`

Required coverage:

- `CandidateItem`: source anchor, source type, original title, URL, timestamps, source metadata, section hints, source media, and eligibility state.
- `BriefingItem`: selected candidate reference, title, bullets, section/subcategory, confidence notice, selection rationale, original source anchor, media attribution, and related history.
- `ArchiveMetadata`: run id, generated files, selected/excluded candidates, delivery status, media inventory, sync status, and model usage summary.
- `BriefingRun`: run id, delivery deadline, connector status, model task status, archive status, Feishu delivery status, and run-level warnings.

Verification:

- Feishu, model, and archive spike templates all reference the same contract file.
- The contracts include run id, delivery status, confidence notice, selection rationale, source anchor, media attribution, and usage metadata.
- `python3 scripts/check_readiness.py` verifies the required contract sections, core fields, and spike references.

## Phase 2: Risk Spikes

Purpose: prove external dependencies before product code is built around them.

Final live evidence for these spikes must include `evidence/readiness-manifest.json`, declaring the Feishu, model-provider, and archive-storage evidence files and matching live model/archive run metadata.

### Feishu Delivery Spike

Default:

- Use a Feishu internal app bot as the primary MVP delivery path.
- Treat a custom group bot only as a group-chat fallback.
- Personal delivery and group delivery are both MVP requirements.

Deliverables:

- `docs/spikes/feishu-delivery.md`
- Proposed or accepted ADR for the Feishu delivery path.
- Minimal throwaway script or request collection kept outside product code.

Verification:

- A test Push Briefing reaches one real Feishu user.
- A test Push Briefing reaches one real Feishu group.
- The message includes section headers, at least one source link, and one confidence notice.
- Recipient identifiers, scopes, app permissions, rate limits, and failure responses are documented.

Official references:

- Feishu send message API: https://open.feishu.cn/document/server-docs/im-v1/message/create?lang=zh-CN
- Feishu card sending guide: https://open.feishu.cn/document/feishu-cards/send-feishu-card
- Message card OpenAPI reference: https://open.larksuite.com/document/common-capabilities/message-card/api-and-resource-reference

### Source Ingestion Spike

Deliverables:

- `docs/spikes/source-ingestion.md`
- `docs/source-registry.md`
- `docs/source-eligibility-checklist.md`
- Normalized sample Candidate Items for RSS/public feeds, academic sources, and manual URLs.

Verification:

- At least one source from each First-Version Source type produces a normalized Candidate Item.
- Source registry contains at least 30 seed sources.
- Every source is marked first-version or deferred.
- Every first-version source has an eligibility note covering access method, summary/storage limits, media use, rate limit, and disallowed behavior.

Official references:

- arXiv API access: https://info.arxiv.org/help/api/index.html
- arXiv API user manual: https://info.arxiv.org/help/api/user-manual.html

### Model Provider Spike

Deliverables:

- `docs/spikes/model-provider.md`
- Prompt and structured-output contract draft.
- Three model-output examples: high-confidence news, low-confidence news, and academic paper.

Verification:

- Output includes Original Source Anchor, Selection Rationale, Confidence Notice when needed, and no invented media/citations.
- The spike records run id, model name, task type, request count, token usage when available, latency, and failure reason.
- No budget cap is introduced; this is observability, not cost control.

### Archive and Storage Spike

Deliverables:

- `docs/spikes/archive-storage.md`
- Example Archive Package folder shape.
- Recommended local path and NAS/cloud sync method.

Verification:

- A sample Archive Package can be written locally.
- The package can be copied or synced to the target storage.
- Sync failure can be recorded without losing the local archive.

### Secrets Preparation

Deliverables:

- `.env.example`
- `docs/secrets.md`
- `.gitignore` rules preventing real secret files from being committed.

Verification:

- Every required secret has a variable name, purpose, owner, and setup note.
- No real secrets are stored in the repo.
- `python3 scripts/check_readiness.py` verifies `.env.example`, `docs/secrets.md`, and `.gitignore` stay aligned.

## Phase 3: Product Inputs

Purpose: create the product fixtures that implementation and tests will use.

Deliverables:

- `docs/taxonomy/technology-domain-template.md`
- `docs/briefing-style-guide.md`
- `fixtures/golden-samples/README.md`
- `fixtures/golden-samples/items.json`

Verification:

- Every MVP Briefing Section has at least three Section Subcategories.
- Embodied intelligence includes robot body, data collection, model training, recent papers, and financing.
- Golden samples cover at least 20 real-world items.
- Golden samples include duplicate coverage, low-confidence content, academic papers, items without source media, and items with source media.
- Golden samples store metadata and expected outputs only, not full copyrighted article bodies.

## Phase 4: ADRs Before MVP Issues

Purpose: avoid marking implementation work agent-ready while hard-to-reverse choices are still open.

ADR candidates required before MVP issues become `ready-for-agent`:

- Application stack and runtime.
- Briefing Host and deployment target.
- Feishu delivery path.
- Operational data storage.
- Archive Package sync strategy.
- Model Provider abstraction boundary.
- Operations Console access approach.

Verification:

- Each ADR records a real tradeoff and a decision.
- `docs/ARCHITECTURE-NOTES.md` is updated if an ADR changes the system shape.
- MVP implementation issues are not marked `ready-for-agent` until the relevant ADRs exist.
- `python3 scripts/check_readiness.py` verifies required ADR tradeoffs, consequences, decision keywords, and architecture defaults.

## Phase 5: GitHub Issue Breakdown

Purpose: turn the preparation work and MVP into trackable GitHub issues.

Issue groups:

- Repo and CI.
- Minimum contracts.
- Taxonomy and source registry.
- Source connectors.
- Editorial Importance and Selection Rationale.
- Briefing generation and style guide compliance.
- Confidence Notice handling.
- Archive Package creation.
- Feishu delivery.
- Operations Console.
- Deployment and secrets.
- End-to-end MVP acceptance test.

Every issue must include:

- Problem.
- Scope.
- Out of scope.
- Acceptance criteria.
- Test expectations.
- Relevant docs.
- Dependencies.
- Triage label.

Verification:

- Every MVP acceptance checklist item maps to at least one issue.
- `python3 scripts/check_readiness.py` verifies the 11 MVP issue-body drafts, required sections, relevant doc paths, dependency sections, `needs-triage` labels, and acceptance coverage map.
- Issues with unresolved ADR dependencies stay `needs-triage`.
- Only decision-complete issues receive `ready-for-agent`.
- `python3 scripts/check_readiness.py --require-github` confirms MVP issues #10-#20 remain `needs-triage` until the readiness gate passes.

## Development Readiness Gate

Formal implementation can begin only when:

- Baseline docs are pushed.
- GitHub labels, milestones, and pre-development tracking issue exist.
- Minimum contracts exist.
- Feishu delivery spike passes for one user and one group.
- Source ingestion spike normalizes at least one source from every First-Version Source type.
- Archive/storage spike passes.
- Model Provider spike passes structured output and usage metadata checks.
- Technology Domain Template and briefing style guide are drafted.
- Source registry contains at least 30 seed sources.
- Golden samples cover at least 20 items.
- Required ADRs exist.
- MVP issue breakdown exists and is labeled.

## First Execution Sequence

1. Commit and push the documentation baseline.
2. Create GitHub labels, milestones, and the pre-development tracking issue.
3. Review minimum contracts.
4. Run the Feishu delivery spike.
5. Run the source ingestion spike.
6. Run the model provider spike.
7. Run the archive/storage spike.
8. Review taxonomy, style guide, and golden samples.
9. Write the required ADRs.
10. Create and label MVP implementation issues.
