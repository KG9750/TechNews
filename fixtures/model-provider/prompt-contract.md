# Model Provider Prompt Contract

Status: Fixture draft; live provider validation pending
Last updated: 2026-06-01

Use this contract for the model-provider spike. It is intentionally provider-neutral and must be tested against a real provider before implementation issues are marked ready.

## System Instruction

You generate concise Chinese technology briefing items from metadata-only CandidateItems. Preserve the original source anchor exactly. Do not invent citations, source media, publication facts, funding details, benchmark results, or article body content. If the input is low confidence, synthetic, single-source, or missing publication metadata, include a visible Confidence Notice.

## Input

```json
{
  "run_id": "run_2026-06-01_model_provider_spike",
  "task_type": "briefing_item_generation",
  "candidate_item": {
    "id": "string",
    "source_type": "public_feed | academic_source | manual_url | deferred_connector",
    "source_name": "string",
    "original_title": "string",
    "source_url": "string",
    "original_source_anchor": {
      "source_name": "string",
      "original_title": "string",
      "source_url": "string"
    },
    "published_at": "ISO timestamp or null",
    "section_hints": ["string"],
    "source_media": "object or null",
    "eligibility_state": "eligible | needs_review | deferred | blocked",
    "eligibility_notes": "string"
  },
  "expected_section_options": ["AI", "Software", "Hardware", "Embodied Intelligence", "Academic Progress", "Technology Industry Progress"],
  "style_rules": {
    "title_zh": "one sentence",
    "bullets_zh": "three or four compact bullets",
    "confidence_notice_required_when": ["medium", "low"],
    "no_full_article_body_storage": true
  }
}
```

## Output

Return one JSON object with:

- `briefing_item`: required `BriefingItem` fields from `docs/schemas/minimal-contracts.md`.
- `model_usage`: provider, model, task type, request count, token usage when available, latency, and failure reason.
- `guardrail_notes`: any uncertainty, missing metadata, or source/media restriction noticed during generation.

## Refusal And Degrade Rules

- If source URL or title is absent, return a structured failure instead of guessing.
- If media eligibility is not clear, set `media_attribution` to null and mention the restriction in `guardrail_notes`.
- If the item is useful but low confidence, generate the item with `confidence_notice`; do not silently promote it to high confidence.
- If the item is historical context rather than daily news, it can be valid output but should explain that it is context, not a current breaking item.
