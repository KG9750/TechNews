# Archive And Storage Spike

Status: Not started
Owner: Briefing Administrator

## Goal

Prove that an Archive Package can be written locally on the Briefing Host, synced to the configured NAS/cloud target, and kept locally when sync fails.

## Inputs

- Minimal contracts: `docs/schemas/minimal-contracts.md`
- Secrets inventory: `docs/secrets.md`

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

## Questions To Answer

- What is the first `ARCHIVE_LOCAL_ROOT` on the Briefing Host?
- What is the first `ARCHIVE_SYNC_TARGET`?
- Is sync implemented by a mounted folder, NAS-native sync, `rsync`, object storage, or another tool?
- What metadata records sync failure and retry status?
- How long should local archive packages be retained?

## Verification Checklist

- A sample Archive Package is written locally.
- `metadata.json` includes selected items, excluded candidates, delivery status, model usage summary, and sync status.
- The package can be copied or synced to the target.
- A simulated sync failure keeps the local package and records failure status.

## Evidence To Attach

- Example local archive tree.
- Redacted sync command or NAS configuration note.
- Success and failure status examples.
