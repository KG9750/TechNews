# Deploy the MVP on a Docker Compose Briefing Host

Status: accepted

The first version will run on an always-on Briefing Host, such as a NAS or small server, using Docker Compose. This matches the product requirement for scheduled daily runs, local archive writes, NAS/cloud sync, and private Operations Console access. Serverless hosting and GitHub Actions are not the default because they make local filesystem archives, private network storage, long-running source collection, and retryable Feishu delivery harder to reason about.

The deployment shape is one application container with mounted archive and data volumes, environment variables supplied outside git, and host-level backup/sync tooling where appropriate. The exact host path names remain deployment-specific and must be provided through environment variables.

**Tradeoffs**

- Docker Compose keeps deployment understandable and portable, but it still requires the Briefing Administrator to manage one host.
- A persistent host makes archive and SQLite storage straightforward, but it is less elastic than cloud-native managed services.
- Serverless can be revisited later if archive storage moves to object storage and scheduled jobs become shorter-lived.

**Consequences**

- The MVP should include a Compose-ready deployment path before being marked production-ready.
- Secrets must come from host configuration or `.env`, never committed files.
- Health checks should cover the scheduler, recent run status, archive write path, and Feishu delivery status.
- MVP implementation issues remain `needs-triage` until the Feishu, model, and archive spikes confirm required host configuration.
