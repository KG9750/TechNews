# Live Spike Evidence Runbook

Status: Ready for external validation
Last updated: 2026-06-03

This runbook explains how to turn the remaining external spikes into evidence that can pass the readiness gate. Generated evidence belongs under `evidence/`, which is ignored by git. Do not commit real credentials, recipient ids, provider responses, or storage paths.

## Live Evidence Preflight

Before running live external spikes, generate a local preflight summary:

```bash
python3 scripts/spikes/live_readiness_preflight.py --dry-run --write-packet --write-spike-packets
python3 scripts/readiness_action_packet.py
```

This writes:

```text
evidence/live-readiness-preflight.json
evidence/live-readiness-packet.md
evidence/live-spike-packets/feishu-delivery.md
evidence/live-spike-packets/model-provider.md
evidence/live-spike-packets/archive-storage.md
evidence/readiness-action-packet.md
```

The preflight runs the local helper dry-runs, reports required environment variable names as present or missing, lists missing live evidence files, and summarizes live evidence validation failures from the same validator used by the final gate. The Markdown packet gives the same status as a human execution checklist with the command order, evidence checklist, validation status, and redaction guardrails. The per-spike packets split Feishu, model-provider, and archive-storage status into issue-facing checklists for #3, #5, and #6. The top-level readiness action packet links the live packet, per-spike packets, source-owner review index and worksheet, readiness-manifest blocker, relevant GitHub issues, and an MVP issue unlock matrix into one execution view. These files do not print or store environment values. The generated summary and packets are ignored by git.

After credentials and redacted evidence are configured, use strict mode as a quick final check before the readiness gate:

```bash
python3 scripts/spikes/live_readiness_preflight.py --strict --write-packet --write-spike-packets
```

Strict mode fails until all required environment variable names are present and the live evidence files exist without template markers, sensitive-value leaks, or schema/metadata validation failures. It is a convenience check; the authoritative final gate remains `scripts/check_readiness.py`.

CI regression coverage:

```bash
python3 scripts/test_live_evidence_helpers.py
```

This test verifies preflight redaction, helper dry-runs in a temporary evidence directory, Markdown packet output without secret values, readiness manifest dry-run shape, template evidence failure reporting, a synthetic redacted evidence package that exercises the positive live-evidence validator path, preflight acceptance of that synthetic package, and rejection of raw sensitive environment values in evidence files.

## Final Gate Command

After credentials and live evidence are available, run:

```bash
python3 scripts/check_readiness.py --require-live --require-evidence
```

The gate only passes when both conditions are true:

- Required environment variables are present.
- Redacted evidence files pass validation.
- `evidence/readiness-manifest.json` declares the final evidence set and matches the live model/archive run metadata.

## Evidence Manifest

Create this file after all three live spikes have generated redacted evidence:

```text
evidence/readiness-manifest.json
```

Dry-run the manifest shape before live evidence is complete:

```bash
python3 scripts/spikes/readiness_manifest.py --dry-run
```

Generate the final manifest after live evidence is complete and redacted:

```bash
python3 scripts/spikes/readiness_manifest.py --reviewed-by "Briefing Administrator" --redaction-notes "Reviewed redacted evidence for template markers, sensitive ids, tokens, and private paths."
```

Template:

```text
fixtures/live-evidence-templates/readiness-manifest.json
```

Validation rules:

- `repository` must be `KG9750/TechNews`.
- `commit`, `generated_at`, `reviewed_by`, and `redaction_review` must be filled in.
- Feishu, model-provider, and archive-storage spike statuses must be `passed`.
- Manifest evidence file declarations must exactly match the required live evidence files below.
- Model Provider `run_id`, `provider`, and `model` must match `evidence/model-provider/usage-log.json`, and every model output must use that same `run_id`.
- Archive/storage `run_id` must match `evidence/archive-storage/sync-result.json`.
- Manifest content must pass the same template-marker and sensitive-value redaction checks as other live evidence files.
- The manifest helper writes generated files under ignored `evidence/`; do not commit live manifests.

## Feishu Delivery

Dry-run:

```bash
python3 scripts/spikes/feishu_delivery_spike.py --dry-run
```

Live run:

```bash
python3 scripts/spikes/feishu_delivery_spike.py
```

Required environment:

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_DEFAULT_USER_OPEN_ID`
- `FEISHU_DEFAULT_CHAT_ID`

Required evidence:

```text
evidence/feishu-delivery/
  user-response.redacted.json
  group-response.redacted.json
  rendered-message.md
```

Validation rules:

- User and group response JSON must have `code = 0`.
- Each response must include a non-empty `data` object.
- Rendered message must include a source line and a Confidence Notice.
- Evidence must not contain `TEMPLATE_` placeholders.
- Evidence must not contain raw tokens, Feishu recipient ids, app ids, authorization headers, private local paths, or raw configured secret/env values.
- The Feishu runner redacts common sensitive response keys and values before writing evidence; still inspect output and run the final gate before sharing.

Template files:

```text
fixtures/live-evidence-templates/feishu-delivery/
```

Synthetic leak-test fixture:

```text
fixtures/live-evidence-negative/leaky-feishu/
```

This fixture intentionally contains fake Feishu ids, a fake bearer token, and a fake local path. It must fail validation and is used by CI to prove the redaction scanner is active.

## Model Provider

Dry-run request generation:

```bash
python3 scripts/spikes/model_provider_spike.py --dry-run
```

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
- Usage log must include three tasks with `request_count > 0` and `latency_ms`.
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
- Local and remote tree files must exist.
- Evidence must not contain `TEMPLATE_` placeholders.
- Evidence must not contain private local paths, private sync target paths, tokens, or raw configured secret/env values.
- The runner writes redacted path labels such as `REDACTED_LOCAL_ARCHIVE_ROOT/2026-06-01/technology` and `REDACTED_SYNC_TARGET/2026-06-01/technology`; do not replace them with real host or NAS paths.

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
