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
python -m ruff format --check technews_briefing scripts/dev_check.py scripts/validate_fixtures.py scripts/run_tests.py scripts/test_product_modules.py
python -m ruff check technews_briefing scripts/dev_check.py scripts/validate_fixtures.py scripts/run_tests.py scripts/test_product_modules.py
python scripts/validate_fixtures.py
python scripts/run_tests.py
```

Runtime secrets and live evidence stay local. Do not commit `.env`, `evidence/`, or `archives/`.

