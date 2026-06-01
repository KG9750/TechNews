# Isolate model providers behind one generation boundary

Status: accepted

The MVP will call model providers through one internal generation boundary instead of spreading provider-specific request code across source ranking, briefing generation, and deep-dive generation. Product code should pass a structured task request containing run id, task type, input Candidate Items or Briefing Items, required output shape, and citation/source constraints. The provider adapter returns structured output, confidence notices, source anchors, usage metadata when available, latency, and failure information.

The exact first provider and model are deferred to the model-provider spike. The MVP should not build a provider marketplace, automatic fallback router, or complex cost optimizer before structured output quality and usage logging are proven.

**Tradeoffs**

- A single boundary makes provider replacement possible, but can hide provider-specific capabilities unless the adapter is designed carefully.
- Avoiding multi-provider routing keeps the MVP small, but manual intervention may be needed if the chosen provider degrades.
- Deferring budget caps supports quality-first evaluation, but usage metadata must be recorded from the start.

**Consequences**

- Model calls must record run id, provider, model, task type, request count, token usage when available, latency, and failure reason.
- Prompt templates and output contracts should live outside provider-specific adapter code.
- Generated content must preserve Original Source Anchors and must not invent citations or media.
- MVP issues for ranking and briefing generation remain `needs-triage` until the model spike proves structured output against golden samples.
