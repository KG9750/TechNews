# Source Registry

Status: Seed
Last updated: 2026-06-02

This registry is a starting point for the Source Ingestion Spike. Feed URLs and access terms must be validated before a source is marked fully eligible.

| ID | Source | Type | URL or feed | Primary section | Secondary sections | Trust tier | Media | MVP state | Eligibility notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| src-the-verge | The Verge | public_feed | https://www.theverge.com/rss/index.xml | Technology Industry Progress | AI, Hardware, Software | mainstream | feed/page media likely | first-version | Validate feed terms; store metadata and summaries only. |
| src-techcrunch | TechCrunch | public_feed | https://techcrunch.com/feed/ | Technology Industry Progress | AI, Software, Funding and investment | mainstream | feed/page media likely | first-version | RSS terms recorded; generated-summary/feed reuse still needs owner review. |
| src-ars-technica | Ars Technica | public_feed | https://feeds.arstechnica.com/arstechnica/index | Software | Hardware, Security | mainstream | feed/page media likely | first-version | Validate feed terms; avoid storing article body. |
| src-mit-tech-review | MIT Technology Review | public_feed | https://www.technologyreview.com/feed/ | AI | Hardware, Academic Progress | mainstream | feed/page media likely | first-version | Validate feed terms; strong for AI and policy. |
| src-ieee-spectrum | IEEE Spectrum | public_feed | https://spectrum.ieee.org/rss/fulltext | Hardware | Embodied Intelligence, Academic Progress | mainstream | feed/page media likely | first-version | Validate feed terms; strong robotics/hardware source. |
| src-engadget | Engadget | public_feed | https://www.engadget.com/rss.xml | Hardware | Software, Technology Industry Progress | mainstream | feed/page media likely | first-version | Validate feed terms; consumer device coverage. |
| src-venturebeat-ai | VentureBeat AI | public_feed | https://venturebeat.com/category/ai/feed/ | AI | Technology Industry Progress | mainstream | feed/page media likely | first-version | Validate feed terms; AI product/business coverage. |
| src-infoq-ai | InfoQ AI/ML/Data Engineering | public_feed | https://feed.infoq.com/ai-ml-data-eng | Software | AI, Academic Progress | specialist | feed/page media limited | first-version | Validate feed terms; developer-focused coverage. |
| src-github-blog | GitHub Blog | public_feed | https://github.blog/feed/ | Software | AI, Security | official | page media likely | first-version | Spike validated RSS metadata normalization on 2026-06-01; validate terms and image reuse before automated MVP ingestion. |
| src-stack-overflow-blog | Stack Overflow Blog | public_feed | https://stackoverflow.blog/feed/ | Software | Technology Industry Progress | specialist | page media likely | first-version | Validate feed terms; developer ecosystem source. |
| src-rust-blog | Rust Blog | public_feed | https://blog.rust-lang.org/feed.xml | Software | Security | official | limited | first-version | Eligible for metadata-first text-only ingestion; no logo/media reuse by default. |
| src-python-insider | Python Insider | public_feed | https://feeds.feedburner.com/PythonInsider | Software | Security | official | limited | first-version | Official-ish Python release source; validate feed. |
| src-kubernetes-blog | Kubernetes Blog | public_feed | https://kubernetes.io/feed.xml | Software | Cloud and DevOps | official | page media likely | first-version | Eligible for metadata-first text-only ingestion; media needs attribution and third-party check. |
| src-cncf-blog | CNCF Blog | public_feed | https://www.cncf.io/feed/ | Software | Cloud and DevOps | official | page media likely | first-version | Official ecosystem source. |
| src-aws-whats-new | AWS What's New | public_feed | https://aws.amazon.com/about-aws/whats-new/recent/feed/ | Software | AI, Hardware | official | limited | first-version | Official release stream; high volume requires filtering. |
| src-google-ai-blog | Google AI Blog | public_feed | https://blog.google/technology/ai/rss/ | AI | Academic Progress | official | page media likely | first-version | Official AI announcements; validate feed. |
| src-google-cloud-blog | Google Cloud Blog | public_feed | https://cloudblog.withgoogle.com/rss/ | Software | AI, Cloud and DevOps | official | page media likely | first-version | Official cloud source; validate feed. |
| src-microsoft-blog | Microsoft Blog | public_feed | https://blogs.microsoft.com/feed/ | Technology Industry Progress | AI, Software | official | page media likely | first-version | Official corporate source; broad feed needs filtering. |
| src-apple-newsroom | Apple Newsroom | public_feed | https://www.apple.com/newsroom/rss-feed.rss | Hardware | Software, AI | official | official media likely | first-version | Official source; media use must follow Apple terms. |
| src-nvidia-blog | NVIDIA Blog | public_feed | https://blogs.nvidia.com/feed/ | Hardware | AI, Data center hardware | official | official media likely | first-version | Official GPU/AI infrastructure source. |
| src-huggingface-blog | Hugging Face Blog | public_feed | https://huggingface.co/blog/feed.xml | AI | Software, Open-source AI | official | page media likely | first-version | Terms evidence recorded; blog/feed reuse scope still needs owner review. |
| src-arxiv-cs-ai | arXiv cs.AI | academic_source | https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending | Academic Progress | AI | academic | paper metadata | first-version | Spike validated Atom API metadata normalization on 2026-06-01; follow arXiv API manual and conservative request pacing. |
| src-arxiv-cs-lg | arXiv cs.LG | academic_source | https://export.arxiv.org/api/query?search_query=cat:cs.LG&sortBy=submittedDate&sortOrder=descending | Academic Progress | AI | academic | paper metadata | first-version | Follow arXiv API manual and rate guidance. |
| src-arxiv-cs-ro | arXiv cs.RO | academic_source | https://export.arxiv.org/api/query?search_query=cat:cs.RO&sortBy=submittedDate&sortOrder=descending | Academic Progress | Embodied Intelligence | academic | paper metadata | first-version | Follow arXiv API manual and rate guidance. |
| src-arxiv-cs-cv | arXiv cs.CV | academic_source | https://export.arxiv.org/api/query?search_query=cat:cs.CV&sortBy=submittedDate&sortOrder=descending | Academic Progress | AI, Embodied Intelligence | academic | paper metadata | first-version | Follow arXiv API manual and rate guidance. |
| src-arxiv-cs-cl | arXiv cs.CL | academic_source | https://export.arxiv.org/api/query?search_query=cat:cs.CL&sortBy=submittedDate&sortOrder=descending | Academic Progress | AI | academic | paper metadata | first-version | Follow arXiv API manual and rate guidance. |
| src-manual-url | Manual URL Inbox | manual_url | configured by administrator | Technology Industry Progress | Any | administrator | page metadata only | first-version | Spike validated Apple Newsroom page metadata normalization on 2026-06-01; some sites may return 403/404 and need graceful failure handling. |
| src-openai-news | OpenAI News | public_feed | https://openai.com/news/ | AI | Software, Technology Industry Progress | official | official media likely | first-version | Validate whether feed/API is available; manual URL fallback acceptable. |
| src-anthropic-news | Anthropic News | public_feed | https://www.anthropic.com/news | AI | Safety, Technology Industry Progress | official | official media likely | first-version | Validate feed availability; manual URL fallback acceptable. |
| src-deepmind-blog | Google DeepMind Blog | public_feed | https://deepmind.google/discover/blog/ | AI | Academic Progress, Embodied Intelligence | official | official media likely | first-version | Validate feed availability; manual URL fallback acceptable. |
| src-meta-ai-blog | Meta AI Blog | public_feed | https://ai.meta.com/blog/ | AI | Open-source AI | official | official media likely | first-version | Validate feed availability; manual URL fallback acceptable. |
| src-robot-report | The Robot Report | public_feed | https://www.therobotreport.com/feed/ | Embodied Intelligence | Hardware, Financing | specialist | feed/page media likely | first-version | Validate feed terms; useful for robotics commercialization. |
| src-hackaday | Hackaday | public_feed | https://hackaday.com/blog/feed/ | Hardware | Software | community | feed/page media likely | deferred | Useful but noisier; validate editorial value before MVP. |
| src-hacker-news | Hacker News RSS | public_feed | https://news.ycombinator.com/rss | Software | AI, Technology Industry Progress | community | none | deferred | Community signal source; defer until ranking quality is stable. |
| src-x | X | deferred_connector | https://x.com/ | Technology Industry Progress | AI, Software, Hardware | social | platform media | deferred | Requires API/compliance review; not MVP dependency. |
| src-linkedin | LinkedIn | deferred_connector | https://www.linkedin.com/ | Technology Industry Progress | Funding and investment | social | platform media | deferred | Requires API/compliance review; not MVP dependency. |
| src-facebook | Facebook | deferred_connector | https://www.facebook.com/ | Technology Industry Progress | Any | social | platform media | deferred | Requires API/compliance review; not MVP dependency. |

## Validation Notes

- `first-version` means the source is a candidate for MVP ingestion, not that its terms are already approved.
- Sources without reliable feeds may still be handled through Manual URL Inbox during the MVP.
- Every first-version source must pass `docs/source-eligibility-checklist.md` before automated ingestion.
- Current per-source eligibility state is tracked in `docs/source-eligibility-reviews.md`.
