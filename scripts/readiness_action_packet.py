#!/usr/bin/env python3
"""Generate a top-level pre-development readiness action packet.

This helper writes ignored Markdown packets that point reviewers to the live
evidence packet, source owner review packets, and MVP issue triage state. It
does not collect credentials or replace the authoritative readiness gate.
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
EXTERNAL_INPUT_REQUEST_RELATIVE = "external-input-request.md"
SOURCE_OWNER_INDEX_RELATIVE = "source-owner-reviews/index.md"
SOURCE_OWNER_WORKSHEET_RELATIVE = "source-owner-reviews/worksheet.md"
SOURCE_OWNER_BATCH_PLAN_RELATIVE = "source-owner-reviews/batch-plan.md"
SOURCE_OWNER_REQUEST_PACKET_RELATIVE = "source-owner-reviews/request-packet.md"
MVP_ISSUE_PACKET_DIR_RELATIVE = "mvp-issue-packets"
GITHUB_ISSUES = [
    ("Pre-development tracking", "https://github.com/KG9750/TechNews/issues/1"),
    ("Feishu delivery spike", "https://github.com/KG9750/TechNews/issues/3"),
    ("Model provider spike", "https://github.com/KG9750/TechNews/issues/5"),
    ("Archive/storage spike", "https://github.com/KG9750/TechNews/issues/6"),
]
EXTERNAL_INPUT_REQUESTS = [
    {
        "workstream": "Feishu delivery",
        "env_group": "feishu",
        "issue": "https://github.com/KG9750/TechNews/issues/3",
        "configure_at": "Briefing Host secret store or local `.env`; never GitHub.",
        "safe_request": "Request app id/secret, approved user open_id, and approved group chat_id through a secure channel.",
        "after_configured": "Run Feishu delivery spike and keep only redacted user/group responses plus rendered message evidence.",
    },
    {
        "workstream": "Model provider",
        "env_group": "model_provider",
        "issue": "https://github.com/KG9750/TechNews/issues/5",
        "configure_at": "Briefing Host secret store or local `.env`; never GitHub.",
        "safe_request": "Request provider name, default model name, and API key through a secure channel.",
        "after_configured": "Run model provider spike and keep redacted outputs plus usage metadata.",
    },
    {
        "workstream": "Archive sync",
        "env_group": "archive_sync",
        "issue": "https://github.com/KG9750/TechNews/issues/6",
        "configure_at": "Briefing Host secret store or local `.env`; never GitHub.",
        "safe_request": "Request local archive root and NAS/cloud sync target through a secure channel.",
        "after_configured": "Run archive storage spike and keep redacted sync result plus local/remote tree evidence.",
    },
]
LIVE_WORKSTREAMS = [
    {
        "key": "feishu_delivery",
        "label": "Feishu delivery",
        "env_group": "feishu",
        "evidence_group": "feishu_delivery",
        "evidence_prefixes": ["feishu-delivery/"],
        "validation_needles": ["feishu", "feishu-delivery"],
    },
    {
        "key": "model_provider",
        "label": "Model provider",
        "env_group": "model_provider",
        "evidence_group": "model_provider",
        "evidence_prefixes": ["model-provider/"],
        "validation_needles": ["model", "model-provider"],
    },
    {
        "key": "archive_sync",
        "label": "Archive sync",
        "env_group": "archive_sync",
        "evidence_group": "archive_storage",
        "evidence_prefixes": ["archive-storage/"],
        "validation_needles": ["archive", "archive-storage"],
    },
]
PREREQUISITE_LABELS = {
    "final_readiness_gate": "Final live readiness gate",
    "source_owner_decisions": "Source owner decisions",
    "feishu_delivery": "Feishu delivery spike",
    "model_provider": "Model provider spike",
    "archive_sync": "Archive/storage spike",
    "core_mvp_issues": "Core MVP issues",
}
MVP_ISSUE_UNLOCKS = [
    ("#10", "Repo and CI", ["final_readiness_gate"]),
    ("#11", "Contracts", ["feishu_delivery", "model_provider", "archive_sync"]),
    ("#12", "Taxonomy and source registry", ["source_owner_decisions"]),
    ("#13", "Source connectors", ["source_owner_decisions"]),
    ("#14", "Ranking and Selection Rationale", ["model_provider"]),
    ("#15", "Briefing generation and Confidence Notices", ["model_provider", "feishu_delivery"]),
    ("#16", "Archive Package", ["archive_sync"]),
    ("#17", "Feishu delivery", ["feishu_delivery"]),
    ("#18", "Operations Console", []),
    ("#19", "Deployment and secrets", ["final_readiness_gate"]),
    ("#20", "End-to-end MVP acceptance", ["final_readiness_gate", "source_owner_decisions", "core_mvp_issues"]),
]
MVP_ISSUE_DRAFTS = {
    "#10": "docs/issues/mvp/01-repo-ci-foundation.md",
    "#11": "docs/issues/mvp/02-contract-schemas.md",
    "#12": "docs/issues/mvp/03-taxonomy-source-registry.md",
    "#13": "docs/issues/mvp/04-source-connectors.md",
    "#14": "docs/issues/mvp/05-ranking-selection-rationale.md",
    "#15": "docs/issues/mvp/06-briefing-generation-confidence.md",
    "#16": "docs/issues/mvp/07-archive-package.md",
    "#17": "docs/issues/mvp/08-feishu-delivery.md",
    "#18": "docs/issues/mvp/09-operations-console.md",
    "#19": "docs/issues/mvp/10-deployment-secrets.md",
    "#20": "docs/issues/mvp/11-e2e-mvp-acceptance.md",
}


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


def count_phrase(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def matches_any_prefix(value: str, prefixes: list[str]) -> bool:
    return any(value.startswith(prefix) for prefix in prefixes)


def matches_any_needle(value: str, needles: list[str]) -> bool:
    lowered = value.lower()
    return any(needle in lowered for needle in needles)


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
        "worksheet_path": display_path(evidence_root / SOURCE_OWNER_WORKSHEET_RELATIVE),
        "batch_plan_path": display_path(evidence_root / SOURCE_OWNER_BATCH_PLAN_RELATIVE),
        "request_packet_path": display_path(evidence_root / SOURCE_OWNER_REQUEST_PACKET_RELATIVE),
    }


def live_workstream_rows(live_summary: dict) -> list[dict[str, object]]:
    evidence_missing = live_summary["evidence"]["missing"]
    rows = []
    for spec in LIVE_WORKSTREAMS:
        env_group = spec["env_group"]
        env_missing = live_summary["environment"][env_group]["missing"]
        final_group_status = live_summary["final_evidence_groups"][spec["evidence_group"]]["status"]
        files_missing = [
            path
            for path in evidence_missing
            if matches_any_prefix(path, spec["evidence_prefixes"])
        ]
        validation_missing = [
            item
            for item in live_summary["evidence_validation"]["missing"]
            if matches_any_needle(item, spec["validation_needles"])
        ]
        validation_failures = [
            item
            for item in live_summary["evidence_validation"]["failures"]
            if matches_any_needle(item, spec["validation_needles"])
        ]
        rows.append(
            {
                "workstream": spec["label"],
                "status": "blocked" if final_group_status != "complete" or env_missing or files_missing or validation_missing or validation_failures else "ready for final gate",
                "final_group_status": final_group_status,
                "missing_env": len(env_missing),
                "missing_evidence": len(files_missing),
                "missing_validation": len(validation_missing),
                "validation_failures": len(validation_failures),
            }
        )
    return rows


def prerequisite_states(live_summary: dict, source_summary: dict) -> dict[str, dict[str, str]]:
    states: dict[str, dict[str, str]] = {}
    for spec in LIVE_WORKSTREAMS:
        row = next(row for row in live_workstream_rows(live_summary) if row["workstream"] == spec["label"])
        blockers = []
        if row["final_group_status"] != "complete":
            blockers.append(f"final evidence group {row['final_group_status']}")
        if row["missing_env"]:
            blockers.append(count_phrase(int(row["missing_env"]), "env var", "env vars"))
        if row["missing_evidence"]:
            blockers.append(count_phrase(int(row["missing_evidence"]), "evidence file", "evidence files"))
        if row["missing_validation"]:
            blockers.append(count_phrase(int(row["missing_validation"]), "validation input", "validation inputs"))
        if row["validation_failures"]:
            blockers.append(count_phrase(int(row["validation_failures"]), "validation failure", "validation failures"))
        states[spec["key"]] = {
            "status": "blocked" if blockers else "ready",
            "detail": ", ".join(blockers) if blockers else "issue-specific evidence is ready",
        }

    live_env_missing = sum(len(group["missing"]) for group in live_summary["environment"].values())
    live_evidence_missing = len(live_summary["evidence"]["missing"])
    incomplete_final_groups = [
        group
        for group, group_summary in live_summary["final_evidence_groups"].items()
        if group_summary["status"] != "complete"
    ]
    validation_missing = len(live_summary["evidence_validation"]["missing"])
    validation_failures = len(live_summary["evidence_validation"]["failures"])
    final_blockers = []
    if live_env_missing:
        final_blockers.append(count_phrase(live_env_missing, "env var", "env vars"))
    if live_evidence_missing:
        final_blockers.append(count_phrase(live_evidence_missing, "evidence file", "evidence files"))
    if incomplete_final_groups:
        final_blockers.append(count_phrase(len(incomplete_final_groups), "incomplete final evidence group", "incomplete final evidence groups"))
    if validation_missing:
        final_blockers.append(count_phrase(validation_missing, "validation input", "validation inputs"))
    if validation_failures:
        final_blockers.append(count_phrase(validation_failures, "validation failure", "validation failures"))
    states["final_readiness_gate"] = {
        "status": "blocked" if final_blockers else "ready",
        "detail": ", ".join(final_blockers) if final_blockers else "live readiness evidence is ready",
    }

    source_blockers = []
    if source_summary["counts"]["missing"]:
        source_blockers.append(count_phrase(source_summary["counts"]["missing"], "missing decision", "missing decisions"))
    if source_summary["counts"]["invalid"]:
        source_blockers.append(count_phrase(source_summary["counts"]["invalid"], "invalid decision", "invalid decisions"))
    states["source_owner_decisions"] = {
        "status": "blocked" if source_blockers else "ready",
        "detail": ", ".join(source_blockers) if source_blockers else "owner decisions are valid or no longer open",
    }
    states["core_mvp_issues"] = {
        "status": "blocked",
        "detail": "core MVP issues #10-#19 must complete before E2E acceptance",
    }
    return states


def mvp_issue_statuses(live_summary: dict, source_summary: dict) -> list[dict[str, object]]:
    states = prerequisite_states(live_summary, source_summary)
    final_gate_blocked = states["final_readiness_gate"]["status"] == "blocked"
    rows = []
    for issue, module, prerequisites in MVP_ISSUE_UNLOCKS:
        blocker_details = [
            f"{PREREQUISITE_LABELS[key]}: {states[key]['detail']}"
            for key in prerequisites
            if states[key]["status"] == "blocked"
        ]
        rows.append(
            {
                "issue": issue,
                "module": module,
                "draft_path": MVP_ISSUE_DRAFTS[issue],
                "url": f"https://github.com/KG9750/TechNews/issues/{issue.lstrip('#')}",
                "issue_specific_status": "blocked" if blocker_details else "ready for final triage",
                "blocker_details": blocker_details,
                "global_readiness_gate": states["final_readiness_gate"]["status"],
                "global_readiness_detail": states["final_readiness_gate"]["detail"],
                "label_action": (
                    "Keep `needs-triage` until final readiness and GitHub tracker gates pass."
                    if final_gate_blocked or blocker_details
                    else "Review for `ready-for-agent` after GitHub tracker gate passes."
                ),
            }
        )
    return rows


def mvp_issue_unlock_rows(live_summary: dict, source_summary: dict) -> list[str]:
    rows = [
        "| Issue | Module | Issue-specific status | Remaining issue-specific inputs | Label gate |",
        "| --- | --- | --- | --- | --- |",
    ]
    for status in mvp_issue_statuses(live_summary, source_summary):
        rows.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(status["issue"]),
                    markdown_cell(status["module"]),
                    markdown_cell(status["issue_specific_status"]),
                    markdown_cell("; ".join(status["blocker_details"]) if status["blocker_details"] else "None."),
                    markdown_cell(status["label_action"]),
                ]
            )
            + " |"
        )
    return rows


def external_input_request_rows(live_summary: dict) -> list[str]:
    rows = [
        "| Workstream | Linked issue | Required variable names | Missing now | Configure at | Safe request wording | Evidence after configured |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for request in EXTERNAL_INPUT_REQUESTS:
        env = live_summary["environment"][request["env_group"]]
        required = live_preflight.ENV_GROUPS[request["env_group"]]
        rows.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(request["workstream"]),
                    markdown_cell(request["issue"]),
                    markdown_cell(", ".join(required)),
                    markdown_cell(", ".join(env["missing"]) if env["missing"] else "None."),
                    markdown_cell(request["configure_at"]),
                    markdown_cell(request["safe_request"]),
                    markdown_cell(request["after_configured"]),
                ]
            )
            + " |"
        )
    return rows


def spike_commands_by_env_group() -> dict[str, list[str]]:
    return {
        spec["env_group"]: spec["commands"]
        for spec in live_preflight.SPIKE_PACKET_SPECS
    }


def evidence_files_for_env_group(env_group: str) -> list[str]:
    evidence_group = next(
        spec["evidence_group"]
        for spec in LIVE_WORKSTREAMS
        if spec["env_group"] == env_group
    )
    return live_preflight.FINAL_EVIDENCE_GROUPS[evidence_group]


def build_external_input_request_packet(evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> str:
    live_summary = live_preflight.build_summary(evidence_root, run_helpers=False)
    commands_by_env_group = spike_commands_by_env_group()
    sections = []
    for request in EXTERNAL_INPUT_REQUESTS:
        env = live_summary["environment"][request["env_group"]]
        required = live_preflight.ENV_GROUPS[request["env_group"]]
        sections.extend(
            [
                f"## {request['workstream']}",
                "",
                f"- Linked issue: {request['issue']}",
                f"- Configure at: {request['configure_at']}",
                f"- Safe request wording: {request['safe_request']}",
                f"- After configured: {request['after_configured']}",
                "",
                "Required variable names:",
                markdown_bullets(required),
                "",
                "Missing variable names now:",
                markdown_bullets(env["missing"], empty_label="None missing."),
                "",
                "Required evidence files:",
                markdown_bullets(evidence_files_for_env_group(request["env_group"])),
                "",
                "Commands after values are configured:",
                "```bash",
                *commands_by_env_group[request["env_group"]],
                "```",
                "",
            ]
        )

    return "\n".join(
        [
            "# External Input Request Packet",
            "",
            "This ignored packet is for requesting live spike inputs through a secure channel. It names variables, evidence paths, and commands only; do not paste real values here, in GitHub, or in tracked files.",
            "",
            f"- Generated at: {utc_now()}",
            f"- Evidence root: `{display_path(evidence_root)}`",
            "- Final gate after evidence is complete: `python3 scripts/check_readiness.py --require-live --require-evidence`",
            "",
            *sections,
            "## Share Guardrails",
            "",
            "- Share variable names and setup instructions only.",
            "- Keep real credentials, Feishu recipient ids, provider responses, local paths, and NAS/cloud targets in the secure environment.",
            "- Commit tracked docs/scripts before generating the final readiness manifest.",
        ]
    )


def write_external_input_request_packet(output_path: Path, evidence_root: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_external_input_request_packet(evidence_root) + "\n", encoding="utf-8")


def mvp_issue_packet_filename(issue: str) -> str:
    return f"issue-{issue.lstrip('#')}.md"


def mvp_issue_packet_path(output_dir: Path, issue: str) -> Path:
    return output_dir / mvp_issue_packet_filename(issue)


def build_mvp_issue_packet(status: dict[str, object]) -> str:
    blockers = status["blocker_details"]
    return "\n".join(
        [
            f"# MVP Issue Triage Packet: {status['issue']} {status['module']}",
            "",
            "This packet is context only. It does not change GitHub labels and does not replace the authoritative readiness gate.",
            "",
            f"- GitHub issue: {status['url']}",
            f"- Issue body draft: `{status['draft_path']}`",
            f"- Issue-specific status: {status['issue_specific_status']}",
            f"- Global readiness gate: {status['global_readiness_gate']} ({status['global_readiness_detail']})",
            f"- Label action: {status['label_action']}",
            "",
            "## Remaining Issue-Specific Inputs",
            "",
            markdown_bullets(blockers, empty_label="None."),
            "",
            "## Verification Before Label Change",
            "",
            "```bash",
            "python3 scripts/check_readiness.py --require-live --require-evidence",
            "python3 scripts/check_readiness.py --require-github",
            "```",
            "",
            "## Guardrails",
            "",
            "- Keep `needs-triage` while any remaining input above is blocked.",
            "- Move to `ready-for-agent` only when the issue body needs no extra product decision.",
            "- Do not paste secrets, recipient ids, local paths, NAS targets, or raw provider responses into GitHub.",
        ]
    )


def write_mvp_issue_packets(output_dir: Path, evidence_root: Path) -> int:
    live_summary = live_preflight.build_summary(evidence_root, run_helpers=False)
    source_summary = source_owner_summary(evidence_root)
    statuses = mvp_issue_statuses(live_summary, source_summary)
    output_dir.mkdir(parents=True, exist_ok=True)
    for status in statuses:
        mvp_issue_packet_path(output_dir, str(status["issue"])).write_text(
            build_mvp_issue_packet(status) + "\n",
            encoding="utf-8",
        )
    print(f"MVP issue triage packets written: {len(statuses)} -> {display_path(output_dir)}")
    return len(statuses)


def build_packet(evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> str:
    live_summary = live_preflight.build_summary(evidence_root, run_helpers=False)
    source_summary = source_owner_summary(evidence_root)
    live_env_missing = sum(len(group["missing"]) for group in live_summary["environment"].values())
    live_evidence_missing = len(live_summary["evidence"]["missing"])
    incomplete_final_groups = [
        group
        for group, group_summary in live_summary["final_evidence_groups"].items()
        if group_summary["status"] != "complete"
    ]
    live_validation_missing = len(live_summary["evidence_validation"]["missing"])
    live_validation_failures = len(live_summary["evidence_validation"]["failures"])
    workstream_rows = live_workstream_rows(live_summary)
    issue_unlock_rows = mvp_issue_unlock_rows(live_summary, source_summary)
    external_input_rows = external_input_request_rows(live_summary)

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
        "| Workstream | Status | Final evidence group | Missing env vars | Missing evidence files | Missing validation inputs | Validation failures |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in workstream_rows:
        table_rows.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(row["workstream"]),
                    markdown_cell(row["status"]),
                    markdown_cell(row["final_group_status"]),
                    markdown_cell(row["missing_env"]),
                    markdown_cell(row["missing_evidence"]),
                    markdown_cell(row["missing_validation"]),
                    markdown_cell(row["validation_failures"]),
                ]
            )
            + " |"
        )
    manifest_validation_missing = [
        item
        for item in live_summary["evidence_validation"]["missing"]
        if "manifest" in item.lower()
    ]
    manifest_validation_failures = [
        item
        for item in live_summary["evidence_validation"]["failures"]
        if "manifest" in item.lower()
    ]
    table_rows.append(
        "| "
        + " | ".join(
            [
                "Readiness manifest",
                "blocked" if live_summary["final_evidence_groups"]["readiness_manifest"]["status"] != "complete" or "readiness-manifest.json" in live_summary["evidence"]["missing"] or manifest_validation_missing or manifest_validation_failures else "ready for final gate",
                live_summary["final_evidence_groups"]["readiness_manifest"]["status"],
                "0",
                "1" if "readiness-manifest.json" in live_summary["evidence"]["missing"] else "0",
                str(len(manifest_validation_missing)),
                str(len(manifest_validation_failures)),
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
                "not applicable",
                "0",
                f"{source_summary['counts']['invalid']} invalid, {source_summary['counts']['missing']} missing",
                "0",
                "0",
            ]
        )
        + " |"
    )
    issue_rows = [
        f"{label}: {url}"
        for label, url in GITHUB_ISSUES
    ]

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
            f"- Incomplete final evidence groups: {len(incomplete_final_groups)}",
            f"- Missing live evidence validation inputs: {live_validation_missing}",
            f"- Live evidence validation failures: {live_validation_failures}",
            f"- Open source owner decisions: {source_summary['open']}",
            f"- Valid source owner decisions: {source_summary['counts']['valid']}",
            f"- Invalid source owner decisions: {source_summary['counts']['invalid']}",
            f"- Missing source owner decisions: {source_summary['counts']['missing']}",
            "",
            "## Linked Packets",
            "",
            f"- Live execution packet: `{display_path(evidence_root / 'live-readiness-packet.md')}`",
            f"- Live spike packets: `{display_path(evidence_root / 'live-spike-packets')}`",
            f"- Live preflight summary: `{display_path(evidence_root / 'live-readiness-preflight.json')}`",
            f"- Final redaction review packet: `{display_path(evidence_root / 'final-redaction-review.md')}`",
            f"- External input request packet: `{display_path(evidence_root / EXTERNAL_INPUT_REQUEST_RELATIVE)}`",
            f"- Source owner review index: `{source_summary['index_path']}`",
            f"- Source owner worksheet: `{source_summary['worksheet_path']}`",
            f"- Source owner batch plan: `{source_summary['batch_plan_path']}`",
            f"- Source owner request packet: `{source_summary['request_packet_path']}`",
            f"- MVP issue triage packets: `{display_path(evidence_root / MVP_ISSUE_PACKET_DIR_RELATIVE)}`",
            "",
            "## GitHub Issue Links",
            "",
            markdown_bullets(issue_rows, empty_label="No GitHub issues linked."),
            "",
            "## Live Environment Names",
            "",
            *env_sections,
            "## External Input Request Checklist",
            "",
            "Use this checklist to request missing live-spike inputs without collecting real values in GitHub, tracked files, or generated packets.",
            "",
            *external_input_rows,
            "",
            "## Blocking Workstreams",
            "",
            *table_rows,
            "",
            "## MVP Issue Unlock Matrix",
            "",
            *issue_unlock_rows,
            "",
            "## Source Owner Decision Types",
            "",
            markdown_bullets(source_decision_rows, empty_label="No open source owner decisions."),
            "",
            "## Execution Order",
            "",
            "```bash",
            "python3 scripts/spikes/live_readiness_preflight.py --dry-run --write-packet --write-spike-packets",
            "python3 scripts/source_owner_review_decision.py --draft-all",
            "python3 scripts/source_owner_review_decision.py --packet-all",
            "python3 scripts/source_owner_review_decision.py --packet-index",
            "python3 scripts/source_owner_review_decision.py --worksheet",
            "python3 scripts/source_owner_review_decision.py --batch-plan",
            "python3 scripts/readiness_action_packet.py --write-mvp-issue-packets",
            "python3 scripts/spikes/feishu_delivery_spike.py",
            "python3 scripts/spikes/feishu_delivery_spike.py --validate-evidence",
            "python3 scripts/spikes/model_provider_spike.py --validate-requests",
            "python3 scripts/spikes/model_provider_spike.py --validate-evidence",
            "python3 scripts/spikes/archive_storage_spike.py",
            "python3 scripts/spikes/archive_storage_spike.py --validate-evidence",
            "python3 scripts/spikes/readiness_manifest.py --write-final-review-packet",
            "python3 scripts/spikes/live_readiness_preflight.py --strict --write-packet --write-spike-packets",
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
    parser.add_argument("--write-mvp-issue-packets", action="store_true")
    parser.add_argument("--mvp-issue-packet-dir", default="")
    args = parser.parse_args()

    evidence_root = Path(args.evidence_root)
    output_path = Path(args.output)
    write_packet(output_path, evidence_root)
    print(f"Readiness action packet written to {display_path(output_path)}")
    external_input_path = evidence_root / EXTERNAL_INPUT_REQUEST_RELATIVE
    write_external_input_request_packet(external_input_path, evidence_root)
    print(f"External input request packet written to {display_path(external_input_path)}")
    if args.write_mvp_issue_packets:
        packet_dir = Path(args.mvp_issue_packet_dir) if args.mvp_issue_packet_dir else evidence_root / MVP_ISSUE_PACKET_DIR_RELATIVE
        write_mvp_issue_packets(packet_dir, evidence_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
