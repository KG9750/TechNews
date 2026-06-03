# Live Spike Evidence Runbook

Status: Ready for external validation
Last updated: 2026-06-03

This runbook explains how to turn the remaining external spikes into evidence that can pass the readiness gate. Generated evidence belongs under `evidence/`, which is ignored by git. Do not commit real credentials, recipient ids, provider responses, or storage paths.

## Live Evidence Preflight

Before running live external spikes, generate a local preflight summary:

```bash
python3 scripts/spikes/live_readiness_preflight.py --dry-run --write-packet --write-spike-packets
python3 scripts/readiness_action_packet.py --write-mvp-issue-packets
```

This writes:

```text
evidence/live-readiness-preflight.json
evidence/live-readiness-packet.md
evidence/live-spike-packets/feishu-delivery.md
evidence/live-spike-packets/model-provider.md
evidence/live-spike-packets/archive-storage.md
evidence/final-redaction-review.md
evidence/readiness-action-packet.md
evidence/mvp-issue-packets/issue-10.md through issue-20.md
```

The preflight runs the local helper dry-runs, reports required environment variable names as present or missing, lists missing live evidence files, groups final evidence by spike as `missing`, `partial`, or `complete`, generates a final redaction review packet, and summarizes live evidence validation failures from the same validator used by the final gate. The Markdown packet gives the same status as a human execution checklist with the command order, evidence checklist, final evidence group status, validation status, and redaction guardrails. The per-spike packets split Feishu, model-provider, and archive-storage status into issue-facing checklists for #3, #5, and #6, including a closure gate that stays blocked until that spike's final evidence group is `complete`. A `partial` final evidence group means some files exist but that spike is still incomplete and must not be closed. The final redaction review packet lists every final evidence file, preserves validation fields that should remain visible, and reminds the operator what must not be pasted into GitHub. The top-level readiness action packet links the live packet, per-spike packets, source-owner review index, worksheet, batch plan, readiness-manifest blocker, final redaction review packet, an external input request checklist, relevant GitHub issues, an MVP issue unlock matrix, and per-MVP-issue triage packets into one execution view. The external input checklist names required variables and safe request wording only; it does not collect real secret values. These files do not print or store environment values. The generated summary and packets are ignored by git.

The live packet also includes a dry-run artifact inventory. Files such as `readiness-manifest.dry-run.json`, `dry-run-request-shape.redacted.json`, model request envelopes, and `dry-run-sync-result.json` are helper outputs only; they do not count as final live evidence and must not be used to close #3, #5, #6, or the readiness gate.

After credentials and redacted evidence are configured, use strict mode as a quick final check before the readiness gate:

```bash
python3 scripts/spikes/live_readiness_preflight.py --strict --write-packet --write-spike-packets
```

Strict mode fails until all required environment variable names are present, every final evidence group is `complete`, the tracked git worktree is clean, and the live evidence files exist without template markers, sensitive-value leaks, or schema/metadata validation failures. Ignored files under `evidence/` do not need to be committed. It is a convenience check; the authoritative final gate remains `scripts/check_readiness.py`.

CI regression coverage:

```bash
python3 scripts/test_live_evidence_helpers.py
```

This test verifies preflight redaction, helper dry-runs in a temporary evidence directory, dry-run artifact inventory, partial final evidence group reporting, strict preflight blocking for incomplete final evidence groups, Markdown packet output without secret values, readiness manifest dry-run shape, final redaction review packet shape, model request-envelope metadata-only validation, template evidence failure reporting, a synthetic redacted evidence package that exercises the positive live-evidence validator path, preflight acceptance of that synthetic package, and rejection of raw sensitive environment values in evidence files.

## Final Gate Command

After credentials and live evidence are available, run:

```bash
python3 scripts/check_readiness.py --require-live --require-evidence
```

The gate only passes when these conditions are true:

- Required environment variables are present.
- Redacted evidence files pass validation.
- `evidence/readiness-manifest.json` declares the final evidence set and matches the live model/archive run metadata.
- The tracked git worktree is clean, so the manifest `commit` and final gate refer to the same tracked files. Ignored `evidence/` files may remain untracked.

## Evidence Manifest

Create this file after all three live spikes have generated redacted evidence:

```text
evidence/readiness-manifest.json
```

Dry-run the manifest shape before live evidence is complete:

```bash
python3 scripts/spikes/readiness_manifest.py --dry-run
```

Generate the final manifest and final redaction review packet after live evidence is complete and redacted:

```bash
python3 scripts/spikes/readiness_manifest.py --write-final-review-packet --reviewed-by "Briefing Administrator" --redaction-notes "Reviewed redacted evidence for template markers, sensitive ids, tokens, and private paths."
```

Template:

```text
fixtures/live-evidence-templates/readiness-manifest.json
```

Validation rules:

- `repository` must be `KG9750/TechNews`.
- `commit`, `generated_at`, `reviewed_by`, and `redaction_review` must be filled in.
- `generated_at` and `redaction_review.reviewed_at` must be valid UTC ISO timestamps ending in `Z`.
- `commit` must match the current git `HEAD` when the final readiness gate runs; regenerate the manifest after any tracked file changes.
- Final manifest generation and the final readiness gate require a clean tracked worktree. Commit or revert tracked changes before writing `evidence/readiness-manifest.json`; ignored evidence files may remain untracked.
- Feishu, model-provider, and archive-storage spike statuses must be `passed`.
- Manifest evidence file declarations must exactly match the required live evidence files below.
- Model Provider `run_id`, `provider`, and `model` must match `evidence/model-provider/usage-log.json`, and every model output must use that same `run_id`.
- Archive/storage `run_id` must match `evidence/archive-storage/sync-result.json`.
- Manifest content must pass the same template-marker and sensitive-value redaction checks as other live evidence files.
- The manifest helper writes generated files under ignored `evidence/`; do not commit live manifests or final redaction review packets.
- `evidence/final-redaction-review.md` is an operator checklist only. It does not replace strict preflight or the final readiness gate.

## Feishu Delivery

Dry-run:

```bash
python3 scripts/spikes/feishu_delivery_spike.py --dry-run
```

Live run:

```bash
python3 scripts/spikes/feishu_delivery_spike.py
python3 scripts/spikes/feishu_delivery_spike.py --validate-evidence
```

Optional group-chat fallback after internal app group delivery fails:

```bash
python3 scripts/spikes/feishu_delivery_spike.py --attempt-group-webhook-fallback
```

This fallback uses `FEISHU_GROUP_WEBHOOK_URL` and optional `FEISHU_GROUP_WEBHOOK_SECRET` for a custom group bot. It is only group-chat fallback evidence; it does not satisfy the final internal-app user and group delivery gate.

Required environment:

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_DEFAULT_USER_OPEN_ID`
- `FEISHU_DEFAULT_CHAT_ID`
- `FEISHU_GROUP_WEBHOOK_URL`, optional fallback only
- `FEISHU_GROUP_WEBHOOK_SECRET`, optional fallback signing secret only

Required evidence:

```text
evidence/feishu-delivery/
  user-request.redacted.json
  user-response.redacted.json
  group-request.redacted.json
  group-response.redacted.json
  rendered-message.md
```

Validation rules:

- User request JSON must use `path = internal_app_bot` and `receive_id_type = open_id`.
- Group request JSON must use `path = internal_app_bot` and `receive_id_type = chat_id`.
- Request bodies must use `msg_type = interactive`, include a redacted `receive_id`, and preserve parseable card content.
- User and group response JSON must have `code = 0`.
- Each response must include a non-empty `data` object.
- Each response must include a non-empty `data.message_id` so the send-message result remains verifiable after redaction.
- Rendered message must include a source line, a Confidence Notice, and an Archive or Deep-Dive link.
- Evidence must not contain `TEMPLATE_` placeholders.
- Evidence must not contain raw tokens, Feishu recipient ids, app ids, authorization headers, private local paths, or raw configured secret/env values.
- The Feishu runner redacts common sensitive response keys and values before writing evidence; still inspect output and run the final gate before sharing.
- The fallback request shape is included in dry-run evidence. Signed fallback payloads redact `sign` before writing evidence.

Template files:

```text
fixtures/live-evidence-templates/feishu-delivery/
```

Synthetic leak-test fixtures:

```text
fixtures/live-evidence-negative/leaky-feishu/
fixtures/live-evidence-negative/leaky-model-provider/
fixtures/live-evidence-negative/leaky-archive-storage/
```

These fixtures intentionally contain fake Feishu ids, fake bearer tokens, and fake private paths across Feishu, Model Provider, and Archive/storage evidence. They must fail validation and are used by CI to prove the redaction scanner is active across every external evidence workstream.

## Model Provider

Dry-run request generation:

```bash
python3 scripts/spikes/model_provider_spike.py --dry-run
python3 scripts/spikes/model_provider_spike.py --validate-requests
```

`--validate-requests` checks that generated provider-neutral request envelopes preserve the Original Source Anchor, remain metadata-only, omit `source_media`, and do not include full-body keys such as `article_body`, `full_text`, `html`, or `transcript`.

After the chosen provider returns redacted outputs:

```bash
python3 scripts/spikes/model_provider_spike.py --validate-evidence
python3 scripts/check_readiness.py --require-evidence
```

Required environment:

- `MODEL_PROVIDER`
- `MODEL_DEFAULT_MODEL`
- `MODEL_API_KEY`

Required evidence:

```text
evidence/model-provider/
  outputs/
    high-confidence-news.json
    low-confidence-news.json
    academic-paper.json
  usage-log.json
```

Validation rules:

- Provider and model must identify a live provider/model, not `fixture` or `not_called`.
- Each output must preserve the exact Original Source Anchor from its input fixture.
- Each output must contain three or four Chinese bullets.
- Low-confidence output must remain `low` and include a Confidence Notice.
- Each output `briefing_item.run_id` must match `usage-log.json` `run_id`.
- Each output `model_usage.provider` and `model_usage.model` must match the usage log provider/model.
- Each output `model_usage.task_type` must be `briefing_item_generation`.
- Usage log must include three tasks with `request_count > 0` and `latency_ms`.
- Usage log tasks must use `briefing_item_generation` and exactly match the three expected output fixtures and input fixture ids.
- Evidence must not contain `TEMPLATE_` placeholders.
- Evidence must not contain raw API keys, authorization headers, private local paths, or raw configured secret/env values.

Template files:

```text
fixtures/live-evidence-templates/model-provider/
```

## Archive Sync

Dry-run:

```bash
python3 scripts/spikes/archive_storage_spike.py --dry-run
```

Live run:

```bash
python3 scripts/spikes/archive_storage_spike.py
python3 scripts/spikes/archive_storage_spike.py --validate-evidence
```

Required environment:

- `ARCHIVE_LOCAL_ROOT`
- `ARCHIVE_SYNC_TARGET`

Required evidence:

```text
evidence/archive-storage/
  sync-result.json
  local-tree.txt
  remote-tree.txt
```

Validation rules:

- `local_archive.status` must be `written`.
- `remote_sync.status` must be `synced`.
- Local and remote file counts must be greater than zero.
- Local and remote file counts must match.
- Each `file_count` value must match the number of file entries in its corresponding tree file; directory entries ending in `/` are not counted.
- Local and remote tree files must exist, be non-empty, and list the same redacted relative package files in the same order.
- Evidence must not contain `TEMPLATE_` placeholders.
- Evidence must not contain private local paths, private sync target paths, tokens, or raw configured secret/env values.
- The runner writes redacted path labels such as `REDACTED_LOCAL_ARCHIVE_ROOT/2026-06-01/technology` and `REDACTED_SYNC_TARGET/2026-06-01/technology`; do not replace them with real host or NAS paths.
- The runner also redacts local/archive/sync paths inside recorded retryable failure reasons before writing evidence.

Template files:

```text
fixtures/live-evidence-templates/archive-storage/
```

## Redaction Rules

- Redact secrets, tokens, authorization headers, recipient ids, tenant ids, and private storage paths.
- Keep enough non-sensitive response shape to prove success.
- Do not redact `code`, status fields, request counts, latency fields, provider/model names, or source anchors needed by validation.
- Do not replace required fields with `TEMPLATE_...`; the readiness checker rejects template markers in live evidence.
- Prefer stable redaction labels such as `REDACTED`, `REDACTED_MESSAGE_ID`, `REDACTED_LOCAL_PATH`, and `REDACTED_SYNC_TARGET`.
- The readiness checker rejects common leak patterns including `Bearer ...`, Feishu `ou_...`/`oc_...`/`cli_...` ids, `/Users/...`, `/private/...`, iCloud workspace paths, and raw values from configured sensitive environment variables.
- CI runs negative live evidence checks for Feishu, Model Provider, and Archive/storage leak fixtures; each root must fail with the expected validation exit code.
