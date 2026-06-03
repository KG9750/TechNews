# Source Eligibility Checklist

Status: Draft
Last updated: 2026-06-03

Use this checklist before marking a source as first-version eligible in `docs/source-registry.md`.

## Required Checks

| Check | Required answer |
| --- | --- |
| Access method | RSS, Atom, official API, public metadata, or manual URL. |
| Terms reviewed | Link or note showing where terms, robots guidance, API terms, or feed policy were checked. |
| Full text storage | Must be `not stored by default`. |
| Summary allowed | Must be acceptable under source terms or limited to source metadata and short generated summary. |
| Source media use | Must identify whether feed images, Open Graph images, official images, or no media are allowed. |
| Rate limit | Must record published limit or conservative default. |
| Attribution | Must preserve source name, original title, and source URL. |
| Disallowed behavior | Must list scraping, login bypass, paywall bypass, or media reuse limits when relevant. |
| Eligibility state | `eligible`, `needs_review`, `deferred`, or `blocked`. |

## Connector Enforcement Policy

After review rows are recorded, mirror the implementation-facing decision in `fixtures/source-ingestion/source-access-policy.json`.
For every `needs_review` row, also keep one open owner decision item in `fixtures/source-ingestion/source-owner-review-queue.json`; use `docs/source-owner-review-runbook.md` to close or update those items.
Use `scripts/source_owner_review_decision.py --status` to report missing, invalid, and valid owner decision drafts, `scripts/source_owner_review_decision.py --draft-all` to create missing ignored owner-decision drafts for all open items, `scripts/source_owner_review_decision.py --refresh-context-all` to refresh current artifact context in existing drafts without overwriting owner answers, `scripts/source_owner_review_decision.py --draft <source_id>` to refresh one explicit draft, `scripts/source_owner_review_decision.py --validate <path>` to check one completed decision, `scripts/source_owner_review_decision.py --validate-all` to check every open decision, `scripts/source_owner_review_decision.py --apply <path>` to update one tracked decision after validation, and `scripts/source_owner_review_decision.py --apply-all` to apply every open completed decision after batch validation.

Required policy behavior:

- Every first-version source must have a policy row.
- Policy `eligibility_state` must match `docs/source-eligibility-reviews.md`.
- `needs_review` sources must have `production_auto_ingestion: false`.
- `needs_review` sources must have an open owner review queue item.
- `eligible` sources may be enabled only for metadata-only ingestion.
- Manual URL sources must require per-item review.
- Full article text must remain `not_stored`.
- Source media must not be blanket-allowed; media use stays text-only or attribution-gated until source-specific rights are approved.

## Conservative Defaults

- If terms are unclear, mark `needs_review`.
- If access requires login, mark `deferred`.
- If the source forbids automated access or reuse, mark `blocked`.
- If media rights are unclear, keep the item text-only or use a neutral structured fallback.
- If rate limits are not published, use a conservative fetch schedule during the spike.
