#!/usr/bin/env python3
"""Generate a top-level pre-development readiness action packet.

This helper writes an ignored Markdown file that points reviewers to the live
evidence packet and source owner review index. It does not collect credentials
or replace the authoritative readiness gate.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = ROOT / "evidence"
DEFAULT_OUTPUT = DEFAULT_EVIDENCE_ROOT / "readiness-action-packet.md"
SOURCE_OWNER_INDEX_RELATIVE = "source-owner-reviews/index.md"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


live_preflight = load_module("live_readiness_preflight", ROOT / "scripts/spikes/live_readiness_preflight.py")
source_owner = load_module("source_owner_review_decision", ROOT / "scripts/source_owner_review_decision.py")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def markdown_cell(value: object) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|")


def source_decision_state(evidence_dir: Path, source_id: str) -> dict[str, str]:
    path = source_owner.decision_path(evidence_dir, source_id)
    if not path.exists():
        return {"status": "missing", "decision": ""}
    decision = ""
    try:
        payload = source_owner.read_json(path)
        decision = str(payload.get("decision", ""))
        source_owner.validated_payload(path)
    except (source_owner.ReviewError, json.JSONDecodeError) as error:
        return {"status": "invalid", "decision": decision, "detail": str(error)}
    return {"status": "valid", "decision": decision, "detail": "ready to apply"}


def source_owner_summary(evidence_root: Path) -> dict:
    evidence_dir = evidence_root / "source-owner-reviews"
    items = source_owner.load_queue_items()
    counts = {"valid": 0, "invalid": 0, "missing": 0}
    by_decision_needed: dict[str, int] = {}
    for source_id in source_owner.open_source_ids():
        item = items[source_id]
        state = source_decision_state(evidence_dir, source_id)
        counts[state["status"]] += 1
        decision_needed = item["decision_needed"]
        by_decision_needed[decision_needed] = by_decision_needed.get(decision_needed, 0) + 1

    return {
        "open": sum(counts.values()),
        "counts": counts,
        "by_decision_needed": by_decision_needed,
        "index_path": display_path(evidence_root / SOURCE_OWNER_INDEX_RELATIVE),
    }


def live_workstream_rows(live_summary: dict) -> list[dict[str, object]]:
    evidence_missing = live_summary["evidence"]["missing"]
    groups = [
        ("Feishu delivery", "feishu", "feishu-delivery/"),
        ("Model provider", "model_provider", "model-provider/"),
        ("Archive sync", "archive_sync", "archive-storage/"),
    ]
    rows = []
    for label, env_group, evidence_prefix in groups:
        env_missing = live_summary["environment"][env_group]["missing"]
        files_missing = [path for path in evidence_missing if path.startswith(evidence_prefix)]
        if env_group == "archive_sync":
            files_missing = [path for path in evidence_missing if path.startswith("archive-storage/")]
        rows.append(
            {
                "workstream": label,
                "status": "blocked" if env_missing or files_missing else "ready for final gate",
                "missing_env": len(env_missing),
                "missing_evidence": len(files_missing),
            }
        )
    return rows


def build_packet(evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> str:
    live_summary = live_preflight.build_summary(evidence_root, run_helpers=False)
    source_summary = source_owner_summary(evidence_root)
    live_env_missing = sum(len(group["missing"]) for group in live_summary["environment"].values())
    live_evidence_missing = len(live_summary["evidence"]["missing"])
    workstream_rows = live_workstream_rows(live_summary)

    source_decision_rows = [
        f"{decision_needed}: {count}"
        for decision_needed, count in sorted(source_summary["by_decision_needed"].items())
    ]
    env_sections = []
    for group, env in live_summary["environment"].items():
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

    table_rows = [
        "| Workstream | Status | Missing env vars | Missing evidence files |",
        "| --- | --- | --- | --- |",
    ]
    for row in workstream_rows:
        table_rows.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(row["workstream"]),
                    markdown_cell(row["status"]),
                    markdown_cell(row["missing_env"]),
                    markdown_cell(row["missing_evidence"]),
                ]
            )
            + " |"
        )
    table_rows.append(
        "| "
        + " | ".join(
            [
                "Source owner decisions",
                "blocked" if source_summary["counts"]["invalid"] or source_summary["counts"]["missing"] else "ready to apply",
                "0",
                f"{source_summary['counts']['invalid']} invalid, {source_summary['counts']['missing']} missing",
            ]
        )
        + " |"
    )

    return "\n".join(
        [
            "# Pre-development Readiness Action Packet",
            "",
            "This packet is context only. It summarizes the remaining external evidence and owner-review actions; it is not readiness evidence and does not replace `scripts/check_readiness.py`.",
            "",
            f"- Generated at: {utc_now()}",
            f"- Evidence root: `{display_path(evidence_root)}`",
            "- Final gate: `python3 scripts/check_readiness.py --require-live --require-evidence`",
            "- GitHub tracker gate: `python3 scripts/check_readiness.py --require-github`",
            "",
            "## Current Snapshot",
            "",
            f"- Missing live environment variables: {live_env_missing}",
            f"- Missing live evidence files: {live_evidence_missing}",
            f"- Open source owner decisions: {source_summary['open']}",
            f"- Valid source owner decisions: {source_summary['counts']['valid']}",
            f"- Invalid source owner decisions: {source_summary['counts']['invalid']}",
            f"- Missing source owner decisions: {source_summary['counts']['missing']}",
            "",
            "## Linked Packets",
            "",
            f"- Live execution packet: `{display_path(evidence_root / 'live-readiness-packet.md')}`",
            f"- Live preflight summary: `{display_path(evidence_root / 'live-readiness-preflight.json')}`",
            f"- Source owner review index: `{source_summary['index_path']}`",
            "",
            "## Live Environment Names",
            "",
            *env_sections,
            "## Blocking Workstreams",
            "",
            *table_rows,
            "",
            "## Source Owner Decision Types",
            "",
            markdown_bullets(source_decision_rows, empty_label="No open source owner decisions."),
            "",
            "## Execution Order",
            "",
            "```bash",
            "python3 scripts/spikes/live_readiness_preflight.py --dry-run --write-packet",
            "python3 scripts/source_owner_review_decision.py --draft-all",
            "python3 scripts/source_owner_review_decision.py --packet-all",
            "python3 scripts/source_owner_review_decision.py --packet-index",
            "python3 scripts/readiness_action_packet.py",
            "python3 scripts/spikes/feishu_delivery_spike.py",
            "python3 scripts/spikes/model_provider_spike.py --validate-evidence",
            "python3 scripts/spikes/archive_storage_spike.py",
            "python3 scripts/spikes/readiness_manifest.py",
            "python3 scripts/spikes/live_readiness_preflight.py --strict --write-packet",
            "python3 scripts/check_readiness.py --require-live --require-evidence",
            "python3 scripts/check_readiness.py --require-github",
            "```",
            "",
            "## Guardrails",
            "",
            "- Do not commit anything under `evidence/`.",
            "- Do not paste real secrets, Feishu recipient ids, local paths, or NAS/cloud targets into tracked files.",
            "- Keep MVP issues `needs-triage` until the final readiness and GitHub tracker gates pass.",
            "- Complete JSON source owner decisions before applying source policy changes.",
        ]
    )


def write_packet(output_path: Path, evidence_root: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_packet(evidence_root) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", default=str(DEFAULT_EVIDENCE_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    evidence_root = Path(args.evidence_root)
    output_path = Path(args.output)
    write_packet(output_path, evidence_root)
    print(f"Readiness action packet written to {display_path(output_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
