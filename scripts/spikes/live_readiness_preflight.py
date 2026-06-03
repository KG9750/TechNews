#!/usr/bin/env python3
"""Preflight the live external spike evidence flow.

This helper runs local dry-runs, checks required environment variable names,
summarizes missing live evidence files, and reports live evidence validation
failures. It writes only under evidence/.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_ROOT = ROOT / "evidence"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


readiness = load_module("check_readiness", ROOT / "scripts/check_readiness.py")

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
FINAL_EVIDENCE_GROUPS = {
    "readiness_manifest": [
        "readiness-manifest.json",
    ],
    "feishu_delivery": [
        "feishu-delivery/user-response.redacted.json",
        "feishu-delivery/group-response.redacted.json",
        "feishu-delivery/rendered-message.md",
    ],
    "model_provider": [
        "model-provider/outputs/high-confidence-news.json",
        "model-provider/outputs/low-confidence-news.json",
        "model-provider/outputs/academic-paper.json",
        "model-provider/usage-log.json",
    ],
    "archive_storage": [
        "archive-storage/sync-result.json",
        "archive-storage/local-tree.txt",
        "archive-storage/remote-tree.txt",
    ],
}
DRY_RUN_ARTIFACT_FILES = [
    "readiness-manifest.dry-run.json",
    "feishu-delivery/dry-run-request-shape.redacted.json",
    "model-provider/dry-run-summary.json",
    "model-provider/prompt-contract.md",
    "model-provider/requests/high-confidence-news.request.json",
    "model-provider/requests/low-confidence-news.request.json",
    "model-provider/requests/academic-paper.request.json",
    "archive-storage/dry-run-sync-result.json",
    "final-redaction-review.md",
]

SENSITIVE_ENV_NAMES = sorted({name for names in ENV_GROUPS.values() for name in names})
SPIKE_PACKET_SPECS = [
    {
        "key": "feishu-delivery",
        "title": "Feishu Delivery",
        "issue_url": "https://github.com/KG9750/TechNews/issues/3",
        "env_group": "feishu",
        "evidence_group": "feishu_delivery",
        "evidence_prefixes": ["feishu-delivery/"],
        "validation_needles": ["feishu", "feishu-delivery"],
        "commands": [
            "python3 scripts/spikes/feishu_delivery_spike.py --dry-run",
            "python3 scripts/spikes/feishu_delivery_spike.py",
            "python3 scripts/spikes/feishu_delivery_spike.py --validate-evidence",
            "python3 scripts/spikes/feishu_delivery_spike.py --attempt-group-webhook-fallback",
            "python3 scripts/spikes/live_readiness_preflight.py --strict --write-packet --write-spike-packets",
        ],
    },
    {
        "key": "model-provider",
        "title": "Model Provider",
        "issue_url": "https://github.com/KG9750/TechNews/issues/5",
        "env_group": "model_provider",
        "evidence_group": "model_provider",
        "evidence_prefixes": ["model-provider/"],
        "validation_needles": ["model", "model-provider"],
        "commands": [
            "python3 scripts/spikes/model_provider_spike.py --dry-run",
            "python3 scripts/spikes/model_provider_spike.py --validate-requests",
            "python3 scripts/spikes/model_provider_spike.py --validate-evidence",
            "python3 scripts/spikes/live_readiness_preflight.py --strict --write-packet --write-spike-packets",
        ],
    },
    {
        "key": "archive-storage",
        "title": "Archive Storage",
        "issue_url": "https://github.com/KG9750/TechNews/issues/6",
        "env_group": "archive_sync",
        "evidence_group": "archive_storage",
        "evidence_prefixes": ["archive-storage/"],
        "validation_needles": ["archive", "archive-storage"],
        "commands": [
            "python3 scripts/spikes/archive_storage_spike.py --dry-run",
            "python3 scripts/spikes/archive_storage_spike.py",
            "python3 scripts/spikes/archive_storage_spike.py --validate-evidence",
            "python3 scripts/spikes/live_readiness_preflight.py --strict --write-packet --write-spike-packets",
        ],
    },
]


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


def final_evidence_group_summary(evidence_root: Path) -> dict[str, dict[str, str | list[str]]]:
    summary = {}
    for group, files in FINAL_EVIDENCE_GROUPS.items():
        present = [path for path in files if (evidence_root / path).exists()]
        missing = [path for path in files if not (evidence_root / path).exists()]
        if not present:
            status = "missing"
        elif missing:
            status = "partial"
        else:
            status = "complete"
        summary[group] = {
            "status": status,
            "present": present,
            "missing": missing,
        }
    return summary


def dry_run_artifact_summary(evidence_root: Path) -> dict[str, list[str]]:
    present = [path for path in DRY_RUN_ARTIFACT_FILES if (evidence_root / path).exists()]
    missing = [path for path in DRY_RUN_ARTIFACT_FILES if not (evidence_root / path).exists()]
    return {
        "present": present,
        "missing": missing,
    }


def evidence_validation_summary(evidence_root: Path, require_clean_worktree: bool = False) -> dict[str, list[str]]:
    passed, missing, failures = readiness.check_live_evidence(
        evidence_root,
        require_clean_worktree=require_clean_worktree,
    )
    return {
        "passed": [redact_text(item) for item in passed],
        "missing": [redact_text(item) for item in missing],
        "failures": [redact_text(item) for item in failures],
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
            "scripts/spikes/model_provider_spike.py",
            "--validate-requests",
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
            "--write-final-review-packet",
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
    comparable_path = path if path.is_absolute() else ROOT / path
    try:
        return str(comparable_path.resolve().relative_to(ROOT))
    except ValueError:
        return "REDACTED_EXTERNAL_PATH"


def markdown_bullets(items: list[str], empty_label: str = "None.") -> str:
    if not items:
        return f"- {empty_label}"
    return "\n".join(f"- {item}" for item in items)


def markdown_command_block(commands: list[str]) -> str:
    return "```bash\n" + "\n".join(commands) + "\n```"


def matches_any_prefix(value: str, prefixes: list[str]) -> bool:
    return any(value.startswith(prefix) for prefix in prefixes)


def matches_any_needle(value: str, needles: list[str]) -> bool:
    lowered = value.lower()
    return any(needle in lowered for needle in needles)


def build_markdown_packet(summary: dict, evidence_root: Path, summary_path: Path, packet_path: Path) -> str:
    env_sections = []
    for group, env in summary["environment"].items():
        env_sections.extend(
            [
                f"### {group}",
                "",
                "Present variable names:",
                markdown_bullets(env["present"], empty_label="None present."),
                "",
                "Missing variable names:",
                markdown_bullets(env["missing"], empty_label="None missing."),
                "",
            ]
        )

    dry_run_sections = []
    if summary["dry_run_commands"]:
        for result in summary["dry_run_commands"]:
            status = "passed" if result["returncode"] == 0 else "failed"
            dry_run_sections.append(f"- `{result['command']}` -> {status} ({result['returncode']})")
    else:
        dry_run_sections.append("- Helper dry-runs were skipped.")

    final_evidence_group_sections = []
    for group, group_summary in summary["final_evidence_groups"].items():
        final_evidence_group_sections.extend(
            [
                f"### {group}",
                "",
                f"- Status: `{group_summary['status']}`",
                "",
                "Present final evidence:",
                markdown_bullets(group_summary["present"], empty_label="None present."),
                "",
                "Missing final evidence:",
                markdown_bullets(group_summary["missing"], empty_label="None missing."),
                "",
            ]
        )

    return "\n".join(
        [
            "# Live Readiness Execution Packet",
            "",
            "This packet is context only. Complete live evidence files under ignored `evidence/`; do not treat this packet as readiness evidence.",
            "",
            f"- Generated at: {summary['generated_at']}",
            f"- Evidence root: `{display_path(evidence_root)}`",
            f"- JSON summary: `{display_path(summary_path)}`",
            f"- Packet path: `{display_path(packet_path)}`",
            f"- Final gate: `{summary['final_gate_command']}`",
            "",
            "## Current Environment Status",
            "",
            *env_sections,
            "## Evidence File Checklist",
            "",
            "Present evidence files:",
            markdown_bullets(summary["evidence"]["present"], empty_label="None present."),
            "",
            "Missing evidence files:",
            markdown_bullets(summary["evidence"]["missing"], empty_label="None missing."),
            "",
            "## Final Evidence Group Status",
            "",
            "A `partial` group means some final evidence files exist, but the spike is still incomplete and must not be closed.",
            "",
            *final_evidence_group_sections,
            "## Dry-Run Artifact Inventory",
            "",
            "These files are generated helper outputs. They do not count as final live evidence.",
            "",
            "Present dry-run artifacts:",
            markdown_bullets(summary["dry_run_artifacts"]["present"], empty_label="None present."),
            "",
            "Missing dry-run artifacts:",
            markdown_bullets(summary["dry_run_artifacts"]["missing"], empty_label="None missing."),
            "",
            "## Evidence Validation Status",
            "",
            "Passed checks:",
            markdown_bullets(summary["evidence_validation"]["passed"], empty_label="None passed yet."),
            "",
            "Missing validation inputs:",
            markdown_bullets(summary["evidence_validation"]["missing"], empty_label="None missing."),
            "",
            "Validation failures:",
            markdown_bullets(summary["evidence_validation"]["failures"], empty_label="None."),
            "",
            "## Helper Dry-Run Results",
            "",
            "\n".join(dry_run_sections),
            "",
            "## Execution Order",
            "",
            markdown_command_block(
                [
                    "python3 scripts/spikes/live_readiness_preflight.py --dry-run --write-packet --write-spike-packets",
                    "python3 scripts/spikes/feishu_delivery_spike.py",
                    "python3 scripts/spikes/feishu_delivery_spike.py --validate-evidence",
                    "python3 scripts/spikes/model_provider_spike.py --validate-requests",
                    "python3 scripts/spikes/model_provider_spike.py --validate-evidence",
                    "python3 scripts/spikes/archive_storage_spike.py",
                    "python3 scripts/spikes/archive_storage_spike.py --validate-evidence",
                    "python3 scripts/spikes/readiness_manifest.py --write-final-review-packet",
                    "python3 scripts/spikes/live_readiness_preflight.py --strict --write-packet --write-spike-packets",
                    "python3 scripts/check_readiness.py --require-live --require-evidence",
                ]
            ),
            "",
            "## Redaction Guardrails",
            "",
            markdown_bullets(summary["notes"]),
            "- Review every generated evidence file before sharing.",
            "- Keep recipient ids, tokens, API keys, local paths, and NAS/cloud targets redacted.",
            "- Preserve validation fields such as status codes, run ids, provider/model names, request counts, latency, and source anchors.",
        ]
    )


def spike_packet_status(summary: dict, spec: dict) -> str:
    env_missing = summary["environment"][spec["env_group"]]["missing"]
    evidence_missing = [
        path
        for path in summary["evidence"]["missing"]
        if matches_any_prefix(path, spec["evidence_prefixes"])
    ]
    validation_missing = [
        item
        for item in summary["evidence_validation"]["missing"]
        if matches_any_needle(item, spec["validation_needles"])
    ]
    validation_failures = [
        item
        for item in summary["evidence_validation"]["failures"]
        if matches_any_needle(item, spec["validation_needles"])
    ]
    if env_missing or evidence_missing or validation_missing or validation_failures:
        return "blocked"
    return "ready for final gate"


def build_spike_packet(summary: dict, evidence_root: Path, spec: dict) -> str:
    env = summary["environment"][spec["env_group"]]
    evidence_group = summary["final_evidence_groups"][spec["evidence_group"]]
    evidence_present = [
        path
        for path in summary["evidence"]["present"]
        if matches_any_prefix(path, spec["evidence_prefixes"])
    ]
    evidence_missing = [
        path
        for path in summary["evidence"]["missing"]
        if matches_any_prefix(path, spec["evidence_prefixes"])
    ]
    validation_passed = [
        item
        for item in summary["evidence_validation"]["passed"]
        if matches_any_needle(item, spec["validation_needles"])
    ]
    validation_missing = [
        item
        for item in summary["evidence_validation"]["missing"]
        if matches_any_needle(item, spec["validation_needles"])
    ]
    validation_failures = [
        item
        for item in summary["evidence_validation"]["failures"]
        if matches_any_needle(item, spec["validation_needles"])
    ]

    return "\n".join(
        [
            f"# Live Spike Packet: {spec['title']}",
            "",
            "This packet is context only. Complete redacted live evidence under ignored `evidence/`; do not commit this packet or live evidence.",
            "",
            f"- Status: {spike_packet_status(summary, spec)}",
            f"- GitHub issue: {spec['issue_url']}",
            f"- Evidence root: `{display_path(evidence_root)}`",
            f"- Final gate: `{summary['final_gate_command']}`",
            "",
            "## Environment Names",
            "",
            "Present variable names:",
            markdown_bullets(env["present"], empty_label="None present."),
            "",
            "Missing variable names:",
            markdown_bullets(env["missing"], empty_label="None missing."),
            "",
            "## Evidence Files",
            "",
            "Present files:",
            markdown_bullets(evidence_present, empty_label="None present."),
            "",
            "Missing files:",
            markdown_bullets(evidence_missing, empty_label="None missing."),
            "",
            "## Final Evidence Group Status",
            "",
            f"- Status: `{evidence_group['status']}`",
            "",
            "Present final evidence:",
            markdown_bullets(evidence_group["present"], empty_label="None present."),
            "",
            "Missing final evidence:",
            markdown_bullets(evidence_group["missing"], empty_label="None missing."),
            "",
            "## Validation Status",
            "",
            "Passed checks:",
            markdown_bullets(validation_passed, empty_label="None passed yet."),
            "",
            "Missing validation inputs:",
            markdown_bullets(validation_missing, empty_label="None missing."),
            "",
            "Validation failures:",
            markdown_bullets(validation_failures, empty_label="None."),
            "",
            "## Commands",
            "",
            markdown_command_block(spec["commands"]),
            "",
            "## Guardrails",
            "",
            "- Do not paste raw secrets, recipient ids, API keys, local paths, or sync targets into GitHub comments.",
            "- Keep validation fields such as status, run id, provider/model, latency, and source anchors visible.",
            "- Attach only redacted summaries or paths to ignored local evidence when updating the linked issue.",
        ]
    )


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


def build_summary(evidence_root: Path, run_helpers: bool, require_clean_worktree: bool = False) -> dict:
    dry_run_results = run_dry_runs(evidence_root, run_helpers)
    return {
        "generated_at": utc_now(),
        "mode": "dry_run_helpers" if run_helpers else "inspect_only",
        "dry_run_commands": dry_run_results,
        "environment": env_summary(),
        "evidence": evidence_summary(evidence_root),
        "final_evidence_groups": final_evidence_group_summary(evidence_root),
        "dry_run_artifacts": dry_run_artifact_summary(evidence_root),
        "evidence_validation": evidence_validation_summary(
            evidence_root,
            require_clean_worktree=require_clean_worktree,
        ),
        "final_gate_command": "python3 scripts/check_readiness.py --require-live --require-evidence",
        "next_commands": [
            "python3 scripts/spikes/feishu_delivery_spike.py",
            "python3 scripts/spikes/feishu_delivery_spike.py --validate-evidence",
            "python3 scripts/spikes/model_provider_spike.py --validate-requests",
            "python3 scripts/spikes/model_provider_spike.py --validate-evidence",
            "python3 scripts/spikes/archive_storage_spike.py",
            "python3 scripts/spikes/archive_storage_spike.py --validate-evidence",
            "python3 scripts/spikes/readiness_manifest.py --write-final-review-packet",
            "python3 scripts/check_readiness.py --require-live --require-evidence",
        ],
        "notes": [
            "Environment values are not written, only variable names.",
            "Dry-run outputs are generated under ignored evidence/.",
            "Strict mode fails until all required environment variables and valid live evidence files are present.",
            "Strict mode requires a clean tracked worktree; ignored evidence files do not need to be committed.",
        ],
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")


def write_spike_packets(packet_dir: Path, summary: dict, evidence_root: Path) -> list[Path]:
    written = []
    for spec in SPIKE_PACKET_SPECS:
        path = packet_dir / f"{spec['key']}.md"
        write_markdown(path, build_spike_packet(summary, evidence_root, spec))
        written.append(path)
    return written


def has_missing_required(summary: dict) -> bool:
    env_missing = any(group["missing"] for group in summary["environment"].values())
    evidence_missing = bool(summary["evidence"]["missing"])
    validation_missing = bool(summary["evidence_validation"]["missing"])
    validation_failed = bool(summary["evidence_validation"]["failures"])
    command_failed = any(result["returncode"] != 0 for result in summary["dry_run_commands"])
    return env_missing or evidence_missing or validation_missing or validation_failed or command_failed


def print_summary(path: Path, summary: dict) -> None:
    missing_env_count = sum(len(group["missing"]) for group in summary["environment"].values())
    missing_evidence_count = len(summary["evidence"]["missing"])
    validation_failure_count = len(summary["evidence_validation"]["failures"])
    partial_groups = [
        name
        for name, group in summary["final_evidence_groups"].items()
        if group["status"] == "partial"
    ]
    failed_commands = [result for result in summary["dry_run_commands"] if result["returncode"] != 0]
    print(f"Preflight summary written to {display_path(path)}")
    print(f"Missing environment variables: {missing_env_count}")
    print(f"Missing live evidence files: {missing_evidence_count}")
    print(f"Partial final evidence groups: {len(partial_groups)}")
    print(f"Live evidence validation failures: {validation_failure_count}")
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
    parser.add_argument("--write-packet", action="store_true", help="Also write a Markdown execution packet under evidence/.")
    parser.add_argument("--packet-path", help="Override Markdown packet output path.")
    parser.add_argument("--write-spike-packets", action="store_true", help="Also write one Markdown packet per live spike under evidence/.")
    parser.add_argument("--spike-packet-dir", help="Override per-spike Markdown packet directory.")
    args = parser.parse_args()

    evidence_root = Path(args.evidence_root)
    output_path = Path(args.summary_path) if args.summary_path else evidence_root / "live-readiness-preflight.json"
    packet_path = Path(args.packet_path) if args.packet_path else evidence_root / "live-readiness-packet.md"
    spike_packet_dir = Path(args.spike_packet_dir) if args.spike_packet_dir else evidence_root / "live-spike-packets"
    run_helpers = args.dry_run and not args.skip_helper_dry_runs
    summary = build_summary(evidence_root, run_helpers=run_helpers, require_clean_worktree=args.strict)
    write_json(output_path, summary)
    if args.write_packet:
        write_markdown(packet_path, build_markdown_packet(summary, evidence_root, output_path, packet_path))
        print(f"Preflight packet written to {display_path(packet_path)}")
    if args.write_spike_packets:
        for path in write_spike_packets(spike_packet_dir, summary, evidence_root):
            print(f"Live spike packet written to {display_path(path)}")
    print_summary(output_path, summary)
    if args.strict and has_missing_required(summary):
        print("STRICT preflight failed: environment variables, failed helper dry-runs, or live evidence validation are incomplete")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
