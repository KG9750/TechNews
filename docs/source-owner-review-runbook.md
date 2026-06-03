# Source Owner Review Runbook

Status: Draft
Last updated: 2026-06-03

Use this runbook to close source eligibility review items before a `needs_review` source is enabled for production auto-ingestion.

This is a product and compliance review workflow, not legal advice. If source terms are unclear, keep the source `needs_review` and keep `production_auto_ingestion` disabled.

## Review Inputs

- Review matrix: `docs/source-eligibility-reviews.md`
- Implementation policy: `fixtures/source-ingestion/source-access-policy.json`
- Owner queue: `fixtures/source-ingestion/source-owner-review-queue.json`
- Source registry: `docs/source-registry.md`
- Source checklist: `docs/source-eligibility-checklist.md`

## Default Until Resolved

- Do not production auto-ingest the source.
- Do not store complete article bodies.
- Do not reuse source media.
- Use metadata-only probe or manual-only behavior from `source-access-policy.json`.
- Preserve source name, original title, and source URL in any fixture or manual validation item.

## Owner Review Steps

1. List open items:

```bash
python3 scripts/source_owner_review_decision.py --list-open
```

2. Pick an `open` item from `fixtures/source-ingestion/source-owner-review-queue.json`.
3. Generate a fillable owner decision draft:

```bash
python3 scripts/source_owner_review_decision.py --draft src-the-verge
```

This writes an ignored file under:

```text
evidence/source-owner-reviews/
```

4. Collect the listed `evidence_required` from source terms, feed/API policy, robots guidance, permissions pages, or owner/legal notes.
5. Answer every `owner_questions` item in the generated decision file.
6. Decide one outcome:
   - Keep `needs_review` if permission, license obligations, media rules, or rate limits remain unclear.
   - Move to `eligible` only when metadata-only generated summaries, access method, attribution, rate behavior, and media policy are all approved.
   - Move to `blocked` if automated access or summary reuse is disallowed.
   - Move to `deferred` if the source should remain a seed source but not an MVP production source.
7. Validate the completed decision file:

```bash
python3 scripts/source_owner_review_decision.py --validate evidence/source-owner-reviews/src-the-verge.decision.json
```

8. Update all affected artifacts in the same change.
9. Run `python3 scripts/check_readiness.py` before changing GitHub issue labels.

## Artifact Update Rules

When a source stays `needs_review`:

- Keep it in `fixtures/source-ingestion/source-owner-review-queue.json` with `review_status: "open"`.
- Keep `production_auto_ingestion: false` in `fixtures/source-ingestion/source-access-policy.json`.
- Update `docs/source-eligibility-reviews.md` only with more precise evidence or next action notes.

When a source becomes `eligible`:

- Update `docs/source-eligibility-reviews.md` to `eligible`.
- Update `fixtures/source-ingestion/source-access-policy.json` to metadata-only production behavior.
- Remove that source from `fixtures/source-ingestion/source-owner-review-queue.json`.
- Update `docs/source-registry.md` eligibility notes.
- Keep media blocked unless source-specific media reuse is approved and attribution behavior is implemented.

When a source becomes `blocked` or `deferred`:

- Update `docs/source-eligibility-reviews.md`.
- Update `fixtures/source-ingestion/source-access-policy.json` so production auto-ingestion remains disabled.
- Update `docs/source-registry.md` notes or MVP state if needed.
- Remove it from the open owner queue once the decision is recorded.

## Evidence Note Template

Use this shape in `docs/source-eligibility-reviews.md` or a linked issue comment:

```text
Reviewed YYYY-MM-DD by Briefing Administrator.
Evidence checked: <terms/feed/API/permissions links or internal note>.
Decision: <eligible | needs_review | blocked | deferred>.
Summary policy: <metadata-only generated summary allowed | owner review still required | disallowed>.
Media policy: <none | attribution-gated | separately licensed>.
Rate policy: <published limit | conservative default>.
Required implementation guardrail: <policy row / connector mode / test expectation>.
```

## Readiness Gate

`python3 scripts/check_readiness.py` verifies that:

- Every current `needs_review` source has exactly one open owner review queue item.
- Queue connector modes match `fixtures/source-ingestion/source-access-policy.json`.
- Production auto-ingestion and source media reuse stay disabled while review is open.
- Manual URL and pending-permission sources use the correct review decision type.
- `scripts/source_owner_review_decision.py` exists and supports listing open reviews, drafting ignored decision files, and validating completed decisions.
