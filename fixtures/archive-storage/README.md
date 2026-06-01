# Archive Storage Fixture

Status: Local write and failure-recording fixture
Last updated: 2026-06-01

This fixture demonstrates the Archive Package shape required by `docs/spikes/archive-storage.md` without storing full source article bodies or real storage credentials.

Contents:

- `local-archive/2026-06-01/technology/briefing.md`: human-readable archived briefing.
- `local-archive/2026-06-01/technology/briefing.html`: browser-readable archived briefing.
- `local-archive/2026-06-01/technology/metadata.json`: Archive Metadata with delivery status, model usage summary, and sync status.
- `local-archive/2026-06-01/technology/media/README.md`: media handling note.

The sample records local archive write success and a simulated remote sync failure because no real `ARCHIVE_SYNC_TARGET` is configured in this repository.
