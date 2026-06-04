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

2. Report draft completion status:

```bash
python3 scripts/source_owner_review_decision.py --status
```

This is a read-only report. Use it to see which open decisions are still missing, invalid, ready to apply, or valid but still unresolved because they remain `needs_review`.

3. Generate missing fillable owner decision drafts for all open items:

```bash
python3 scripts/source_owner_review_decision.py --draft-all
```

This writes only missing drafts and keeps any existing partially completed decision file unchanged.
Each draft includes `current_artifact_context` so the owner can see the current review matrix row, source registry row, source access policy row, and owner queue item without switching files.

4. Refresh current artifact context in existing drafts without overwriting owner answers:

```bash
python3 scripts/source_owner_review_decision.py --refresh-context-all
```

5. Generate or refresh derived Markdown review packets for all open items:

```bash
python3 scripts/source_owner_review_decision.py --packet-all
python3 scripts/source_owner_review_decision.py --packet-index
python3 scripts/source_owner_review_decision.py --worksheet
python3 scripts/source_owner_review_decision.py --batch-plan
python3 scripts/source_owner_review_decision.py --request-packet
```

Each packet is ignored context only. Single-source packets collect the current review matrix row, source registry row, source access policy row, owner queue questions, evidence requirements, and suggested commands. The index packet groups all open items by `decision_needed` and links the generated draft/packet filenames. The worksheet gives a consolidated checklist of decision files, draft status, required evidence, owner questions, and fields to complete. The batch plan groups open decisions into access-path blockers, RSS/feed reuse, summary/media permission, and license-obligation batches so owner review can proceed in smaller passes. The request packet is the shareable owner handoff: it lists each batch's goal, default unresolved policy, source list, evidence required, owner questions, and validation commands. Complete the JSON decision files; do not edit packets, the worksheet, the batch plan, or the request packet as the source of truth.

The top-level readiness action packet can generate the same owner packet set and MVP issue packets in one pass:

```bash
python3 scripts/readiness_action_packet.py --write-source-owner-packets --write-mvp-issue-packets
```

6. To refresh one packet explicitly:

```bash
python3 scripts/source_owner_review_decision.py --packet src-the-verge
```

7. Pick an `open` item from `fixtures/source-ingestion/source-owner-review-queue.json`.
8. To refresh or create one fillable owner decision draft explicitly:

```bash
python3 scripts/source_owner_review_decision.py --draft src-the-verge
```

This writes an ignored file under:

```text
evidence/source-owner-reviews/
```

Keep each decision filename matched to its `source_id`, for example `src-the-verge.decision.json` must contain `"source_id": "src-the-verge"`.

9. Collect every listed `evidence_required` item from source terms, feed/API policy, robots guidance, permissions pages, or owner/legal notes. The decision file must include exactly one `evidence_checked` entry for each required item, with no duplicates or unlisted evidence labels. Each `url_or_note` must include an `http(s)` URL or start with `internal note:`, `owner note:`, or `legal note:` and include concrete evidence detail.
10. Answer every `owner_questions` item in the generated decision file. Each answer must include concrete decision detail, such as whether use is approved, blocked, metadata-only, text-only, permission-gated, rate-limited, or still unresolved.
11. Use real ISO dates: `reviewed_at` and every evidence `checked_at` must be valid `YYYY-MM-DD` dates, and evidence `checked_at` must be on or before `reviewed_at`.
12. Replace every placeholder with concrete review text, including `reviewed_by`, owner answers, implementation guardrails, and `policy_after_decision` fields. Values such as `TBD`, `todo`, `unknown`, `pending`, `n/a`, or `placeholder` are rejected by validation even if `TEMPLATE_` is gone.
13. Fill the `artifact_updates` section with the exact Markdown table cell text that should be written back to the tracked docs.
14. Decide one outcome:
   - Keep `needs_review` if permission, license obligations, media rules, or rate limits remain unclear.
   - Move to `eligible` only when metadata-only generated summaries, access method, attribution, rate behavior, and media policy are all approved.
   - Move to `blocked` if automated access or summary reuse is disallowed.
   - Move to `deferred` if the source should remain a seed source but not an MVP production source.
15. Validate the completed decision file:

```bash
python3 scripts/source_owner_review_decision.py --validate evidence/source-owner-reviews/src-the-verge.decision.json
```

16. Validate every open owner decision after batch completion:

```bash
python3 scripts/source_owner_review_decision.py --validate-all
```

This exits non-zero until every open source has a completed, template-free decision file.

17. Preview one tracked artifact update, or preview every open decision after batch completion:

```bash
python3 scripts/source_owner_review_decision.py --apply evidence/source-owner-reviews/src-the-verge.decision.json --dry-run
python3 scripts/source_owner_review_decision.py --apply-all --dry-run
```

18. Apply one tracked artifact update, or apply every open decision after batch completion:

```bash
python3 scripts/source_owner_review_decision.py --apply evidence/source-owner-reviews/src-the-verge.decision.json
python3 scripts/source_owner_review_decision.py --apply-all
```

Batch apply validates every open decision before writing. If any decision is missing, invalid, or still contains `TEMPLATE_`, it exits non-zero without changing tracked artifacts.

17. Run `python3 scripts/check_readiness.py` before changing GitHub issue labels.

## Artifact Update Rules

When a source stays `needs_review`:

- Keep it in `fixtures/source-ingestion/source-owner-review-queue.json` with `review_status: "open"`.
- Keep `production_auto_ingestion: false` in `fixtures/source-ingestion/source-access-policy.json`.
- Keep `policy_after_decision.connector_mode` at the queued `default_connector_mode`; do not switch unresolved sources to a production connector.
- Use `scripts/source_owner_review_decision.py --apply <decision-file>` or `scripts/source_owner_review_decision.py --apply-all` to update `docs/source-eligibility-reviews.md`, `fixtures/source-ingestion/source-access-policy.json`, and `docs/source-registry.md` with the validated owner notes while keeping the queue item open.

When a source becomes `eligible`:

- Use `scripts/source_owner_review_decision.py --apply <decision-file>` or `scripts/source_owner_review_decision.py --apply-all` to update `docs/source-eligibility-reviews.md` to `eligible`, update `fixtures/source-ingestion/source-access-policy.json` to metadata-only production behavior, remove that source from `fixtures/source-ingestion/source-owner-review-queue.json`, and update `docs/source-registry.md` eligibility notes.
- Use only the source-type production metadata connector: `rss_metadata_only` for public feeds or `arxiv_api_metadata_only` for academic sources.
- Keep manual URL sources in per-item review; do not mark them `eligible` or set `production_auto_ingestion: true`.
- Keep media blocked unless source-specific media reuse is approved and attribution behavior is implemented.

When a source becomes `blocked` or `deferred`:

- Use `scripts/source_owner_review_decision.py --apply <decision-file>` or `scripts/source_owner_review_decision.py --apply-all` to update `docs/source-eligibility-reviews.md`, keep production auto-ingestion disabled in `fixtures/source-ingestion/source-access-policy.json`, update `docs/source-registry.md` notes, and remove it from the open owner queue once the decision is recorded.
- Keep `policy_after_decision.connector_mode` at the queued `default_connector_mode`; blocked and deferred outcomes must not introduce production connector modes.

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
- `scripts/source_owner_review_decision.py` exists and supports listing open reviews, reporting draft status, drafting ignored decision files with current artifact context, generating ignored Markdown review packets, a packet index, and a consolidated owner worksheet, refreshing context in existing drafts, validating one or all completed decisions, and applying one or all validated decisions to tracked artifacts.
- `scripts/source_owner_review_decision.py` also supports an ignored owner request packet for batching decision requests without treating the packet as the source of truth.
- `scripts/test_source_owner_review_decision.py` verifies that drafts include current artifact context, that generated packets include review context and commands, that the packet index groups open items by decision type and links draft/packet filenames, that the worksheet lists decision fields and per-source prompts, that context refresh preserves owner answers, that status reports template drafts as invalid and completed drafts as valid, that batch draft generation covers every open item without overwriting existing drafts, that packet generation covers every open item, that batch validation fails template drafts and passes completed open-review decisions, that batch apply refuses template drafts without writing, that batch apply dry-run does not write, that batch apply can update completed open-review decisions, that `blocked` decisions close queue items, and that `needs_review` decisions keep queue items open while updating copied artifacts.
- `scripts/test_source_owner_review_decision.py` also verifies that the batch plan groups all open items by review workstream, links the ignored decision and packet files for each source, and that the request packet groups source-owner prompts into shareable owner batches.
