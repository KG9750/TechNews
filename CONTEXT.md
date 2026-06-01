# TechNews Briefing

This context defines the product language for a configurable daily briefing that turns selected technology news sources into concise, push-ready briefings.

## Language

**Curated Source Aggregation**:
The first-version coverage model: a controlled set of trusted public media, academic sources, and manually whitelisted URLs used to produce the daily briefing.
_Avoid_: Global web crawl, full-network scraping

**Source Connector**:
A source-specific way to bring eligible articles, posts, or papers into the briefing pipeline.
_Avoid_: Scraper, crawler

**Editorial Importance**:
An explainable measure of whether an item deserves briefing space, based on source trust, event impact, timeliness, corroboration, subscribed sections, and original-material availability.
_Avoid_: Viral score, black-box recommendation

**Briefing Preference**:
A lightweight user or team setting that adjusts section selection and ordering without replacing editorial importance.
_Avoid_: Personalization model, feed algorithm

**Push Briefing**:
The short daily version delivered to Feishu, optimized for fast scanning and entry into deeper content.
_Avoid_: Full report, article dump

**Archived Briefing**:
The complete daily version saved locally and to cloud storage, containing the full section structure, images, summaries, source links, and deep-dive content.
_Avoid_: Backup copy, raw export

**Archive Package**:
A date-based briefing archive containing readable briefing files, structured metadata, and attributed media assets.
_Avoid_: Database row, opaque backup

**Archive Metadata**:
The structured record for a briefing run, including candidate item metadata, source links, selection rationales, confidence notices, and delivery status.
_Avoid_: Full source copy, hidden logs

**Briefing Host**:
The always-on machine responsible for scheduled briefing runs, archive package creation, storage sync, and Feishu delivery, with NAS or a small server as the first-version target.
_Avoid_: Personal laptop, cloud-only backend

**Domain Template**:
A reusable briefing taxonomy for one coverage domain, such as technology news or political economy news.
_Avoid_: Category set, topic preset

**Briefing Section**:
A top-level area inside a domain template, such as AI, software, hardware, embodied intelligence, academic progress, or technology industry progress.
_Avoid_: Channel, column

**Section Subcategory**:
A finer-grained classification inside a briefing section, such as robot body, data collection, model training, recent papers, or financing under embodied intelligence.
_Avoid_: Tag, label

**Recipient Subscription**:
A user or Feishu group setting that chooses which domain templates, sections, and subcategories appear in its push briefing.
_Avoid_: White-list rule, audience segment

**Briefing Recipient**:
A Feishu user or Feishu group approved to receive push briefings.
_Avoid_: Whitelist entry, audience

**Output Language**:
The language used for generated briefing summaries for a recipient, with Chinese as the first-version default.
_Avoid_: Translation mode, locale

**Original Source Anchor**:
The original title and source link retained on a briefing item so readers can verify the summarized source material.
_Avoid_: Citation decoration, raw content

**Source Media**:
Images or visual metadata that come from the original source, an official entity page, a paper page, or structured site metadata.
_Avoid_: AI-generated news art, decorative illustration

**Media Attribution**:
The visible source reference attached to a briefing image or visual asset.
_Avoid_: Unlabeled image, visual filler

**Automatic Briefing Run**:
A scheduled end-to-end run that collects eligible source items, scores them, generates the push briefing and archived briefing, stores both, and delivers the push briefing without manual approval.
_Avoid_: Draft review, manual send

**Confidence Notice**:
A visible cue attached to a briefing item when evidence is limited, disputed, or lower-confidence, showing the supporting sources and uncertainty instead of hiding the risk.
_Avoid_: Silent uncertainty, internal-only confidence score

**Delivery Deadline**:
The configured daily cutoff time for sending a push briefing, even when some source connectors have not completed.
_Avoid_: Completion time, freshness target

**Candidate Item**:
A source item considered for inclusion in a briefing run, whether or not it appears in the final push briefing.
_Avoid_: Raw article, scraped content

**Selection Rationale**:
The human-readable explanation for why a candidate item was included, excluded, ranked, or marked with a confidence notice.
_Avoid_: Debug score, model trace

**Operations Console**:
A lightweight management surface for source configuration, section subscriptions, recipients, delivery schedules, briefing runs, and archived briefing review.
_Avoid_: Full reading app, content community

**Briefing Administrator**:
The person allowed to configure sources, templates, recipients, schedules, and operations console access in the first version.
_Avoid_: Team member, role matrix

**Deep-Dive Detail**:
A static expanded view for a briefing item, including richer summary, source list, event context, related candidate items, and selection rationale.
_Avoid_: AI chat, topic tracker

**Related History**:
A lightweight link from a briefing item to earlier archived items about the same event or closely related topic.
_Avoid_: Event lifecycle, topic tracker

**Model Provider**:
The configurable AI service used to classify, summarize, translate, rank, and generate confidence notices, with one stable cloud provider as the first-version implementation.
_Avoid_: Hard-coded model, local-only AI

**Quality-First Run**:
A briefing run that prioritizes output quality and end-to-end reliability without first-version budget caps or automatic cost-based degradation.
_Avoid_: Budgeted run, low-cost mode

**First-Version Source**:
A source type required for the first release, limited to public site feeds, academic sources, and manually added URLs.
_Avoid_: Everything source, platform-wide feed

**Deferred Source Connector**:
A source connector reserved for later expansion, such as social media posts or commercial news aggregation APIs.
_Avoid_: MVP dependency, required source
