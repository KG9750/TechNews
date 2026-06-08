# MVP: Implement briefing generation, Deep-Dive Detail, and Confidence Notices

## Problem

The MVP needs Feishu-friendly Chinese Push Briefings and archived Deep-Dive Details that stay grounded in source metadata.

## Scope

- Generate one-sentence Chinese titles and three to four compact bullets.
- Group items by Briefing Section and Section Subcategory.
- Include Original Source Anchors for every item.
- Include Confidence Notices for medium and low confidence items.
- Include Source Media attribution when eligible media is displayed.
- Generate static Deep-Dive Detail content for archived items.
- Include non-misleading structured fallback when no source media exists.

## Out of scope

- AI chat over briefing items.
- AI-generated news imagery.
- Exact wording tests for model-generated prose.

## Acceptance criteria

- Generated items follow `docs/briefing-style-guide.md`.
- Low and medium confidence items include visible Confidence Notices.
- Source links and media attribution are never invented.
- Deep-Dive Detail can be opened from an archived item.
- Items without media do not use misleading generated art.

## Test expectations

- Contract tests for generated `BriefingItem` fields.
- Golden-sample checks for high-confidence, low-confidence, academic, source-media, and no-media cases.
- Tests assert structure, source preservation, confidence notices, and media rules.

## Relevant docs

- `docs/briefing-style-guide.md`
- `fixtures/model-provider/prompt-contract.md`
- `fixtures/model-provider/outputs/`
- `fixtures/golden-samples/items.json`
- `docs/adr/0007-model-provider-boundary.md`

## Dependencies

- Live model-provider spike (#5) and Feishu card rendering evidence (#3) are complete.

## Triage label

`ready-for-agent`
