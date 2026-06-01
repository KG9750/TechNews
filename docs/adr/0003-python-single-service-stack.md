# Use a Python single-service stack for the MVP

Status: accepted

The MVP should be implemented as one Python service instead of a split frontend/backend system or a Node-first application. Python is the best fit for the first version because source ingestion, archive writing, model-provider calls, and operational scripts are all data-heavy workflows with mature Python libraries. A single service can expose the Operations Console, run scheduled jobs, call Feishu, and write Archive Packages without introducing cross-service contracts before the core workflow is proven.

The default runtime is Python 3.12. The default web boundary is FastAPI with server-rendered console pages or minimal progressive enhancement. A separate React/Next.js frontend is deferred until the Operations Console needs richer interaction than configuration, run status, and retry controls.

**Tradeoffs**

- Python reduces workflow and data-processing risk, but the Operations Console will be less interactive than a dedicated frontend.
- A single service is easier to deploy on a NAS or small server, but long-running work needs careful scheduling and status recording.
- Deferring a separate frontend avoids early build complexity, but later UI growth may require a frontend split.

**Consequences**

- MVP implementation issues should assume one Python codebase unless this ADR is superseded.
- Console work should start with server-rendered pages and basic forms.
- Shared contracts should be expressed as Python data models first, then exported to JSON Schema only when another runtime needs them.
- Repo/CI setup should validate Python formatting, typing where practical, unit tests, and fixture checks before adding frontend tooling.
