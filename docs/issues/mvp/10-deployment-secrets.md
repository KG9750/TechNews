# MVP: Implement deployment and secrets setup

## Problem

The MVP needs a repeatable deployment path on the Briefing Host with secrets outside version control.

## Scope

- Add Docker Compose configuration for the Python single-service app.
- Mount data and archive volumes.
- Document required environment variables and secret setup.
- Add health checks for scheduler/run status and archive write path.
- Document backup/sync responsibilities for the Briefing Host.

## Out of scope

- Managed cloud deployment.
- Kubernetes or multi-host orchestration.
- Cost dashboard or model-routing infrastructure.

## Acceptance criteria

- The app can run on a NAS or always-on small server through Docker Compose.
- `.env.example` remains secret-free and complete for MVP variables.
- Real `.env` files are ignored by git.
- Health checks expose whether the service can schedule, write archives, and reach configured dependencies.

## Test expectations

- Compose config validation.
- Local container startup smoke test.
- Secret redaction check in logs/config output.
- Manual Briefing Host smoke test before MVP acceptance.

## Relevant docs

- `docs/adr/0004-docker-compose-briefing-host.md`
- `docs/secrets.md`
- `.env.example`
- `.gitignore`

## Dependencies

- Feishu credentials, model credentials, archive local root, archive sync target, and admin access values.

## Triage label

`ready-for-agent`
