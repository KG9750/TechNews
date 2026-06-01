# TechNews Briefing PRD

Status: Draft
Last updated: 2026-06-01

This PRD uses the product language defined in [CONTEXT.md](../CONTEXT.md).

## Problem Statement

The user wants a reliable daily briefing application that can collect important technology news from selected global sources, condense it into a Perplexity-like visual briefing, push it to Feishu at a fixed time, and preserve each day's briefing locally and on cloud/NAS storage.

Today this work would require repeatedly checking public media, academic sources, company announcements, newsletters, and selected social links by hand. The user needs a system that can make the daily scan automatic while keeping the output verifiable through source links, source media, selection rationales, and confidence notices.

## Solution

Build a configurable daily briefing system that runs on an always-on Briefing Host, performs Curated Source Aggregation from First-Version Sources, ranks Candidate Items by Editorial Importance, generates a Chinese Push Briefing for approved Briefing Recipients, and writes a complete Archived Briefing as an Archive Package.

The MVP is quality-first and fully automatic. It sends at the configured Delivery Deadline even if some Source Connectors are late or incomplete. Lower-confidence items may still be pushed, but they must carry a visible Confidence Notice with source evidence and uncertainty.

The first Domain Template is technology news. It includes Briefing Sections such as AI, software, hardware, embodied intelligence, academic progress, and technology industry progress. Each section can contain Section Subcategories, and each Briefing Recipient can subscribe to the sections and subcategories they care about.

## User Stories

1. As a Briefing Administrator, I want to configure trusted public media sources, so that the daily briefing uses a controlled source base.
2. As a Briefing Administrator, I want to configure academic sources, so that papers and research updates can appear beside industry news.
3. As a Briefing Administrator, I want to manually add a URL, so that a relevant item can enter the next briefing even when it is not in a feed.
4. As a Briefing Administrator, I want social media and commercial news APIs to be Deferred Source Connectors, so that they can be added later without reshaping the product.
5. As a Briefing Administrator, I want to define a technology Domain Template, so that technology news has a stable taxonomy.
6. As a Briefing Administrator, I want to manage Briefing Sections such as AI, software, hardware, embodied intelligence, academic progress, and technology industry progress, so that the briefing can match my interests.
7. As a Briefing Administrator, I want to manage Section Subcategories such as robot body, data collection, model training, recent papers, and financing, so that embodied intelligence coverage is specific enough to be useful.
8. As a Briefing Administrator, I want to approve Briefing Recipients, so that only selected Feishu users or groups receive push briefings.
9. As a Briefing Administrator, I want each Briefing Recipient to have a Recipient Subscription, so that different users or groups can receive different sections.
10. As a Briefing Administrator, I want to configure a Delivery Deadline, so that the system sends the briefing at a predictable time each day.
11. As a Briefing Recipient, I want the briefing to arrive at a fixed daily time, so that it becomes part of my routine.
12. As a Briefing Recipient, I want the Push Briefing to contain only the most important items, so that I can scan it quickly in Feishu.
13. As a Briefing Recipient, I want each briefing item to have a one-sentence title and three to four concise bullets, so that I can understand the point without opening every source.
14. As a Briefing Recipient, I want briefing items grouped by Briefing Section, so that I can jump to the areas I care about.
15. As a Briefing Recipient, I want important low-confidence items to include a Confidence Notice, so that I can interpret them cautiously.
16. As a Briefing Recipient, I want every item to retain an Original Source Anchor, so that I can verify the summarized source material.
17. As a Briefing Recipient, I want source images or structured visual metadata when available, so that the briefing is visually scannable without using misleading generated art.
18. As a Briefing Recipient, I want image sources to be attributed, so that I know where the visual material came from.
19. As a Briefing Recipient, I want to open a Deep-Dive Detail for an item, so that I can see richer context, source lists, related items, and selection rationale.
20. As a Briefing Recipient, I want Related History on follow-up stories, so that I understand whether a story continues an earlier event.
21. As a Briefing Recipient, I want summaries in Chinese by default, so that the briefing is immediately readable.
22. As a Briefing Recipient, I want original titles and source links preserved, so that I can inspect the original language and source.
23. As a Briefing Administrator, I want the system to create an Archived Briefing every day, so that the daily output is not lost after the Feishu push.
24. As a Briefing Administrator, I want each Archive Package to include readable HTML or Markdown, so that people can browse old briefings without a special client.
25. As a Briefing Administrator, I want each Archive Package to include structured Archive Metadata, so that selection, confidence, and delivery decisions can be audited.
26. As a Briefing Administrator, I want archives stored locally and synced to cloud/NAS storage, so that briefings survive local device failure.
27. As a Briefing Administrator, I want the Operations Console to show briefing run status, so that I can see whether today's run succeeded.
28. As a Briefing Administrator, I want the Operations Console to show Source Connector health, so that broken sources can be fixed without reading logs first.
29. As a Briefing Administrator, I want the Operations Console to show which Candidate Items were selected or excluded, so that the Editorial Importance behavior can be inspected.
30. As a Briefing Administrator, I want a simple administrator-protected console, so that first-version setup is protected without building a full account system.
31. As a Briefing Administrator, I want the Model Provider to be configurable, so that the first implementation can use one stable cloud provider while leaving room for later changes.
32. As a Briefing Administrator, I want a Quality-First Run, so that the first version optimizes for useful output rather than cost caps.
33. As a product owner, I want technology news to be only the first Domain Template, so that the same system can later support political economy or other domains.
34. As a product owner, I want the MVP to exclude full-network scraping, so that the first version remains stable, legal, and maintainable.
35. As a product owner, I want AI chat and full event tracking to remain out of scope, so that the first version can ship around a reliable daily briefing loop.

## Implementation Decisions

- The first release uses Curated Source Aggregation, not global web crawling.
- First-Version Sources are public site feeds, academic sources, and manually added URLs.
- X, Facebook, LinkedIn, and commercial news APIs are Deferred Source Connectors.
- The first Domain Template is technology news.
- Briefing Sections and Section Subcategories are centrally managed in the Domain Template.
- Briefing Recipients can be Feishu users or Feishu groups.
- Recipient Subscriptions control which templates, sections, and subcategories appear for each recipient.
- The system performs Automatic Briefing Runs without manual approval.
- The Delivery Deadline takes priority over waiting for every Source Connector to complete.
- Editorial Importance is explainable and based on source trust, impact, timeliness, corroboration, subscribed sections, and original-material availability.
- Briefing Preferences can adjust section selection and ordering, but they do not replace Editorial Importance.
- Low-confidence items may be pushed, but only with a visible Confidence Notice.
- Push Briefings are short Feishu-friendly entries, not full reports.
- Archived Briefings are the complete daily record.
- Deep-Dive Detail is static in the MVP and does not include AI chat.
- Related History is lightweight and does not become full event lifecycle tracking.
- Output Language defaults to Chinese.
- Each briefing item keeps an Original Source Anchor.
- Source Media must come from the source, an official entity page, a paper page, or structured site metadata.
- AI-generated news imagery is out of scope.
- Archive Packages contain readable briefing files, structured metadata, and attributed media.
- Archive Metadata includes Candidate Item metadata, source links, Selection Rationales, Confidence Notices, and delivery status.
- The Operations Console is for configuration and operations, not a full reading application.
- The first version has a single Briefing Administrator model rather than a full role matrix.
- The Briefing Host is expected to be a NAS or always-on small server.
- The Model Provider is configurable, with one stable cloud provider implemented first.
- The first version is Quality-First and does not enforce cost budgets or automatic cost-based model degradation.

## Testing Decisions

- Test at product seams first: complete briefing run, source ingestion, candidate selection, archive creation, Feishu delivery, and Operations Console workflows.
- Use source fixtures for public feeds, academic items, and manually added URLs.
- Verify that the system can generate a Push Briefing at the Delivery Deadline when one Source Connector is slow or unavailable.
- Verify that low-confidence selected items include a Confidence Notice and supporting sources.
- Verify that each briefing item has an Original Source Anchor.
- Verify that Source Media is attributed and that generated news art is not used.
- Verify that Archive Packages contain readable output, structured metadata, and media assets.
- Verify that Archive Metadata contains selected and excluded Candidate Items with Selection Rationales.
- Verify that each Briefing Recipient receives only the sections and subcategories in its Recipient Subscription.
- Verify that the Operations Console can show run status, source health, recipient configuration, and archive links.
- Avoid tests that assert exact AI wording. Assert structure, required fields, source references, confidence notices, and acceptance thresholds instead.
- Add manual review for generated briefing quality during early development, even though the product run is automatic.

## Out of Scope

- Full-network crawling or scraping.
- Required first-version support for X, Facebook, LinkedIn, or commercial news aggregation APIs.
- AI-generated news images.
- AI chat over briefing items.
- Full event lifecycle tracking or automatic topic pages.
- Full reading application or content community.
- Complete multi-user account and role system.
- Fine-grained cost dashboards, cost caps, or automatic low-cost mode.
- Default storage of complete source article text.
- Complex recommendation models based on long-term behavior.
- Publishing to channels other than Feishu.

## Further Notes

- Exact Feishu API capabilities, card formats, and delivery constraints should be verified before implementation.
- Exact source licensing and acceptable storage behavior should be checked before saving excerpts beyond metadata and summaries.
- Social media integrations require a separate compliance and API review before becoming First-Version Sources.
- The next useful product decision is the initial technology Domain Template taxonomy and the first seed list of sources.
