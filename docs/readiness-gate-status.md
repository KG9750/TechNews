# Development Readiness Gate Status

Status: Not passed
Last updated: 2026-06-02

This file is the current audit trail for the readiness gate in `docs/PRE-DEVELOPMENT-PLAN.md`. It records evidence that has been verified and the remaining evidence required before formal MVP implementation issues can move out of `needs-triage`.

## Gate Summary

The repository is ready for live external validation, but not ready for product implementation. The remaining blockers are:

- Feishu delivery spike: needs real internal app bot delivery to one user and one group.
- Model Provider spike: needs one real provider/model call set with usage metadata.
- Archive/storage spike: needs real `ARCHIVE_SYNC_TARGET` success evidence.

Additional review item:

- Source eligibility: 32 first-version seed sources are covered in `docs/source-eligibility-reviews.md`; all first-version sources now have source-specific evidence or per-URL review rules recorded, and `scripts/check_readiness.py` rejects generic terms-evidence placeholders. 7 metadata/text-only sources are `eligible`, and 25 public/company/manual sources remain `needs_review` before automated production ingestion.

The live spike evidence procedure is now documented in `docs/live-spike-evidence-runbook.md`. Template evidence files live under `fixtures/live-evidence-templates/`; they are examples only, and `scripts/check_readiness.py` rejects any live evidence that still contains `TEMPLATE_` placeholders.

Pre-development readiness is also protected in GitHub Actions by `.github/workflows/pre-development-readiness.yml`. The workflow runs the local readiness checker, compiles the readiness/spike scripts, and proves the tracked evidence templates cannot pass as live evidence. It intentionally does not require live external credentials.

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
| Baseline docs are committed and pushed | Passed | Commit `6fa77b1`; current `main` pushed through `76a9f74` | None |
| GitHub labels, milestones, and tracking issue exist | Passed | Labels and milestones created; tracking issue #1 | None |
| Pre-development readiness CI exists | Passed | `.github/workflows/pre-development-readiness.yml`; `scripts/check_readiness.py` verifies workflow coverage | None |
| Minimum contracts exist | Passed | `docs/schemas/minimal-contracts.md`; issue #2 closed | None |
| Feishu delivery spike passes for one user and one group | Blocked | Fixtures in `fixtures/feishu-delivery/`; live evidence template in `fixtures/live-evidence-templates/feishu-delivery/`; issue #3 open `needs-info` | Need Feishu app credentials, user open_id, group chat_id, live send evidence under `evidence/feishu-delivery/` |
| Source ingestion spike normalizes every First-Version Source type | Passed | `docs/spikes/source-ingestion.md`; `fixtures/source-ingestion/candidate-items.json`; issue #4 closed | None |
| Archive/storage spike passes | Blocked | Local archive fixture in `fixtures/archive-storage/`; live evidence template in `fixtures/live-evidence-templates/archive-storage/`; issue #6 open `needs-info` | Need real NAS/cloud sync target success evidence under `evidence/archive-storage/` |
| Model Provider spike passes structured output and usage metadata checks | Blocked | Prompt/output fixtures in `fixtures/model-provider/`; live evidence template in `fixtures/live-evidence-templates/model-provider/`; issue #5 open `needs-info` | Need live provider/model, redacted outputs, token/latency/failure metadata under `evidence/model-provider/` |
| Live evidence runbook and template-negative gate exist | Passed | `docs/live-spike-evidence-runbook.md`; `fixtures/live-evidence-templates/`; `scripts/check_readiness.py --require-evidence --evidence-root fixtures/live-evidence-templates` fails on `TEMPLATE_` placeholders | None |
| Technology Domain Template and briefing style guide are drafted | Passed | `docs/taxonomy/technology-domain-template.md`; `docs/briefing-style-guide.md`; issue #7 closed | None |
| Source registry contains at least 30 seed sources | Passed | `docs/source-registry.md`; 37 total seed sources, 32 first-version, 5 deferred | None |
| Source eligibility review covers first-version seed sources | Review | `docs/source-eligibility-reviews.md`; 32 first-version sources covered, 7 `eligible`, 25 `needs_review`; no first-version source remains without recorded evidence or per-URL review rules; placeholder regression is checked by `scripts/check_readiness.py` | Owner must complete source-specific terms/media/rate-limit review before automated production ingestion for `needs_review` sources |
| Golden samples cover at least 20 real-world items | Passed | `fixtures/golden-samples/items.json`; 22 total fixtures, 21 real-world items; issue #8 closed | None |
| Required ADRs exist | Passed | 8 ADRs in `docs/adr/`; issue #9 closed | None |
| MVP issue breakdown exists and is labeled | Passed | `docs/github-issue-breakdown.md`; GitHub issues #10, #11, #12, #13, #14, #15, #16, #17, #18, #19, and #20 created with milestone `mvp` and label `needs-triage` | None |

## External Inputs Needed

To finish the gate, provide these values in the deployment environment or secure local test environment. Do not commit them.

Use `docs/live-spike-evidence-runbook.md` for the exact commands, redaction rules, evidence layouts, and final gate command. Copy templates from `fixtures/live-evidence-templates/` only as a starting point; every `TEMPLATE_` placeholder must be replaced or the checker will fail.

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
