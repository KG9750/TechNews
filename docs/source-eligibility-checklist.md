# Source Eligibility Checklist

Status: Draft
Last updated: 2026-06-01

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

## Conservative Defaults

- If terms are unclear, mark `needs_review`.
- If access requires login, mark `deferred`.
- If the source forbids automated access or reuse, mark `blocked`.
- If media rights are unclear, keep the item text-only or use a neutral structured fallback.
- If rate limits are not published, use a conservative fetch schedule during the spike.
