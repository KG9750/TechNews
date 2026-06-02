# Development Readiness Gate Status

Status: Not passed
Last updated: 2026-06-01

This file is the current audit trail for the readiness gate in `docs/PRE-DEVELOPMENT-PLAN.md`. It records evidence that has been verified and the remaining evidence required before formal MVP implementation issues can move out of `needs-triage`.

## Gate Summary

The repository is ready for live external validation, but not ready for product implementation. The remaining blockers are:

- Feishu delivery spike: needs real internal app bot delivery to one user and one group.
- Model Provider spike: needs one real provider/model call set with usage metadata.
- Archive/storage spike: needs real `ARCHIVE_SYNC_TARGET` success evidence.

Local evidence can be checked with:

```bash
python3 scripts/check_readiness.py
```

To make missing external variables fail the check before a live spike, run:

```bash
python3 scripts/check_readiness.py --require-live
```

## Requirement Status

| Requirement | Status | Evidence | Remaining gap |
| --- | --- | --- | --- |
| Baseline docs are committed and pushed | Passed | Commit `6fa77b1`; current `main` pushed through `297a71d` | None |
| GitHub labels, milestones, and tracking issue exist | Passed | Labels and milestones created; tracking issue #1 | None |
| Minimum contracts exist | Passed | `docs/schemas/minimal-contracts.md`; issue #2 closed | None |
| Feishu delivery spike passes for one user and one group | Blocked | Fixtures in `fixtures/feishu-delivery/`; issue #3 open `needs-info` | Need Feishu app credentials, user open_id, group chat_id, live send evidence |
| Source ingestion spike normalizes every First-Version Source type | Passed | `docs/spikes/source-ingestion.md`; `fixtures/source-ingestion/candidate-items.json`; issue #4 closed | None |
| Archive/storage spike passes | Blocked | Local archive fixture in `fixtures/archive-storage/`; issue #6 open `needs-info` | Need real NAS/cloud sync target success evidence |
| Model Provider spike passes structured output and usage metadata checks | Blocked | Prompt/output fixtures in `fixtures/model-provider/`; issue #5 open `needs-info` | Need live provider/model, redacted outputs, token/latency/failure metadata |
| Technology Domain Template and briefing style guide are drafted | Passed | `docs/taxonomy/technology-domain-template.md`; `docs/briefing-style-guide.md`; issue #7 closed | None |
| Source registry contains at least 30 seed sources | Passed | `docs/source-registry.md`; 37 total seed sources, 32 first-version, 5 deferred | None |
| Golden samples cover at least 20 real-world items | Passed | `fixtures/golden-samples/items.json`; 22 total fixtures, 21 real-world items; issue #8 closed | None |
| Required ADRs exist | Passed | 8 ADRs in `docs/adr/`; issue #9 closed | None |
| MVP issue breakdown exists and is labeled | Passed | `docs/github-issue-breakdown.md`; GitHub issues #10, #11, #12, #13, #14, #15, #16, #17, #18, #19, and #20 created with milestone `mvp` and label `needs-triage` | None |

## External Inputs Needed

To finish the gate, provide these values in the deployment environment or secure local test environment. Do not commit them.

### Feishu

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_TENANT_KEY`, if required by the app setup
- `FEISHU_DEFAULT_USER_OPEN_ID`
- `FEISHU_DEFAULT_CHAT_ID`

Required evidence:

- Redacted successful send response for one user.
- Redacted successful send response for one group.
- Rendered Feishu message text or screenshot.
- Scopes, permissions, recipient id type, rate/message-size notes, and any failure response shape.

### Model Provider

- `MODEL_PROVIDER`
- `MODEL_DEFAULT_MODEL`
- `MODEL_API_KEY`

Required evidence:

- Redacted request/response for high-confidence news, low-confidence news, and academic paper examples.
- Provider/model name.
- Request count, token usage when available, latency, and failure reason when present.

### Archive Sync

- `ARCHIVE_LOCAL_ROOT`
- `ARCHIVE_SYNC_TARGET`

Required evidence:

- Local Archive Package path.
- Redacted sync command or host-native sync configuration note.
- Successful sync status for a sample package.
- Failure status remains recorded and retryable.

## Implementation Rule

Issues #10, #11, #12, #13, #14, #15, #16, #17, #18, #19, and #20 must remain `needs-triage` until the relevant blockers above are cleared. Moving any issue to `ready-for-agent` requires checking its Dependencies section and confirming the corresponding live spike evidence exists.
