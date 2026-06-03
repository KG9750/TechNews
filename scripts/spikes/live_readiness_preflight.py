#!/usr/bin/env python3
"""Preflight the live external spike evidence flow.

This helper runs local dry-runs, checks required environment variable names,
and summarizes missing live evidence files. It writes only under evidence/.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_ROOT = ROOT / "evidence"

ENV_GROUPS = {
    "feishu": [
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
        "FEISHU_DEFAULT_USER_OPEN_ID",
        "FEISHU_DEFAULT_CHAT_ID",
    ],
    "model_provider": [
        "MODEL_PROVIDER",
        "MODEL_DEFAULT_MODEL",
        "MODEL_API_KEY",
    ],
    "archive_sync": [
        "ARCHIVE_LOCAL_ROOT",
        "ARCHIVE_SYNC_TARGET",
    ],
}

EVIDENCE_FILES = [
    "readiness-manifest.json",
    "feishu-delivery/user-response.redacted.json",
    "feishu-delivery/group-response.redacted.json",
    "feishu-delivery/rendered-message.md",
    "model-provider/outputs/high-confidence-news.json",
    "model-provider/outputs/low-confidence-news.json",
    "model-provider/outputs/academic-paper.json",
    "model-provider/usage-log.json",
    "archive-storage/sync-result.json",
    "archive-storage/local-tree.txt",
    "archive-storage/remote-tree.txt",
]

SENSITIVE_ENV_NAMES = sorted({name for names in ENV_GROUPS.values() for name in names})


def env_summary() -> dict[str, dict[str, list[str]]]:
    summary = {}
    for group, names in ENV_GROUPS.items():
        present = [name for name in names if os.environ.get(name)]
        missing = [name for name in names if not os.environ.get(name)]
        summary[group] = {
            "present": present,
            "missing": missing,
        }
    return summary


def evidence_summary(evidence_root: Path) -> dict[str, list[str]]:
    present = [path for path in EVIDENCE_FILES if (evidence_root / path).exists()]
    missing = [path for path in EVIDENCE_FILES if not (evidence_root / path).exists()]
    return {
        "present": present,
        "missing": missing,
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def dry_run_commands(evidence_root: Path) -> list[list[str]]:
    return [
        [
            "scripts/spikes/feishu_delivery_spike.py",
            "--dry-run",
            "--evidence-dir",
            str(evidence_root / "feishu-delivery"),
        ],
        [
            "scripts/spikes/model_provider_spike.py",
            "--dry-run",
            "--evidence-dir",
            str(evidence_root / "model-provider"),
        ],
        [
            "scripts/spikes/archive_storage_spike.py",
            "--dry-run",
            "--evidence-dir",
            str(evidence_root / "archive-storage"),
        ],
        [
            "scripts/spikes/readiness_manifest.py",
            "--dry-run",
            "--evidence-root",
            str(evidence_root),
            "--output",
            str(evidence_root / "readiness-manifest.dry-run.json"),
        ],
    ]


def redact_text(text: str) -> str:
    replacements = {
        str(ROOT): "REDACTED_WORKSPACE",
        str(Path.home()): "REDACTED_HOME",
    }
    for name in SENSITIVE_ENV_NAMES:
        value = os.environ.get(name)
        if value:
            replacements[value] = "REDACTED_ENV_VALUE"
    redacted = text
    for needle, replacement in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        if needle:
            redacted = redacted.replace(needle, replacement)
    return redacted


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return redact_text(str(path))


def run_dry_runs(evidence_root: Path, run_helpers: bool) -> list[dict]:
    results = []
    if not run_helpers:
        return results
    for command in dry_run_commands(evidence_root):
        args = [sys.executable, *command]
        result = subprocess.run(
            args,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        results.append(
            {
                "command": redact_text(" ".join([sys.executable, *command])),
                "returncode": result.returncode,
                "stdout": redact_text(result.stdout.strip()),
                "stderr": redact_text(result.stderr.strip()),
            }
        )
    return results


def build_summary(evidence_root: Path, run_helpers: bool) -> dict:
    dry_run_results = run_dry_runs(evidence_root, run_helpers)
    return {
        "generated_at": utc_now(),
        "mode": "dry_run_helpers" if run_helpers else "inspect_only",
        "dry_run_commands": dry_run_results,
        "environment": env_summary(),
        "evidence": evidence_summary(evidence_root),
        "final_gate_command": "python3 scripts/check_readiness.py --require-live --require-evidence",
        "next_commands": [
            "python3 scripts/spikes/feishu_delivery_spike.py",
            "python3 scripts/spikes/model_provider_spike.py --validate-evidence",
            "python3 scripts/spikes/archive_storage_spike.py",
            "python3 scripts/spikes/readiness_manifest.py",
            "python3 scripts/check_readiness.py --require-live --require-evidence",
        ],
        "notes": [
            "Environment values are not written, only variable names.",
            "Dry-run outputs are generated under ignored evidence/.",
            "Strict mode fails until all required environment variables and live evidence files are present.",
        ],
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def has_missing_required(summary: dict) -> bool:
    env_missing = any(group["missing"] for group in summary["environment"].values())
    evidence_missing = bool(summary["evidence"]["missing"])
    command_failed = any(result["returncode"] != 0 for result in summary["dry_run_commands"])
    return env_missing or evidence_missing or command_failed


def print_summary(path: Path, summary: dict) -> None:
    missing_env_count = sum(len(group["missing"]) for group in summary["environment"].values())
    missing_evidence_count = len(summary["evidence"]["missing"])
    failed_commands = [result for result in summary["dry_run_commands"] if result["returncode"] != 0]
    print(f"Preflight summary written to {display_path(path)}")
    print(f"Missing environment variables: {missing_env_count}")
    print(f"Missing live evidence files: {missing_evidence_count}")
    if summary["dry_run_commands"]:
        print(f"Helper dry-runs: {len(summary['dry_run_commands']) - len(failed_commands)} passed, {len(failed_commands)} failed")
    else:
        print("Helper dry-runs: skipped")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run local dry-run helpers and write a preflight summary.")
    parser.add_argument("--skip-helper-dry-runs", action="store_true", help="Only inspect environment and evidence files.")
    parser.add_argument("--strict", action="store_true", help="Fail if env vars, dry-runs, or live evidence files are missing.")
    parser.add_argument("--evidence-root", default=str(DEFAULT_EVIDENCE_ROOT))
    parser.add_argument("--summary-path", "--output", dest="summary_path", help="Override summary output path.")
    args = parser.parse_args()

    evidence_root = Path(args.evidence_root)
    output_path = Path(args.summary_path) if args.summary_path else evidence_root / "live-readiness-preflight.json"
    run_helpers = args.dry_run and not args.skip_helper_dry_runs
    summary = build_summary(evidence_root, run_helpers=run_helpers)
    write_json(output_path, summary)
    print_summary(output_path, summary)
    if args.strict and has_missing_required(summary):
        print("STRICT preflight failed: environment variables, failed helper dry-runs, or live evidence files are incomplete")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
