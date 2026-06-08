# MVP E2E Acceptance

The final MVP acceptance path is a fixture-backed end-to-end run that exercises the production modules without calling live Feishu or model-provider APIs. Live Feishu, model, and archive sync evidence remains in ignored `evidence/` and is verified by the readiness gates.

Run the deterministic acceptance flow:

```bash
python scripts/run_e2e_acceptance.py
```

The script prints a redacted JSON report. It verifies:

- one configured source from each First-Version Source type
- completed public-feed and academic-source collection
- deferred manual URL handling under the MVP source-access policy
- late connector timeout without blocking delivery
- ranking, Confidence Notice, Source Media attribution, no-media fallback, and Related History
- Push Briefing request construction for one Feishu user and one Feishu group
- Archive Package creation and sync status for the same run
- Operations Console run, delivery, and sync status visibility

To write a local redacted report:

```bash
python scripts/run_e2e_acceptance.py --write-report evidence/e2e-acceptance-report.json
```

On a Briefing Host, pass explicit archive paths when you want the fixture run to write to the host archive surfaces:

```bash
python scripts/run_e2e_acceptance.py \
  --archive-root "$ARCHIVE_LOCAL_ROOT" \
  --sync-target "$ARCHIVE_SYNC_TARGET" \
  --write-report evidence/e2e-acceptance-report.json
```

Do not paste the generated report into GitHub if it has been produced on a host with private paths. Use only copy-safe summaries and keep raw evidence local.
