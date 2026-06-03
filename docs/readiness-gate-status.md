# Development Readiness Gate Status

Status: Not passed
Last updated: 2026-06-03

This file is the current audit trail for the readiness gate in `docs/PRE-DEVELOPMENT-PLAN.md`. It records evidence that has been verified and the remaining evidence required before formal MVP implementation issues can move out of `needs-triage`.

## Gate Summary

The repository is ready for live external validation, but not ready for product implementation. The remaining blockers are:

- Feishu delivery spike: needs real internal app bot delivery to one user and one group.
- Model Provider spike: needs one real provider/model call set with usage metadata.
- Archive/storage spike: needs real `ARCHIVE_SYNC_TARGET` success evidence.

Additional review item:

- Source eligibility: 32 first-version seed sources are covered in `docs/source-eligibility-reviews.md`; all first-version sources now have source-specific evidence or per-URL review rules recorded, and `scripts/check_readiness.py` rejects generic terms-evidence placeholders. `fixtures/source-ingestion/source-access-policy.json` now mirrors those review states for implementation: 7 metadata-only sources are production-enabled, and 25 public/company/manual sources remain locked out of production auto-ingestion while `needs_review`. Those 25 open decisions are tracked in `fixtures/source-ingestion/source-owner-review-queue.json`, governed by `docs/source-owner-review-runbook.md`, and supported by `scripts/source_owner_review_decision.py` for ignored single-source or batch decision drafts with current artifact context, ignored Markdown review packets, packet index and consolidated worksheet for owner context, read-only draft status reporting, non-destructive context refresh in existing drafts, single-source or batch completed-decision validation, and single-source or batch application to tracked artifacts.

The live spike evidence procedure is now documented in `docs/live-spike-evidence-runbook.md`. Template evidence files live under `fixtures/live-evidence-templates/`; they are examples only, and `scripts/check_readiness.py` rejects any live evidence that still contains `TEMPLATE_` placeholders or common sensitive leak patterns. Final live evidence must also include `evidence/readiness-manifest.json`, which declares the evidence set and checks model/archive run metadata consistency; `scripts/spikes/readiness_manifest.py` generates that manifest from the redacted evidence files. `scripts/spikes/live_readiness_preflight.py` provides a one-command preflight that runs local helper dry-runs, reports missing environment variable names, lists missing evidence files, and can write an ignored Markdown execution packet without printing secret values. `scripts/readiness_action_packet.py` then links the live packet, readiness-manifest blocker, GitHub issue links, source-owner review index, and source-owner worksheet into one ignored top-level execution packet. A synthetic leaky fixture under `fixtures/live-evidence-negative/leaky-feishu/` proves the redaction scanner fails unsafe evidence. The Feishu spike runner also redacts common sensitive response keys and values before writing evidence, and readiness verifies that recipient ids are scrubbed while `receive_id_type` remains reviewable.

Pre-development readiness is also protected in GitHub Actions by `.github/workflows/pre-development-readiness.yml`. The workflow uses Node 24-native GitHub actions, runs the local readiness checker, compiles the readiness/spike scripts, and proves the tracked evidence templates cannot pass as live evidence. It intentionally does not require live external credentials.

The GitHub issue tracker gate is checked manually because it requires `gh` access. Run it from this checkout with:

```bash
python3 scripts/check_readiness.py --require-github
```

This verifies GitHub auth, origin remote identity, default branch, push-capable permission, required triage labels, milestones, pre-development issues, and MVP issue labels. The default CI workflow intentionally does not require this external access.

Local evidence can be checked with:

```bash
python3 scripts/check_readiness.py
```

To make missing external variables fail the check before a live spike, run:

```bash
python3 scripts/check_readiness.py --require-live
```

To make missing or invalid redacted live evidence fail the check after live spikes, run:

```bash
python3 scripts/check_readiness.py --require-evidence
```

For the final readiness gate, require both environment variables and redacted evidence:

```bash
python3 scripts/check_readiness.py --require-live --require-evidence
```

The checker may also print `REVIEW` notes. These are not local fixture failures, but they identify items that must not be treated as fully production-ready. For example, first-version seed sources still need source-by-source eligibility review before automated ingestion.

## Requirement Status

| Requirement | Status | Evidence | Remaining gap |
| --- | --- | --- | --- |
| Baseline docs are committed and pushed | Passed | Baseline commit `6fa77b1`; current `main` is verified by the latest Pre-development readiness CI and optional GitHub tracker gate | None |
| GitHub repo access, labels, milestones, and tracking issue exist | Passed | `--require-github` verifies `gh auth status`, origin remote identity, default branch `main`, push-capable repo permission, labels, milestones, and tracking issue #1 | None |
| Pre-development readiness CI exists | Passed | `.github/workflows/pre-development-readiness.yml`; `scripts/check_readiness.py` verifies Node 24-native action versions, workflow coverage, secrets inventory alignment, live evidence helper coverage, and local fixtures | None |
| Minimum contracts exist | Passed | `docs/schemas/minimal-contracts.md`; readiness verifies required contract sections, core fields, guardrail rules, and spike references; issue #2 closed | None |
| Feishu delivery spike passes for one user and one group | Blocked | Fixtures in `fixtures/feishu-delivery/`; live evidence template in `fixtures/live-evidence-templates/feishu-delivery/`; issue #3 open `needs-info` | Need Feishu app credentials, user open_id, group chat_id, live send evidence under `evidence/feishu-delivery/` |
| Source ingestion spike normalizes every First-Version Source type | Passed | `docs/spikes/source-ingestion.md`; `fixtures/source-ingestion/candidate-items.json`; issue #4 closed | None |
| Archive/storage spike passes | Blocked | Local archive fixture in `fixtures/archive-storage/`; live evidence template in `fixtures/live-evidence-templates/archive-storage/`; issue #6 open `needs-info` | Need real NAS/cloud sync target success evidence under `evidence/archive-storage/` |
| Model Provider spike passes structured output and usage metadata checks | Blocked | Prompt/output fixtures in `fixtures/model-provider/`; live evidence template in `fixtures/live-evidence-templates/model-provider/`; issue #5 open `needs-info` | Need live provider/model, redacted outputs, token/latency/failure metadata under `evidence/model-provider/` |
| Live evidence runbook and template-negative gate exist | Passed | `docs/live-spike-evidence-runbook.md`; `scripts/spikes/live_readiness_preflight.py`; `scripts/spikes/readiness_manifest.py`; `scripts/readiness_action_packet.py`; `scripts/test_live_evidence_helpers.py`; `scripts/test_readiness_action_packet.py`; `fixtures/live-evidence-templates/`; `fixtures/live-evidence-templates/readiness-manifest.json`; `fixtures/live-evidence-negative/leaky-feishu/`; `scripts/check_readiness.py --require-evidence --evidence-root fixtures/live-evidence-templates` fails on `TEMPLATE_` placeholders; live evidence scans for common token/id/path leaks and raw sensitive environment values; preflight reports missing env/evidence and writes a Markdown execution packet without secret values; the top-level action packet links live evidence, readiness manifest, GitHub issue links, source owner review index, worksheet, and source owner review state; final evidence manifest checks declared files and model/archive run metadata; Feishu runner redaction, helper regressions, and a synthetic redacted positive evidence package are covered by readiness | None |
| Technology Domain Template and briefing style guide are drafted | Passed | `docs/taxonomy/technology-domain-template.md`; `docs/briefing-style-guide.md`; readiness verifies MVP sections, Embodied Intelligence subcategories, Push Briefing structure, confidence notices, source/media rules, and Deep-Dive Detail rules; issue #7 closed | None |
| Source registry contains at least 30 seed sources | Passed | `docs/source-registry.md`; 37 total seed sources, 32 first-version, 5 deferred | None |
| Source eligibility review covers first-version seed sources | Review | `docs/source-eligibility-reviews.md`; `fixtures/source-ingestion/source-access-policy.json`; `fixtures/source-ingestion/source-owner-review-queue.json`; `docs/source-owner-review-runbook.md`; `scripts/source_owner_review_decision.py`; `scripts/test_source_owner_review_decision.py`; 32 first-version sources covered, 7 `eligible`, 25 `needs_review`; readiness checks that `needs_review` sources have `production_auto_ingestion: false` and exactly one open owner review queue item, and that owner decisions have read-only status reporting, context-rich single-source draft, context-rich batch draft, ignored Markdown review packets, index and worksheet, non-destructive context refresh, single-source validation, batch validation, single-source apply, and batch apply tooling with regression tests | Owner must complete source-specific terms/media/rate-limit review before automated production ingestion for `needs_review` sources |
| Golden samples cover at least 20 real-world items | Passed | `fixtures/golden-samples/items.json`; 22 total fixtures, 21 real-world items; issue #8 closed | None |
| Required ADRs exist | Passed | 8 ADRs in `docs/adr/`; readiness verifies 7 required architecture ADRs for status, tradeoffs, consequences, decision keywords, and matching `docs/ARCHITECTURE-NOTES.md` defaults; issue #9 closed | None |
| MVP issue breakdown exists and is labeled | Passed | `docs/github-issue-breakdown.md`; `docs/issues/mvp/`; readiness verifies 11 mapped drafts, required sections, relevant doc paths, dependency sections, `needs-triage` labels, and acceptance coverage map; GitHub issues #10, #11, #12, #13, #14, #15, #16, #17, #18, #19, and #20 created with milestone `mvp` and label `needs-triage`; `--require-github` verifies none are marked `ready-for-agent` before readiness passes | None |

## External Inputs Needed

To finish the gate, provide these values in the deployment environment or secure local test environment. Do not commit them.

Use `docs/live-spike-evidence-runbook.md` for the exact commands, redaction rules, evidence layouts, and final gate command. Copy templates from `fixtures/live-evidence-templates/` only as a starting point; every `TEMPLATE_` placeholder must be replaced or the checker will fail.

Before live execution, run:

```bash
python3 scripts/spikes/live_readiness_preflight.py --dry-run --write-packet
python3 scripts/readiness_action_packet.py
```

After credentials and redacted evidence are configured, run:

```bash
python3 scripts/spikes/live_readiness_preflight.py --strict --write-packet
```

### Evidence Manifest

- `evidence/readiness-manifest.json`

This manifest must declare the Feishu, model-provider, and archive-storage evidence files. It must also match the Model Provider run id/provider/model in `evidence/model-provider/usage-log.json` and the Archive/storage run id in `evidence/archive-storage/sync-result.json`.

Generate it after all live evidence files are present:

```bash
python3 scripts/spikes/readiness_manifest.py
```

### Feishu

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_TENANT_KEY`, if required by the app setup
- `FEISHU_DEFAULT_USER_OPEN_ID`
- `FEISHU_DEFAULT_CHAT_ID`

Dry-run before live send:

```bash
python3 scripts/spikes/feishu_delivery_spike.py --dry-run
```

Live command after credentials are configured:

```bash
python3 scripts/spikes/feishu_delivery_spike.py
```

Required evidence:

- Redacted successful send response for one user.
- Redacted successful send response for one group.
- Rendered Feishu message text or screenshot.
- Scopes, permissions, recipient id type, rate/message-size notes, and any failure response shape.

Expected evidence files:

- `evidence/feishu-delivery/user-response.redacted.json`
- `evidence/feishu-delivery/group-response.redacted.json`
- `evidence/feishu-delivery/rendered-message.md`

### Model Provider

- `MODEL_PROVIDER`
- `MODEL_DEFAULT_MODEL`
- `MODEL_API_KEY`

Dry-run before live model calls:

```bash
python3 scripts/spikes/model_provider_spike.py --dry-run
```

Validate redacted live evidence after calls are made with the chosen provider:

```bash
python3 scripts/spikes/model_provider_spike.py --validate-evidence
```

Required evidence:

- Redacted request/response for high-confidence news, low-confidence news, and academic paper examples.
- Provider/model name.
- Request count, token usage when available, latency, and failure reason when present.

Expected evidence files:

- `evidence/model-provider/outputs/high-confidence-news.json`
- `evidence/model-provider/outputs/low-confidence-news.json`
- `evidence/model-provider/outputs/academic-paper.json`
- `evidence/model-provider/usage-log.json`

### Archive Sync

- `ARCHIVE_LOCAL_ROOT`
- `ARCHIVE_SYNC_TARGET`

Dry-run before live sync:

```bash
python3 scripts/spikes/archive_storage_spike.py --dry-run
```

Live command after paths are configured:

```bash
python3 scripts/spikes/archive_storage_spike.py
```

Required evidence:

- Local Archive Package path.
- Redacted sync command or host-native sync configuration note.
- Successful sync status for a sample package.
- Failure status remains recorded and retryable.

Expected evidence files:

- `evidence/archive-storage/sync-result.json`
- `evidence/archive-storage/local-tree.txt`
- `evidence/archive-storage/remote-tree.txt`

## Implementation Rule

Issues #10, #11, #12, #13, #14, #15, #16, #17, #18, #19, and #20 must remain `needs-triage` until the relevant blockers above are cleared. Moving any issue to `ready-for-agent` requires checking its Dependencies section and confirming the corresponding live spike evidence exists.
