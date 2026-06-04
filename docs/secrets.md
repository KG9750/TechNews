# Runtime Environment Inventory

Status: Draft
Last updated: 2026-06-04

Do not store real secrets in this repo. Use `.env.example` for variable names only and configure real values on the Briefing Host. Some variables below are non-secret runtime configuration, but they still belong outside tracked files until the Operations Console owns them.

| Variable | Purpose | Required for | Owner | Setup note |
| --- | --- | --- | --- | --- |
| `FEISHU_APP_ID` | Feishu internal app identifier | Feishu delivery spike, MVP delivery | Briefing Administrator | Created in Feishu Open Platform. |
| `FEISHU_APP_SECRET` | Feishu internal app secret | Feishu delivery spike, MVP delivery | Briefing Administrator | Store only on the Briefing Host secret store or `.env`. |
| `FEISHU_TENANT_KEY` | Tenant identifier when required by Feishu app setup | Feishu delivery spike | Briefing Administrator | Confirm during Feishu spike. |
| `FEISHU_DEFAULT_USER_OPEN_ID` | Test recipient user identifier | Feishu user delivery verification | Briefing Administrator | Use a test user approved for MVP validation. |
| `FEISHU_DEFAULT_CHAT_ID` | Test group identifier | Feishu group delivery verification | Briefing Administrator | Use a test group containing the app bot. |
| `DELIVERY_DEADLINE_LOCAL_TIME` | Daily Push Briefing delivery deadline local time | Pre-development readiness gate, MVP scheduler | Briefing Administrator | Use `HH:MM` in the configured timezone. |
| `DELIVERY_TIMEZONE` | IANA timezone for the daily delivery deadline | Pre-development readiness gate, MVP scheduler | Briefing Administrator | Example format: `Asia/Shanghai`; do not commit a real deployment value. |
| `FEISHU_GROUP_WEBHOOK_URL` | Optional custom group bot webhook | Group fallback only | Briefing Administrator | Leave empty unless fallback is chosen. |
| `FEISHU_GROUP_WEBHOOK_SECRET` | Optional group bot signing secret | Group fallback only | Briefing Administrator | Leave empty unless fallback is chosen. |
| `MODEL_PROVIDER` | First Model Provider name | Model provider spike | Briefing Administrator | Example values are intentionally omitted until selected. |
| `MODEL_API_KEY` | Model provider credential | Model provider spike, MVP generation | Briefing Administrator | Must not appear in fixtures, logs, or docs. |
| `MODEL_DEFAULT_MODEL` | Default model name | Model provider spike | Briefing Administrator | Record chosen model in the model spike. |
| `ARCHIVE_LOCAL_ROOT` | Local archive root on the Briefing Host | Archive/storage spike | Briefing Administrator | Example: host-specific mounted path, not committed. |
| `ARCHIVE_SYNC_TARGET` | NAS/cloud sync destination | Archive/storage spike | Briefing Administrator | Use a path or remote target supported by the host. |
| `ADMIN_USERNAME` | Operations Console administrator login | Operations Console | Briefing Administrator | First version has a single administrator. |
| `ADMIN_PASSWORD_HASH` | Hashed administrator password | Operations Console | Briefing Administrator | Store a hash, not a plaintext password. |
| `SESSION_SECRET` | Session signing secret | Operations Console | Briefing Administrator | Generate per deployment. |

## Handling Rules

- Commit `.env.example`, never `.env`.
- Live spike runners, preflight, action packets, and the final readiness gate load root `.env` when present; process environment values take precedence.
- Redact secrets from Feishu, model, and storage spike logs.
- If a secret is accidentally committed, rotate it immediately and treat the commit as compromised.
- Spike documents may include response shapes, status codes, and redacted request payloads, but not credentials.
