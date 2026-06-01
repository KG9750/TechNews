# Golden Samples

Status: Reviewed for model spike
Last updated: 2026-06-01

These fixtures exercise classification, selection, confidence notices, and archive metadata without storing full copyrighted article bodies.

Review notes:

- Reviewed on 2026-06-01 for model-provider spike readiness.
- Contains 22 fixtures: 21 real-world metadata-only items and 1 synthetic behavior exercise.
- The synthetic item is marked with `synthetic_behavior_exercise` and uses `example.invalid` intentionally.
- URL anchors were normalized where old links returned 404 or redirected to a canonical location.
- Known access limitation: the official OpenAI GPT-4o URL may return HTTP 403 to metadata scripts, but is retained as an official source anchor.

Rules:

- Store source metadata and expected outputs only.
- Do not store complete source article text.
- Prefer official source URLs when possible.
- Include duplicate coverage, low-confidence items, academic papers, source media, and no-media items.
- Treat these as regression fixtures, not as a complete daily briefing.
