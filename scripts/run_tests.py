#!/usr/bin/env python3
"""Run the local test suite through one stable entrypoint."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

COMMANDS = [
    ["scripts/check_readiness.py"],
    ["scripts/test_live_evidence_helpers.py"],
    ["scripts/test_readiness_action_packet.py"],
    ["scripts/test_source_owner_review_decision.py"],
    ["scripts/test_product_modules.py"],
    ["scripts/test_deployment.py"],
    ["scripts/generate_architecture_review_ui.py"],
]


def main() -> int:
    for command in COMMANDS:
        print(f"$ python {' '.join(command)}")
        completed = subprocess.run([sys.executable, *command], cwd=ROOT)
        if completed.returncode:
            return completed.returncode
    print("all local tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
