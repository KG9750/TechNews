# MVP Scope

Status: Active scope - readiness inputs pending
Last updated: 2026-06-04

## MVP Goal

Ship a fully automatic daily technology briefing loop that collects from controlled sources, creates a Feishu-friendly Push Briefing, stores a complete Archive Package, and lets a Briefing Administrator operate the system from a lightweight Operations Console.

## Success Criteria

- A scheduled Automatic Briefing Run starts each day on the Briefing Host.
- The Push Briefing is sent to configured Briefing Recipients at the Delivery Deadline.
- Each pushed item has a concise title, three to four summary bullets, section placement, source link, and confidence state.
- Low-confidence items are still allowed, but each one includes a visible Confidence Notice.
- Each day creates an Archive Package with readable briefing files, Archive Metadata, and media assets.
- The Operations Console shows source configuration, recipient subscriptions, delivery schedule, run status, and archive links.
- The system can run from a NAS or always-on small server.

## In Scope

- Technology news as the first Domain Template.
- Briefing Sections for AI, software, hardware, embodied intelligence, academic progress, and technology industry progress.
- Section Subcategories, including embodied intelligence subcategories such as robot body, data collection, model training, recent papers, and financing.
- First-Version Sources: public site feeds, academic sources, and manually added URLs.
- Source Connector abstraction for future source types.
- Editorial Importance scoring with explainable Selection Rationales.
- Recipient Subscriptions for Feishu users and Feishu groups.
- Chinese Output Language by default.
- Original Source Anchors for every briefing item.
- Source Media and Media Attribution when available.
- Static Deep-Dive Detail for selected items.
- Lightweight Related History for follow-up context.
- Archive Package format containing readable files, structured metadata, and media.
- Local storage plus cloud/NAS sync target.
- Administrator-protected Operations Console.
- Configurable Model Provider with one cloud provider implemented first.
- Quality-First Run behavior without cost caps.

## Out of Scope

- Global web crawling.
- First-version social media ingestion from X, Facebook, or LinkedIn.
- First-version commercial news API dependency.
- AI-generated news imagery.
- AI chat for follow-up questions.
- Full event tracking, topic lifecycle, or persistent topic pages.
- Full reader-facing Web App.
- Full multi-user identity and role management.
- Cost budget enforcement, model routing, or automatic degradation.
- Complete source-text storage by default.
- Multi-domain production support beyond proving the Domain Template structure can support other domains later.

## MVP Acceptance Checklist

- Configure at least one source in each First-Version Source type.
- Run a complete Automatic Briefing Run from source collection to Feishu delivery.
- Demonstrate that a late Source Connector does not block Delivery Deadline delivery.
- Produce a Push Briefing for at least one Feishu user and one Feishu group.
- Produce an Archived Briefing for the same run.
- Open a Deep-Dive Detail from an archived item.
- Show a low-confidence item with a Confidence Notice.
- Show Source Media with attribution when source media exists.
- Show an item without source media using a non-misleading structured fallback.
- Show Related History for a repeated or follow-up item.
- Show run status and delivery status in the Operations Console.

## Readiness Inputs Still Needed Before Build

- Exact daily Delivery Deadline.
- Approved Feishu user and group recipients, app credentials, and live internal-app delivery evidence.
- First Model Provider selection, API credentials, and live structured-output usage evidence.
- Local archive path, NAS/cloud sync target, and live sync success evidence.
- Source-owner approvals, blocking, deferral, or MVP source-set narrowing for the `needs_review` sources tracked by issue #21.
- Final MVP source set confirmation after source-owner approvals are applied.
