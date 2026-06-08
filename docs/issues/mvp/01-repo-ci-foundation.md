# MVP: Repo and CI foundation

## Problem

The MVP needs a predictable Python project foundation before product modules are added.

## Scope

- Add Python 3.12 project metadata, dependency management, and a test runner.
- Add formatting and lint commands that can run locally and in CI.
- Add fixture validation commands for JSON and markdown-backed contract examples.
- Add a minimal GitHub Actions workflow once the project commands exist.

## Out of scope

- Product source connectors, model calls, Feishu delivery, archive sync, and UI implementation.
- Frontend build tooling unless a later ADR supersedes the server-rendered console choice.

## Acceptance criteria

- A new contributor can install dependencies and run the baseline checks from documented commands.
- CI runs the same checks as local development.
- CI validates existing JSON fixtures under `fixtures/`.
- The repo remains aligned with ADR-0003 and ADR-0004.

## Test expectations

- Run formatter/linter in check mode.
- Run unit test command, even if the first suite is small.
- Run JSON fixture validation.
- Confirm CI passes on the branch or commit that adds the foundation.

## Relevant docs

- `docs/adr/0003-python-single-service-stack.md`
- `docs/adr/0004-docker-compose-briefing-host.md`
- `docs/PRE-DEVELOPMENT-PLAN.md`

## Dependencies

- Readiness gate has passed; this issue is ready to implement.

## Triage label

`ready-for-agent`
