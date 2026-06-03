# Source Ingestion Spike

Status: Completed
Owner: Briefing Administrator

## Goal

Prove that First-Version Sources can be normalized into `CandidateItem` records without storing full source article bodies.

## Inputs

- Minimal contracts: `docs/schemas/minimal-contracts.md`
- Source registry: `docs/source-registry.md`
- Eligibility checklist: `docs/source-eligibility-checklist.md`
- Connector enforcement policy: `fixtures/source-ingestion/source-access-policy.json`
- Owner review queue: `fixtures/source-ingestion/source-owner-review-queue.json`

## Source Types To Prove

- RSS or Atom public feed.
- Academic source, starting with arXiv API queries.
- Manually added URL using page metadata.

## Questions To Answer

- Which feed formats and metadata fields appear in selected sources?
- Which sources expose source media through feed metadata or page metadata?
- Which sources require custom parsing or should be deferred?
- What access policy, rate limit, or storage constraint applies per source?
- What deduplication keys are reliable across duplicate coverage?

## Verification Checklist

- [x] One public feed item normalizes to a CandidateItem.
- [x] One academic item normalizes to a CandidateItem.
- [x] One manual URL normalizes to a CandidateItem.
- [x] Every sample has `source_name`, `original_title`, `source_url`, `discovered_at`, `source_type`, and eligibility state.
- [x] No sample stores full article body text.
- [x] Every first-version source has a machine-readable access policy row that blocks production auto-ingestion while `needs_review`.
- [x] Every `needs_review` first-version source has an owner review queue item with required evidence and decision questions.

## Evidence To Attach

- Redacted raw feed/API/page metadata: see "Observed Metadata Snippets".
- Normalized CandidateItem examples: see `fixtures/source-ingestion/candidate-items.json`.
- Notes on failed or deferred sources: see "Findings".

## Run Summary

Run time: 2026-06-01T06:03:12Z

Validated source types:

| Source type | Source | Result |
| --- | --- | --- |
| `public_feed` | GitHub Blog RSS | Success. RSS feed returned `application/rss+xml` with item title, link, pubDate, categories, and description metadata. |
| `academic_source` | arXiv API `cat:cs.AI` | Success. API returned `application/atom+xml` with entry title, id URL, published timestamp, authors, categories, and summary metadata. |
| `manual_url` | Apple Newsroom M4 page | Success. HTML metadata returned title, description, canonical URL, Open Graph image, and site name. |

## Observed Metadata Snippets

These snippets are metadata-only and intentionally omit full article bodies.

### Public Feed: GitHub Blog RSS

```json
{
  "content_type": "application/rss+xml",
  "feed_title": "The GitHub Blog",
  "title": "Still a developer. Just outside. Our latest GitHub Shop collection is here.",
  "link": "https://github.blog/news-insights/company-news/still-a-developer-just-outside-our-latest-github-shop-collection-is-here/",
  "pubDate": "Thu, 28 May 2026 18:18:43 +0000",
  "categories": ["Company news", "News & insights", "GitHub Shop"],
  "description_excerpt": "The ESC collection lets you escape the confines of your desk and get out into the sun where good ideas are bound to happen..."
}
```

### Academic Source: arXiv API

```json
{
  "content_type": "application/atom+xml",
  "feed_title": "arXiv Query: search_query=cat:cs.AI&id_list=&start=0&max_results=1",
  "title": "Lumos-Nexus: Efficient Frequency Bridging with Homogeneous Latent Space for Video Unified Models",
  "id": "http://arxiv.org/abs/2605.31603v1",
  "published": "2026-05-29T17:59:50Z",
  "authors": ["Jiazheng Xing", "Hangjie Yuan", "Lingling Cai", "Xinyu Liu", "Yujie Wei"],
  "categories": ["cs.CV", "cs.AI"],
  "summary_excerpt": "Connector-based video unified models have demonstrated strong capability in instruction-grounded video synthesis..."
}
```

### Manual URL: Apple Newsroom M4 Page

```json
{
  "content_type": "text/html",
  "title": "Apple introduces M4 chip",
  "url": "https://www.apple.com/newsroom/2024/05/apple-introduces-m4-chip/",
  "description_excerpt": "Apple today announced M4, the latest Apple-designed silicon chip delivering phenomenal performance to the all-new iPad Pro.",
  "image": "https://www.apple.com/newsroom/images/2024/05/apple-introduces-m4-chip/tile/Apple-M4-chip-badge-240507.jpg.og.jpg?202605131928",
  "site_name": "Apple Newsroom"
}
```

## Normalization Findings

- RSS public feeds can be normalized from `title`, `link`, `pubDate`, `category`, and `description` metadata without storing full article body.
- arXiv API Atom entries can be normalized from `title`, `id`, `published`, `author`, `category`, and `summary` metadata.
- Manual URLs can use HTML title, canonical/Open Graph URL, description, site name, and Open Graph image metadata.
- `dedupe_key` can start as `source_id|canonical_url` for exact duplicate detection.
- `event_key` should be assigned later by ranking/model logic when multiple sources cover the same event.
- Source media must remain conditional: the Apple Newsroom page exposed Open Graph image metadata, while the GitHub RSS item and arXiv API item did not provide a source media object for display.

## Failed Or Deferred Observations

- `https://openai.com/index/hello-gpt-4o/` returned HTTP 403 to the metadata-only script. Manual URL ingestion needs graceful failure status and may require browser/manual metadata fallback for some protected sites.
- `https://huggingface.co/blog/lerobot` returned HTTP 404 during this run, so that golden sample URL should be reviewed before it is used as a live ingestion fixture.
- Sources with unclear terms remain `needs_review` in the registry until the source eligibility checklist is completed.
- `fixtures/source-ingestion/source-access-policy.json` turns the review matrix into implementation-facing defaults: 7 eligible metadata-only sources are production-enabled, while 25 `needs_review` sources are locked to probe/manual modes until owner review clears them.
- `fixtures/source-ingestion/source-owner-review-queue.json` turns those 25 open reviews into owner decision items so they can be resolved without weakening the default connector policy.
- `scripts/source_owner_review_decision.py` can list open source reviews, report draft status, draft ignored owner-decision files, generate ignored review packets and a packet index, refresh current artifact context in existing drafts, validate completed decisions, and apply validated decisions to the review matrix, access policy, owner queue, and registry notes.

## Contract Notes

The examples use the field names from `docs/schemas/minimal-contracts.md`. No new required fields were discovered during this spike.

## Official References

- arXiv API access: https://info.arxiv.org/help/api/index.html
- arXiv API user manual: https://info.arxiv.org/help/api/user-manual.html
