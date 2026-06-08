#!/usr/bin/env python3
"""Run the local MVP foundation checks used by CI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLING_PATHS = [
    "technews_briefing",
    "scripts/dev_check.py",
    "scripts/validate_fixtures.py",
    "scripts/run_tests.py",
    "scripts/test_product_modules.py",
    "scripts/test_deployment.py",
    "scripts/run_e2e_acceptance.py",
    "scripts/test_e2e_acceptance.py",
    "scripts/run_daily_briefing.py",
    "scripts/test_daily_run.py",
]
COMMANDS = [
    ("format", [sys.executable, "-m", "ruff", "format", "--check", *TOOLING_PATHS]),
    ("lint", [sys.executable, "-m", "ruff", "check", *TOOLING_PATHS]),
    ("compile", [sys.executable, "-m", "compileall", "-q", "technews_briefing", "scripts"]),
    ("fixtures", [sys.executable, "scripts/validate_fixtures.py"]),
    ("tests", [sys.executable, "scripts/run_tests.py"]),
]


def main() -> int:
    for label, command in COMMANDS:
        print(f"$ {' '.join(command)}")
        completed = subprocess.run(command, cwd=ROOT, check=False)
        if completed.returncode:
            print(f"{label} check failed")
            return completed.returncode
    print("all MVP foundation checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
