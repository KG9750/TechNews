# Source Ingestion Spike

Status: Not started
Owner: Briefing Administrator

## Goal

Prove that First-Version Sources can be normalized into `CandidateItem` records without storing full source article bodies.

## Inputs

- Minimal contracts: `docs/schemas/minimal-contracts.md`
- Source registry: `docs/source-registry.md`
- Eligibility checklist: `docs/source-eligibility-checklist.md`

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

- One public feed item normalizes to a CandidateItem.
- One academic item normalizes to a CandidateItem.
- One manual URL normalizes to a CandidateItem.
- Every sample has `source_name`, `original_title`, `source_url`, `discovered_at`, `source_type`, and eligibility state.
- No sample stores full article body text.

## Evidence To Attach

- Redacted raw feed/API/page metadata.
- Normalized CandidateItem examples.
- Notes on failed or deferred sources.

## Official References

- arXiv API access: https://info.arxiv.org/help/api/index.html
- arXiv API user manual: https://info.arxiv.org/help/api/user-manual.html
