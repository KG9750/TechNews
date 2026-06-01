# MVP: Implement taxonomy and source registry configuration

## Problem

The MVP needs editable but controlled configuration for the technology Domain Template and First-Version Sources.

## Scope

- Load the technology Domain Template and Section Subcategories from configuration or seed data.
- Load First-Version Sources from a registry with source type, trust level, section hints, media availability, and eligibility notes.
- Support public feeds, academic sources, and manual URLs as first-version source types.
- Keep deferred social and commercial sources visible but inactive.

## Out of scope

- Implementing live source connector fetch logic.
- Adding production social media ingestion.
- Creating a full multi-domain management system.

## Acceptance criteria

- All MVP Briefing Sections and at least three subcategories per section are available to the application.
- Embodied Intelligence includes robot body, data collection, model training, recent papers, and financing.
- At least 30 seed sources can be loaded with first-version/deferred state.
- Deferred sources cannot be accidentally run as first-version connectors.

## Test expectations

- Unit tests for taxonomy loading and required subcategory coverage.
- Registry validation for first-version/deferred state and eligibility notes.
- Fixture or snapshot test proving the configured technology template matches `docs/taxonomy/technology-domain-template.md`.

## Relevant docs

- `docs/taxonomy/technology-domain-template.md`
- `docs/source-registry.md`
- `docs/source-eligibility-checklist.md`
- `docs/PRD.md`

## Dependencies

- Source registry owner review remains useful before marking this `ready-for-agent`.

## Triage label

`needs-triage`
