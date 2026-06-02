# Live Spike Evidence Runbook

Status: Ready for external validation
Last updated: 2026-06-02

This runbook explains how to turn the remaining external spikes into evidence that can pass the readiness gate. Generated evidence belongs under `evidence/`, which is ignored by git. Do not commit real credentials, recipient ids, provider responses, or storage paths.

## Final Gate Command

After credentials and live evidence are available, run:

```bash
python3 scripts/check_readiness.py --require-live --require-evidence
```

The gate only passes when both conditions are true:

- Required environment variables are present.
- Redacted evidence files pass validation.

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

Template files:

```text
fixtures/live-evidence-templates/feishu-delivery/
```

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

Template files:

```text
fixtures/live-evidence-templates/archive-storage/
```

## Redaction Rules

- Redact secrets, tokens, authorization headers, recipient ids, tenant ids, and private storage paths.
- Keep enough non-sensitive response shape to prove success.
- Do not redact `code`, status fields, request counts, latency fields, provider/model names, or source anchors needed by validation.
- Do not replace required fields with `TEMPLATE_...`; the readiness checker rejects template markers in live evidence.
