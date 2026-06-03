# Write archives locally before syncing to NAS or cloud storage

Status: accepted

Archive creation is local-first: every Automatic Briefing Run writes a complete Archive Package under `ARCHIVE_LOCAL_ROOT` before any remote sync is attempted. Sync to NAS or cloud storage happens after the local package is complete, and sync failure is recorded in Archive Metadata and operational run state without deleting or rewriting the local archive.

The exact sync mechanism is deferred to the archive/storage spike because it depends on the Briefing Host: a mounted NAS folder, `rsync`, `rclone`, Synology/TrueNAS-native sync, or another host-supported tool may be the best fit. The hard-to-reverse decision is that the local Archive Package is the source of truth for MVP recovery.

**Tradeoffs**

- Local-first archives protect the daily record from transient remote failures, but require enough host disk space and backup monitoring.
- Host-native sync can be simpler and more reliable than custom app code, but the Operations Console still needs visible sync status.
- Direct cloud-only storage may be cleaner later, but would weaken the MVP requirement for local backups.

**Consequences**

- Archive Writer must be able to complete without network storage being available.
- Storage Sync must record success, failure reason, target, and retry status.
- Archive/storage spike must prove local write, one configured sync path, and one recorded sync failure.
- MVP delivery must not block on sync success after the local Archive Package has been written.
