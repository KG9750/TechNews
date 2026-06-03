# Technology Domain Template

Status: Reviewed for model spike
Last updated: 2026-06-03

This is the first Domain Template for TechNews Briefing. It defines the MVP Briefing Sections and Section Subcategories used by classification, Recipient Subscriptions, Push Briefings, and Archive Packages.

## Output Contract

Every classified CandidateItem must use:

- One primary `section`.
- Zero or one primary `subcategory`.
- Up to two `secondary_sections` when helpful for archive/search context.
- A short classification rationale when section choice is not obvious.

Use the section and subcategory names exactly as written below.

## Sections And Subcategories

| Section | Subcategories |
| --- | --- |
| AI | Foundation models; Multimodal AI; AI agents; AI infrastructure; Evaluation and safety; AI applications; Open-source AI |
| Software | Developer tools; Programming languages; Cloud and DevOps; Security; Databases and data systems; Open-source projects; SaaS platforms |
| Hardware | Semiconductors; AI accelerators; Data center hardware; Consumer devices; Manufacturing and supply chain; Networking and connectivity; Energy and cooling |
| Embodied Intelligence | Robot body; Data collection; Model training; Recent papers; Financing; Deployment and pilots; Simulation and evaluation |
| Academic Progress | AI papers; Robotics papers; Systems papers; Hardware research; Datasets and benchmarks; Research institutions; Reproducibility and evaluation |
| Technology Industry Progress | Funding and investment; M&A and partnerships; Regulation and policy; Antitrust and litigation; Earnings and market signals; Talent and organization; Platform strategy |

## AI

Use for model releases, AI infrastructure, agents, evaluation, safety, productization, and major AI research that is not primarily academic-paper coverage.

Include:

- New model releases, benchmark shifts, developer tools, major product integrations, and material safety or policy changes.

Exclude:

- Physical-world robot embodiment, which belongs under Embodied Intelligence.
- Papers without immediate product or industry relevance, which usually belong under Academic Progress.

Examples:

- GPT-4o release -> AI / Multimodal AI
- Llama open model release -> AI / Open-source AI
- AI coding workspace -> Software / Developer tools, with AI as secondary section

## Software

Use for developer platforms, programming languages, cloud-native systems, security, databases, open source, and SaaS infrastructure.

Include:

- Releases, incidents, ecosystem changes, major vulnerabilities, platform policy changes, and developer workflow shifts.

Exclude:

- Hardware product launches unless the main impact is software platform strategy.

Examples:

- Kubernetes release -> Software / Cloud and DevOps
- Rust release -> Software / Programming languages
- CrowdStrike outage guidance -> Software / Security, with Technology Industry Progress as secondary section

## Hardware

Use for chips, devices, data centers, consumer electronics, manufacturing, supply chain, and infrastructure hardware.

Include:

- Chip announcements, device launches, data center capacity, manufacturing process news, and strategic hardware partnerships.

Exclude:

- Robot body design, which belongs under Embodied Intelligence.

Examples:

- NVIDIA accelerator platform -> Hardware / AI accelerators
- Apple M-series chip -> Hardware / Semiconductors
- Copilot+ PC platform -> Hardware / Consumer devices, with AI as secondary section

## Embodied Intelligence

Use for robotics, autonomous agents in the physical world, data collection for robot learning, robot models, and related commercialization.

Include:

- Humanoid robots, robot foundation models, teleoperation datasets, sim-to-real work, manipulation, navigation, and financing for robotics companies.

Exclude:

- General AI model releases with no physical-world embodiment.

Examples:

- Unitree humanoid robot page -> Embodied Intelligence / Robot body
- Robot dataset or teleoperation pipeline -> Embodied Intelligence / Data collection
- Robotics model-training toolkit -> Embodied Intelligence / Model training

## Academic Progress

Use for papers, preprints, conference results, research benchmarks, datasets, and notable lab publications.

Include:

- arXiv papers, institutional research posts, benchmark datasets, and conference highlights.

Exclude:

- Company product launches based on research unless the research contribution is the main story.

Examples:

- arXiv AI paper -> Academic Progress / AI papers
- Robotics preprint -> Academic Progress / Robotics papers, with Embodied Intelligence as secondary section
- Benchmark dataset -> Academic Progress / Datasets and benchmarks

## Technology Industry Progress

Use for company strategy, regulation, financing, M&A, antitrust, hiring, market structure, platform competition, and major business outcomes.

Include:

- Large funding rounds, acquisitions, regulatory decisions, strategic partnerships, earnings that affect technology direction, and platform policy shifts.

Exclude:

- Technical releases that are better understood as AI, Software, Hardware, Embodied Intelligence, or Academic Progress.

Examples:

- Robotics funding round -> Technology Industry Progress / Funding and investment, with Embodied Intelligence as secondary section
- AI regulation decision -> Technology Industry Progress / Regulation and policy
- Major platform partnership -> Technology Industry Progress / M&A and partnerships

## Classification Rules

- Prefer the section that explains why the item matters to a technology briefing reader.
- Assign the most specific primary section first; use Technology Industry Progress only when business, policy, financing, or market structure is the main point.
- For academic papers, use Academic Progress as primary unless the paper is mainly being discussed as product, deployment, or company strategy.
- For robotics papers, use Academic Progress as primary and Embodied Intelligence as secondary unless the item is about deployment, productization, or financing.
- For AI-enabled hardware, use Hardware as primary when the news is about chips/devices and AI as secondary when model capability is context.
- For duplicate coverage, classify the event once and preserve multiple Original Source Anchors in Archive Metadata.
- If classification confidence is low, keep the best primary section and require a Selection Rationale explaining uncertainty.

## MVP Readiness Check

- Each MVP section has at least three subcategories.
- Embodied Intelligence includes Robot body, Data collection, Model training, Recent papers, and Financing.
- Section names match PRD and MVP scope language.
- This template is ready for the Model Provider Spike as the canonical classification vocabulary.
- `python3 scripts/check_readiness.py` verifies MVP sections, minimum subcategory coverage, and Embodied Intelligence required subcategories.
