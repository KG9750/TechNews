# TechNews Briefing

Python service foundation for the TechNews Briefing MVP.

## Development

Use Python 3.12:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the same baseline checks used by MVP CI:

```bash
python scripts/dev_check.py
```

Useful focused commands:

```bash
python -m ruff format --check technews_briefing scripts/dev_check.py scripts/validate_fixtures.py scripts/run_tests.py scripts/test_product_modules.py scripts/test_deployment.py scripts/run_e2e_acceptance.py scripts/test_e2e_acceptance.py scripts/run_daily_briefing.py scripts/test_daily_run.py
python -m ruff check technews_briefing scripts/dev_check.py scripts/validate_fixtures.py scripts/run_tests.py scripts/test_product_modules.py scripts/test_deployment.py scripts/run_e2e_acceptance.py scripts/test_e2e_acceptance.py scripts/run_daily_briefing.py scripts/test_daily_run.py
python scripts/validate_fixtures.py
python scripts/run_tests.py
python scripts/run_e2e_acceptance.py
python scripts/run_daily_briefing.py
```

Runtime secrets and live evidence stay local. Do not commit `.env`, `evidence/`, or `archives/`.

## Deployment

The MVP deployment path is Docker Compose on a Briefing Host. See `docs/deployment.md` for host setup, volume mounts, `.env` handling, and the redacted health check.

The final fixture-backed MVP acceptance path is documented in `docs/e2e-acceptance.md`. The live daily runner uses metadata-only source fetching and is available through `scripts/run_daily_briefing.py`; use `--no-deliver` to test live fetch, ranking, archive writing, and sync without sending to Feishu.
