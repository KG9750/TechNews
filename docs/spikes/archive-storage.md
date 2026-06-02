# Archive And Storage Spike

Status: Local write and failure simulation complete; external sync target pending
Owner: Briefing Administrator

## Goal

Prove that an Archive Package can be written locally on the Briefing Host, synced to the configured NAS/cloud target, and kept locally when sync fails.

## Inputs

- Minimal contracts: `docs/schemas/minimal-contracts.md`
- Secrets inventory: `docs/secrets.md`
- Throwaway live runner: `scripts/spikes/archive_storage_spike.py`

## Archive Package Shape

```text
archives/
  2026-06-01/
    technology/
      briefing.html
      briefing.md
      metadata.json
      media/
```

Fixture evidence:

```text
fixtures/archive-storage/
  local-archive/
    2026-06-01/
      technology/
        briefing.html
        briefing.md
        metadata.json
        media/
          README.md
```

## Questions To Answer

- What is the first `ARCHIVE_LOCAL_ROOT` on the Briefing Host?
- What is the first `ARCHIVE_SYNC_TARGET`?
- Is sync implemented by a mounted folder, NAS-native sync, `rsync`, object storage, or another tool?
- What metadata records sync failure and retry status?
- How long should local archive packages be retained?

## Verification Checklist

- [x] A sample Archive Package is written locally.
- [x] `metadata.json` includes selected items, excluded candidates, delivery status, model usage summary, and sync status.
- [ ] The package can be copied or synced to the target.
- [x] A simulated sync failure keeps the local package and records failure status.

## Evidence To Attach

- Example local archive tree: `fixtures/archive-storage/local-archive/2026-06-01/technology/`.
- Failure status example: `sync_status.remote_sync.status = failed` in fixture `metadata.json`.
- Dry-run command: `python3 scripts/spikes/archive_storage_spike.py --dry-run`.
- Live command: `python3 scripts/spikes/archive_storage_spike.py`.
- Pending: redacted success evidence for a real `ARCHIVE_SYNC_TARGET`.

## Current Finding

The local-first strategy in ADR-0006 is viable for the archive package shape. The fixture proves that local artifacts remain readable and that sync failure can be recorded without deleting local output. The spike is not fully complete until the Briefing Administrator provides a real NAS/cloud target and a redacted success note.
