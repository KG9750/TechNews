# Store operational data in SQLite for the MVP

Status: accepted

The MVP will use SQLite for operational data: sources, recipient whitelist entries, subscriptions, run records, connector status, selected/excluded Candidate Items, delivery status, sync status, and model usage metadata. Archive Packages remain file-based artifacts and are not stored inside SQLite.

SQLite is the right first-version tradeoff because the product starts as a single-host automation system with one administrator and a small number of daily runs. PostgreSQL or another external database would add deployment and backup work before there is evidence that concurrent multi-user writes or large query volumes are needed.

**Tradeoffs**

- SQLite is simple and reliable for one-host operation, but it is not the right long-term choice for multi-host scaling.
- Keeping archives as files preserves readable daily records, but queries over historical archives may later need indexing.
- A local database is easy to back up with the host, but corruption and filesystem permissions need explicit operational checks.

**Consequences**

- The Operations Console should read run state and configuration from SQLite.
- Archive Metadata should duplicate the audit-critical facts needed to understand a run even if the database is unavailable.
- Secrets must not be stored in SQLite; only secret references, redacted status, or provider names may be stored.
- A future search feature can add an index over Archive Metadata without replacing SQLite immediately.
