# Technology Domain Template

Status: Draft
Last updated: 2026-06-01

This is the first Domain Template for TechNews Briefing. It defines the MVP Briefing Sections and Section Subcategories used by classification, subscriptions, and archive organization.

## AI

Use for model releases, AI infrastructure, agents, evaluation, safety, productization, and major AI research that is not primarily academic-paper coverage.

Subcategories:

- Foundation models
- Multimodal AI
- AI agents
- AI infrastructure
- Evaluation and safety
- AI applications
- Open-source AI

Include:

- New model releases, benchmark shifts, developer tools, major product integrations, and material safety or policy changes.

Exclude:

- Pure robotics embodiment work, which belongs under Embodied Intelligence.
- Papers without immediate industry relevance, which usually belong under Academic Progress.

## Software

Use for developer platforms, programming languages, cloud-native systems, security, databases, open source, and SaaS infrastructure.

Subcategories:

- Developer tools
- Programming languages
- Cloud and DevOps
- Security
- Databases and data systems
- Open-source projects
- SaaS platforms

Include:

- Releases, incidents, ecosystem changes, major vulnerabilities, platform policy changes, and developer workflow shifts.

Exclude:

- Hardware product launches unless the main impact is software platform strategy.

## Hardware

Use for chips, devices, data centers, consumer electronics, manufacturing, supply chain, and infrastructure hardware.

Subcategories:

- Semiconductors
- AI accelerators
- Data center hardware
- Consumer devices
- Manufacturing and supply chain
- Networking and connectivity
- Energy and cooling

Include:

- Chip announcements, device launches, data center capacity, manufacturing process news, and strategic hardware partnerships.

Exclude:

- Robot body design, which belongs under Embodied Intelligence.

## Embodied Intelligence

Use for robotics, autonomous agents in the physical world, data collection for robot learning, robot models, and related commercialization.

Subcategories:

- Robot body
- Data collection
- Model training
- Recent papers
- Financing
- Deployment and pilots
- Simulation and evaluation

Include:

- Humanoid robots, robot foundation models, teleoperation datasets, sim-to-real work, manipulation, navigation, and financing for robotics companies.

Exclude:

- General AI model releases with no physical-world embodiment.

## Academic Progress

Use for papers, preprints, conference results, research benchmarks, datasets, and notable lab publications.

Subcategories:

- AI papers
- Robotics papers
- Systems papers
- Hardware research
- Datasets and benchmarks
- Research institutions
- Reproducibility and evaluation

Include:

- arXiv papers, institutional research posts, benchmark datasets, and conference highlights.

Exclude:

- Company product launches based on research unless the research contribution is the main story.

## Technology Industry Progress

Use for company strategy, regulation, financing, M&A, antitrust, hiring, market structure, platform competition, and major business outcomes.

Subcategories:

- Funding and investment
- M&A and partnerships
- Regulation and policy
- Antitrust and litigation
- Earnings and market signals
- Talent and organization
- Platform strategy

Include:

- Large funding rounds, acquisitions, regulatory decisions, strategic partnerships, earnings that affect technology direction, and platform policy shifts.

Exclude:

- Technical releases that are better understood as AI, Software, Hardware, Embodied Intelligence, or Academic Progress.

## Classification Rules

- Prefer the section that explains why the item matters.
- Assign one primary section and at most two secondary sections.
- Use Section Subcategory only when the item clearly matches it.
- For duplicate coverage, classify the event once and preserve multiple source anchors in the archive metadata.
- If an item cannot be classified confidently, use `Technology Industry Progress` only when the business context is clear; otherwise mark for review during the source/model spike.
