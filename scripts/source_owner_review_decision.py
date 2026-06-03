#!/usr/bin/env python3
"""Draft, validate, and apply source owner review decisions.

This helper does not make product or legal decisions. It turns each open source
owner review queue item into a fillable evidence file under ignored evidence/.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "fixtures/source-ingestion/source-owner-review-queue.json"
POLICY_PATH = ROOT / "fixtures/source-ingestion/source-access-policy.json"
REVIEW_PATH = ROOT / "docs/source-eligibility-reviews.md"
REGISTRY_PATH = ROOT / "docs/source-registry.md"
DEFAULT_EVIDENCE_DIR = ROOT / "evidence/source-owner-reviews"
VALID_DECISIONS = {"eligible", "needs_review", "blocked", "deferred"}
SOURCE_REVIEW_BATCHES = [
    {
        "title": "Batch 1 - Access Path Blockers",
        "decision_needed": ["automated_access_permission", "manual_per_item_review"],
        "goal": "Decide whether an automated access path exists before connector work starts.",
        "default_if_unresolved": "Keep manual-only or per-item review behavior with production auto-ingestion disabled.",
    },
    {
        "title": "Batch 2 - RSS Feed Reuse Scope",
        "decision_needed": ["feed_reuse_scope"],
        "goal": "Confirm feed metadata reuse and generated-summary boundaries for public RSS connectors.",
        "default_if_unresolved": "Keep RSS sources probe-only and disable production auto-ingestion.",
    },
    {
        "title": "Batch 3 - Generated Summary And Media Permission",
        "decision_needed": ["summary_permission"],
        "goal": "Confirm generated-summary, source-media, and brand/attribution rules for media and company sources.",
        "default_if_unresolved": "Allow fixture/manual validation only; keep generated summaries and media blocked for production.",
    },
    {
        "title": "Batch 4 - License Obligations",
        "decision_needed": ["license_obligation"],
        "goal": "Resolve NC, share-alike, non-commercial, or explicit permission obligations.",
        "default_if_unresolved": "Keep source locked, blocked, or deferred rather than enabling automated ingestion.",
    },
]


class ReviewError(Exception):
    pass


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_queue_items() -> dict[str, dict]:
    queue = read_json(QUEUE_PATH)
    return {item["source_id"]: item for item in queue["items"]}


def load_policy_rows() -> dict[str, dict]:
    policy = read_json(POLICY_PATH)
    return {source["source_id"]: source for source in policy["sources"]}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewError(message)


def split_markdown_row(line: str) -> list[str]:
    return [part.strip() for part in line.strip().strip("|").split("|")]


def build_markdown_row(columns: list[str]) -> str:
    return "| " + " | ".join(columns) + " |"


def markdown_table_row(path: Path, source_id: str) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header: list[str] | None = None
    for line in lines:
        if line.startswith("| ID |"):
            header = split_markdown_row(line)
            continue
        if not header or not line.startswith(f"| {source_id} |"):
            continue
        columns = split_markdown_row(line)
        require(len(columns) == len(header), f"{path.relative_to(ROOT)} row has wrong column count: {source_id}")
        return dict(zip(header, columns))
    raise ReviewError(f"{path.relative_to(ROOT)} missing row: {source_id}")


def list_open() -> int:
    items = load_queue_items()
    for source_id in sorted(items):
        item = items[source_id]
        if item.get("review_status") == "open":
            print(
                "\t".join(
                    [
                        source_id,
                        item["decision_needed"],
                        item["default_connector_mode"],
                        item["next_action"],
                    ]
                )
            )
    return 0


def current_artifact_context(source_id: str, item: dict, policy: dict) -> dict:
    return {
        "review_matrix_row": markdown_table_row(REVIEW_PATH, source_id),
        "source_registry_row": markdown_table_row(REGISTRY_PATH, source_id),
        "source_access_policy": policy,
        "owner_review_queue_item": item,
    }


def draft_payload(source_id: str) -> dict:
    items = load_queue_items()
    policies = load_policy_rows()
    require(source_id in items, f"source is not in owner review queue: {source_id}")
    item = items[source_id]
    policy = policies.get(source_id, {})
    require(item.get("review_status") == "open", f"source owner review is not open: {source_id}")
    return {
        "source_id": source_id,
        "reviewed_at": "TEMPLATE_YYYY-MM-DD",
        "reviewed_by": item.get("review_owner", "Briefing Administrator"),
        "decision": "TEMPLATE_DECISION",
        "decision_options": sorted(VALID_DECISIONS),
        "current_artifact_context": current_artifact_context(source_id, item, policy),
        "evidence_checked": [
            {
                "required_evidence": evidence,
                "url_or_note": "TEMPLATE_EVIDENCE_URL_OR_NOTE",
                "checked_at": "TEMPLATE_YYYY-MM-DD",
            }
            for evidence in item.get("evidence_required", [])
        ],
        "owner_question_answers": [
            {
                "question": question,
                "answer": "TEMPLATE_ANSWER",
            }
            for question in item.get("owner_questions", [])
        ],
        "policy_after_decision": {
            "eligibility_state": "TEMPLATE_DECISION",
            "connector_mode": item["default_connector_mode"],
            "production_auto_ingestion": False,
            "full_text_storage": "not_stored",
            "summary_policy": policy.get("summary_policy", "owner_review_required_before_generated_summary"),
            "media_policy": "none_until_approved",
            "rate_policy": policy.get("rate_policy", "conservative_default"),
        },
        "implementation_guardrail": "TEMPLATE_REQUIRED_GUARDRAIL",
        "artifact_updates": {
            "review_matrix": {
                "terms_evidence": "TEMPLATE_TERMS_EVIDENCE_CELL",
                "summary_storage": "TEMPLATE_SUMMARY_STORAGE_CELL",
                "media_use": "TEMPLATE_MEDIA_USE_CELL",
                "rate_limit": "TEMPLATE_RATE_LIMIT_CELL",
                "next_action": "TEMPLATE_NEXT_ACTION_CELL",
            },
            "source_registry": {
                "eligibility_notes": "TEMPLATE_REGISTRY_ELIGIBILITY_NOTES",
            },
        },
        "docs_to_update_after_decision": [
            "docs/source-eligibility-reviews.md",
            "fixtures/source-ingestion/source-access-policy.json",
            "fixtures/source-ingestion/source-owner-review-queue.json",
            "docs/source-registry.md",
        ],
    }


def write_draft(source_id: str, evidence_dir: Path) -> int:
    output = evidence_dir / f"{source_id}.decision.json"
    write_json(output, draft_payload(source_id))
    print(f"Draft owner decision written to {output.relative_to(ROOT)}")
    return 0


def open_source_ids() -> list[str]:
    items = load_queue_items()
    return sorted(source_id for source_id, item in items.items() if item.get("review_status") == "open")


def write_all_drafts(evidence_dir: Path) -> int:
    written = 0
    kept = 0
    for source_id in open_source_ids():
        output = evidence_dir / f"{source_id}.decision.json"
        if output.exists():
            kept += 1
            continue
        write_json(output, draft_payload(source_id))
        written += 1
    print(f"Draft owner decisions prepared: {written} written, {kept} existing, {written + kept} open items")
    return 0


def packet_path(evidence_dir: Path, source_id: str) -> Path:
    return evidence_dir / f"{source_id}.packet.md"


def packet_index_path(evidence_dir: Path) -> Path:
    return evidence_dir / "index.md"


def worksheet_path(evidence_dir: Path) -> Path:
    return evidence_dir / "worksheet.md"


def batch_plan_path(evidence_dir: Path) -> Path:
    return evidence_dir / "batch-plan.md"


def markdown_bullets(items: list[str]) -> str:
    if not items:
        return "- None recorded."
    return "\n".join(f"- {item}" for item in items)


def markdown_fields(row: dict, fields: list[str]) -> str:
    return "\n".join(f"- {field}: {row.get(field, '')}" for field in fields)


def markdown_cell(value: object) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|")


def review_packet(source_id: str, evidence_dir: Path = DEFAULT_EVIDENCE_DIR) -> str:
    payload = draft_payload(source_id)
    context = payload["current_artifact_context"]
    review_row = context["review_matrix_row"]
    registry_row = context["source_registry_row"]
    policy = context["source_access_policy"]
    item = context["owner_review_queue_item"]
    decision_file = decision_path(evidence_dir, source_id).relative_to(ROOT)

    return "\n".join(
        [
            f"# Source Owner Review Packet: {source_id}",
            "",
            "This packet is context only. Complete the JSON decision file; do not edit this packet as the source of truth.",
            "",
            f"Decision file: `{decision_file}`",
            "",
            "## Source Registry Context",
            "",
            markdown_fields(
                registry_row,
                [
                    "Source",
                    "Type",
                    "URL or feed",
                    "Primary section",
                    "Secondary sections",
                    "Trust tier",
                    "Media",
                    "Eligibility notes",
                ],
            ),
            "",
            "## Current Eligibility Review",
            "",
            markdown_fields(
                review_row,
                [
                    "Eligibility state",
                    "Access method",
                    "Terms evidence",
                    "Summary/storage",
                    "Media use",
                    "Rate limit",
                    "Attribution",
                    "Disallowed behavior",
                    "Next action",
                ],
            ),
            "",
            "## Current Access Policy",
            "",
            "\n".join(
                [
                    f"- connector_mode: {policy.get('connector_mode', '')}",
                    f"- production_auto_ingestion: {policy.get('production_auto_ingestion', '')}",
                    f"- summary_policy: {policy.get('summary_policy', '')}",
                    f"- media_policy: {policy.get('media_policy', '')}",
                    f"- rate_policy: {policy.get('rate_policy', '')}",
                ]
            ),
            "",
            "## Owner Decision Needed",
            "",
            "\n".join(
                [
                    f"- decision_needed: {item['decision_needed']}",
                    f"- default_connector_mode: {item['default_connector_mode']}",
                    f"- next_action: {item['next_action']}",
                    f"- production_auto_ingestion_until_resolved: {item['production_auto_ingestion_until_resolved']}",
                    f"- media_use_until_resolved: {item['media_use_until_resolved']}",
                ]
            ),
            "",
            "## Evidence Required",
            "",
            markdown_bullets(item.get("evidence_required", [])),
            "",
            "## Owner Questions",
            "",
            markdown_bullets(item.get("owner_questions", [])),
            "",
            "## Suggested Commands",
            "",
            "```bash",
            f"python3 scripts/source_owner_review_decision.py --validate {decision_file}",
            f"python3 scripts/source_owner_review_decision.py --apply {decision_file} --dry-run",
            f"python3 scripts/source_owner_review_decision.py --apply {decision_file}",
            "```",
        ]
    )


def write_packet(source_id: str, evidence_dir: Path) -> int:
    output = packet_path(evidence_dir, source_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(review_packet(source_id, evidence_dir) + "\n", encoding="utf-8")
    print(f"Source owner review packet written to {output.relative_to(ROOT)}")
    return 0


def write_all_packets(evidence_dir: Path) -> int:
    source_ids = open_source_ids()
    for source_id in source_ids:
        output = packet_path(evidence_dir, source_id)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(review_packet(source_id, evidence_dir) + "\n", encoding="utf-8")
    print(f"Source owner review packets prepared: {len(source_ids)} written, {len(source_ids)} open items")
    return 0


def decision_file_state(evidence_dir: Path, source_id: str) -> dict[str, str]:
    path = decision_path(evidence_dir, source_id)
    if not path.exists():
        return {
            "status": "missing",
            "decision": "",
            "detail": str(path.relative_to(ROOT)),
        }
    decision = ""
    try:
        payload = read_json(path)
        decision = str(payload.get("decision", ""))
        validated_payload(path)
    except (ReviewError, json.JSONDecodeError) as error:
        return {
            "status": "invalid",
            "decision": decision,
            "detail": str(error),
        }
    return {
        "status": "valid",
        "decision": decision,
        "detail": "ready to apply",
    }


def review_packet_index(evidence_dir: Path = DEFAULT_EVIDENCE_DIR) -> str:
    items = load_queue_items()
    rows = []
    counts = {"valid": 0, "invalid": 0, "missing": 0}
    for source_id in open_source_ids():
        item = items[source_id]
        registry = markdown_table_row(REGISTRY_PATH, source_id)
        state = decision_file_state(evidence_dir, source_id)
        counts[state["status"]] += 1
        rows.append(
            {
                "source_id": source_id,
                "source": registry["Source"],
                "decision_needed": item["decision_needed"],
                "status": state["status"],
                "decision": state["decision"],
                "decision_file": decision_path(evidence_dir, source_id).name,
                "packet_file": packet_path(evidence_dir, source_id).name,
                "next_action": item["next_action"],
            }
        )

    grouped_sections = []
    for decision_needed in sorted({row["decision_needed"] for row in rows}):
        grouped_sections.extend(
            [
                f"### {decision_needed}",
                "",
                "| Source ID | Source | Status | Decision | Decision file | Packet | Next action |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in rows:
            if row["decision_needed"] != decision_needed:
                continue
            grouped_sections.append(
                "| "
                + " | ".join(
                    [
                        markdown_cell(row["source_id"]),
                        markdown_cell(row["source"]),
                        markdown_cell(row["status"]),
                        markdown_cell(row["decision"]),
                        markdown_cell(row["decision_file"]),
                        markdown_cell(row["packet_file"]),
                        markdown_cell(row["next_action"]),
                    ]
                )
                + " |"
            )
        grouped_sections.append("")

    return "\n".join(
        [
            "# Source Owner Review Index",
            "",
            "This packet is context only. Complete the JSON decision files; do not edit this index as the source of truth.",
            "",
            f"- Open decisions: {len(rows)}",
            f"- Valid decision files: {counts['valid']}",
            f"- Invalid decision files: {counts['invalid']}",
            f"- Missing decision files: {counts['missing']}",
            "",
            "## Suggested Commands",
            "",
            "```bash",
            "python3 scripts/source_owner_review_decision.py --status",
            "python3 scripts/source_owner_review_decision.py --draft-all",
            "python3 scripts/source_owner_review_decision.py --packet-all",
            "python3 scripts/source_owner_review_decision.py --packet-index",
            "python3 scripts/source_owner_review_decision.py --worksheet",
            "python3 scripts/source_owner_review_decision.py --validate-all",
            "python3 scripts/source_owner_review_decision.py --apply-all --dry-run",
            "```",
            "",
            "## Open Items By Decision Needed",
            "",
            *grouped_sections,
        ]
    )


def write_packet_index(evidence_dir: Path) -> int:
    output = packet_index_path(evidence_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(review_packet_index(evidence_dir) + "\n", encoding="utf-8")
    print(f"Source owner review packet index written to {output.relative_to(ROOT)}")
    return 0


def review_worksheet(evidence_dir: Path = DEFAULT_EVIDENCE_DIR) -> str:
    items = load_queue_items()
    rows = []
    prompt_sections = []
    for source_id in open_source_ids():
        item = items[source_id]
        registry = markdown_table_row(REGISTRY_PATH, source_id)
        state = decision_file_state(evidence_dir, source_id)
        decision_file = decision_path(evidence_dir, source_id).relative_to(ROOT)
        packet_file = packet_path(evidence_dir, source_id).relative_to(ROOT)
        evidence_required = item.get("evidence_required", [])
        owner_questions = item.get("owner_questions", [])
        rows.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(source_id),
                    markdown_cell(registry["Source"]),
                    markdown_cell(state["status"]),
                    markdown_cell(item["decision_needed"]),
                    markdown_cell(decision_file),
                    markdown_cell(packet_file),
                    markdown_cell(len(evidence_required)),
                    markdown_cell(len(owner_questions)),
                    markdown_cell(item["next_action"]),
                ]
            )
            + " |"
        )
        prompt_sections.extend(
            [
                f"### {source_id} - {registry['Source']}",
                "",
                f"- Decision file: `{decision_file}`",
                f"- Packet: `{packet_file}`",
                f"- Current draft status: {state['status']}",
                f"- Decision needed: {item['decision_needed']}",
                f"- Default connector mode: {item['default_connector_mode']}",
                f"- Next action: {item['next_action']}",
                "",
                "Evidence required:",
                "",
                markdown_bullets(evidence_required),
                "",
                "Owner questions:",
                "",
                markdown_bullets(owner_questions),
                "",
            ]
        )

    return "\n".join(
        [
            "# Source Owner Review Worksheet",
            "",
            "This worksheet is context only. Complete the JSON decision files; do not edit this worksheet as the source of truth.",
            "",
            f"- Open decisions: {len(rows)}",
            f"- Decision directory: `{evidence_dir.relative_to(ROOT)}`",
            "",
            "## Batch Commands",
            "",
            "```bash",
            "python3 scripts/source_owner_review_decision.py --status",
            "python3 scripts/source_owner_review_decision.py --draft-all",
            "python3 scripts/source_owner_review_decision.py --packet-all",
            "python3 scripts/source_owner_review_decision.py --packet-index",
            "python3 scripts/source_owner_review_decision.py --worksheet",
            "python3 scripts/source_owner_review_decision.py --validate-all",
            "python3 scripts/source_owner_review_decision.py --apply-all --dry-run",
            "```",
            "",
            "## Decision Fields To Complete",
            "",
            "- `reviewed_at` and `reviewed_by`",
            "- `decision`: one of `eligible`, `needs_review`, `blocked`, or `deferred`",
            "- every `evidence_checked` item",
            "- every `owner_question_answers` item",
            "- `policy_after_decision` with full text storage still `not_stored`",
            "- `implementation_guardrail`",
            "- `artifact_updates` Markdown cell text",
            "",
            "## Open Decision Checklist",
            "",
            "| Source ID | Source | Draft status | Decision needed | Decision file | Packet | Evidence items | Owner questions | Next action |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            *rows,
            "",
            "## Per-Source Prompts",
            "",
            *prompt_sections,
        ]
    )


def write_worksheet(evidence_dir: Path) -> int:
    output = worksheet_path(evidence_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(review_worksheet(evidence_dir) + "\n", encoding="utf-8")
    print(f"Source owner review worksheet written to {output.relative_to(ROOT)}")
    return 0


def review_batch_plan(evidence_dir: Path = DEFAULT_EVIDENCE_DIR) -> str:
    items = load_queue_items()
    batch_sections = []
    summary_rows = []
    assigned_source_ids: set[str] = set()

    for batch in SOURCE_REVIEW_BATCHES:
        decision_types = set(batch["decision_needed"])
        source_ids = [
            source_id
            for source_id in open_source_ids()
            if items[source_id]["decision_needed"] in decision_types
        ]
        assigned_source_ids.update(source_ids)
        status_counts = {"valid": 0, "invalid": 0, "missing": 0}
        rows = []
        for source_id in source_ids:
            item = items[source_id]
            registry = markdown_table_row(REGISTRY_PATH, source_id)
            state = decision_file_state(evidence_dir, source_id)
            status_counts[state["status"]] += 1
            rows.append(
                "| "
                + " | ".join(
                    [
                        markdown_cell(source_id),
                        markdown_cell(registry["Source"]),
                        markdown_cell(registry["Primary section"]),
                        markdown_cell(registry["Trust tier"]),
                        markdown_cell(item["decision_needed"]),
                        markdown_cell(item["default_connector_mode"]),
                        markdown_cell(state["status"]),
                        markdown_cell(decision_path(evidence_dir, source_id).relative_to(ROOT)),
                        markdown_cell(packet_path(evidence_dir, source_id).relative_to(ROOT)),
                        markdown_cell(item["next_action"]),
                    ]
                )
                + " |"
            )

        summary_rows.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(batch["title"]),
                    markdown_cell(len(source_ids)),
                    markdown_cell(status_counts["valid"]),
                    markdown_cell(status_counts["invalid"]),
                    markdown_cell(status_counts["missing"]),
                    markdown_cell(", ".join(batch["decision_needed"])),
                    markdown_cell(batch["goal"]),
                ]
            )
            + " |"
        )
        batch_sections.extend(
            [
                f"## {batch['title']}",
                "",
                f"- Goal: {batch['goal']}",
                f"- Default if unresolved: {batch['default_if_unresolved']}",
                "",
                "| Source ID | Source | Primary section | Trust tier | Decision needed | Connector mode | Draft status | Decision file | Packet | Next action |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                *rows,
                "",
            ]
        )

    unassigned = sorted(set(open_source_ids()) - assigned_source_ids)
    if unassigned:
        batch_sections.extend(
            [
                "## Unassigned Review Items",
                "",
                markdown_bullets(unassigned),
                "",
            ]
        )

    return "\n".join(
        [
            "# Source Owner Review Batch Plan",
            "",
            "This plan is context only. Complete the JSON decision files; do not edit this plan as the source of truth.",
            "",
            "## Batch Summary",
            "",
            "| Batch | Open items | Valid drafts | Invalid drafts | Missing drafts | Decision types | Goal |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            *summary_rows,
            "",
            "## Recommended Review Loop",
            "",
            "```bash",
            "python3 scripts/source_owner_review_decision.py --status",
            "python3 scripts/source_owner_review_decision.py --draft-all",
            "python3 scripts/source_owner_review_decision.py --packet-all",
            "python3 scripts/source_owner_review_decision.py --packet-index",
            "python3 scripts/source_owner_review_decision.py --worksheet",
            "python3 scripts/source_owner_review_decision.py --batch-plan",
            "python3 scripts/source_owner_review_decision.py --validate-all",
            "python3 scripts/source_owner_review_decision.py --apply-all --dry-run",
            "```",
            "",
            *batch_sections,
        ]
    )


def write_batch_plan(evidence_dir: Path) -> int:
    output = batch_plan_path(evidence_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(review_batch_plan(evidence_dir) + "\n", encoding="utf-8")
    print(f"Source owner review batch plan written to {output.relative_to(ROOT)}")
    return 0


def refresh_context(path: Path) -> str:
    payload = read_json(path)
    source_id = payload.get("source_id")
    items = load_queue_items()
    policies = load_policy_rows()
    require(source_id in items, f"decision source is not in owner review queue: {source_id}")
    item = items[source_id]
    require(item.get("review_status") == "open", f"source owner review is not open: {source_id}")
    payload["current_artifact_context"] = current_artifact_context(source_id, item, policies.get(source_id, {}))
    write_json(path, payload)
    return source_id


def refresh_all_context(evidence_dir: Path) -> int:
    refreshed = 0
    missing = 0
    invalid = 0
    for source_id in open_source_ids():
        path = decision_path(evidence_dir, source_id)
        if not path.exists():
            missing += 1
            print(f"MISSING source owner decision: {source_id} -> {path.relative_to(ROOT)}")
            continue
        try:
            refreshed_source_id = refresh_context(path)
        except (ReviewError, json.JSONDecodeError) as error:
            invalid += 1
            print(f"INVALID source owner decision: {source_id} -> {error}")
            continue
        refreshed += 1
        print(f"REFRESHED source owner decision context: {refreshed_source_id}")
    print(f"Source owner decision contexts refreshed: {refreshed} refreshed, {invalid} invalid, {missing} missing")
    return 0 if invalid == 0 and missing == 0 else 1


def decision_path(evidence_dir: Path, source_id: str) -> Path:
    return evidence_dir / f"{source_id}.decision.json"


def contains_template_marker(payload: dict) -> bool:
    return "TEMPLATE_" in json.dumps(payload, ensure_ascii=False)


def require_markdown_cell(value: str, label: str) -> None:
    require(bool(value), f"{label} is required")
    require("\n" not in value, f"{label} must be a single line")
    require("|" not in value, f"{label} must not contain markdown table pipes")


def validated_payload(path: Path) -> dict:
    items = load_queue_items()
    payload = read_json(path)
    source_id = payload.get("source_id")
    require(source_id in items, f"decision source is not in owner review queue: {source_id}")
    item = items[source_id]
    require(item.get("review_status") == "open", f"source owner review is not open: {source_id}")
    require(not contains_template_marker(payload), "decision file still contains TEMPLATE_ placeholders")

    reviewed_at = payload.get("reviewed_at", "")
    require(bool(re.match(r"^\d{4}-\d{2}-\d{2}$", reviewed_at)), "reviewed_at must be YYYY-MM-DD")
    require(payload.get("reviewed_by"), "reviewed_by is required")

    decision = payload.get("decision")
    require(decision in VALID_DECISIONS, "decision must be one of: " + ", ".join(sorted(VALID_DECISIONS)))

    evidence = payload.get("evidence_checked", [])
    require(isinstance(evidence, list), "evidence_checked must be a list")
    require(len(evidence) >= len(item.get("evidence_required", [])), "all required evidence items must be addressed")
    for entry in evidence:
        require(entry.get("required_evidence"), "each evidence item needs required_evidence")
        require(entry.get("url_or_note"), "each evidence item needs url_or_note")
        require(bool(re.match(r"^\d{4}-\d{2}-\d{2}$", entry.get("checked_at", ""))), "each evidence item needs checked_at YYYY-MM-DD")

    answers = payload.get("owner_question_answers", [])
    questions = item.get("owner_questions", [])
    require(isinstance(answers, list), "owner_question_answers must be a list")
    require([entry.get("question") for entry in answers] == questions, "owner questions must match queue order")
    for entry in answers:
        require(entry.get("answer"), "each owner question needs an answer")

    policy = payload.get("policy_after_decision", {})
    require(policy.get("eligibility_state") == decision, "policy_after_decision.eligibility_state must match decision")
    require(policy.get("full_text_storage") == "not_stored", "full_text_storage must remain not_stored")
    for field in ["connector_mode", "summary_policy", "media_policy", "rate_policy"]:
        require(policy.get(field), f"policy_after_decision.{field} is required")

    production_auto_ingestion = policy.get("production_auto_ingestion")
    require(isinstance(production_auto_ingestion, bool), "production_auto_ingestion must be boolean")
    if decision == "eligible":
        require(production_auto_ingestion is True, "eligible decisions must explicitly enable production_auto_ingestion")
        require(
            policy.get("summary_policy") == "generated_summary_from_metadata_only",
            "eligible decisions must keep summaries metadata-only",
        )
    else:
        require(production_auto_ingestion is False, f"{decision} decisions must keep production_auto_ingestion disabled")

    require(payload.get("implementation_guardrail"), "implementation_guardrail is required")
    updates = payload.get("artifact_updates", {})
    review_matrix = updates.get("review_matrix", {})
    registry = updates.get("source_registry", {})
    for field in ["terms_evidence", "summary_storage", "media_use", "rate_limit", "next_action"]:
        require_markdown_cell(review_matrix.get(field, ""), f"artifact_updates.review_matrix.{field}")
    require_markdown_cell(registry.get("eligibility_notes", ""), "artifact_updates.source_registry.eligibility_notes")
    return payload


def validate_decision(path: Path) -> int:
    payload = validated_payload(path)
    print(f"VALID source owner decision: {payload['source_id']} -> {payload['decision']}")
    return 0


def checked_decision_payloads(evidence_dir: Path) -> tuple[list[dict], int, int]:
    payloads: list[dict] = []
    invalid = 0
    missing = 0
    for source_id in open_source_ids():
        path = decision_path(evidence_dir, source_id)
        if not path.exists():
            missing += 1
            print(f"MISSING source owner decision: {source_id} -> {path.relative_to(ROOT)}")
            continue
        try:
            payload = validated_payload(path)
        except (ReviewError, json.JSONDecodeError) as error:
            invalid += 1
            print(f"INVALID source owner decision: {source_id} -> {error}")
            continue
        payloads.append(payload)
        print(f"VALID source owner decision: {payload['source_id']} -> {payload['decision']}")

    total = len(payloads) + invalid + missing
    print(f"Source owner decisions checked: {len(payloads)} valid, {invalid} invalid, {missing} missing, {total} open items")
    return payloads, invalid, missing


def validate_all_decisions(evidence_dir: Path) -> int:
    _, invalid, missing = checked_decision_payloads(evidence_dir)
    return 0 if invalid == 0 and missing == 0 else 1


def decision_status(evidence_dir: Path) -> int:
    valid = 0
    invalid = 0
    missing = 0
    for source_id in open_source_ids():
        state = decision_file_state(evidence_dir, source_id)
        if state["status"] == "missing":
            missing += 1
            print(f"{source_id}\tmissing\t\t{state['detail']}")
            continue
        if state["status"] == "invalid":
            invalid += 1
            print(f"{source_id}\tinvalid\t{state['decision']}\t{state['detail']}")
            continue
        valid += 1
        print(f"{source_id}\tvalid\t{state['decision']}\t{state['detail']}")

    total = valid + invalid + missing
    print(f"Source owner decision status: {valid} valid, {invalid} invalid, {missing} missing, {total} open items")
    return 0


def update_markdown_table_row(path: Path, source_id: str, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    header: list[str] | None = None
    for index, line in enumerate(lines):
        if line.startswith("| ID |"):
            header = split_markdown_row(line)
            continue
        if not header or not line.startswith(f"| {source_id} |"):
            continue
        columns = split_markdown_row(line)
        require(len(columns) == len(header), f"{path.relative_to(ROOT)} row has wrong column count: {source_id}")
        row = dict(zip(header, columns))
        for column, value in updates.items():
            require(column in row, f"{path.relative_to(ROOT)} missing column: {column}")
            row[column] = value
        lines[index] = build_markdown_row([row[column] for column in header])
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    raise ReviewError(f"{path.relative_to(ROOT)} missing row: {source_id}")


def update_access_policy(payload: dict) -> None:
    policy = read_json(POLICY_PATH)
    source_id = payload["source_id"]
    policy_after = payload["policy_after_decision"]
    for source in policy["sources"]:
        if source["source_id"] != source_id:
            continue
        source.update(policy_after)
        source["requires_owner_review"] = payload["decision"] == "needs_review"
        if source_id == "src-manual-url":
            source["requires_per_item_review"] = True
        write_json(POLICY_PATH, policy)
        return
    raise ReviewError(f"source access policy missing row: {source_id}")


def update_owner_queue(payload: dict) -> None:
    if payload["decision"] == "needs_review":
        return
    queue = read_json(QUEUE_PATH)
    before = len(queue["items"])
    queue["items"] = [item for item in queue["items"] if item["source_id"] != payload["source_id"]]
    require(len(queue["items"]) == before - 1, f"source owner review queue missing item: {payload['source_id']}")
    write_json(QUEUE_PATH, queue)


def apply_payload(payload: dict, dry_run: bool) -> None:
    source_id = payload["source_id"]
    decision = payload["decision"]
    if dry_run:
        print(f"DRY-RUN would apply source owner decision: {source_id} -> {decision}")
        return

    updates = payload["artifact_updates"]
    update_markdown_table_row(
        REVIEW_PATH,
        source_id,
        {
            "Eligibility state": decision,
            "Terms evidence": updates["review_matrix"]["terms_evidence"],
            "Full text storage": "not stored by default",
            "Summary/storage": updates["review_matrix"]["summary_storage"],
            "Media use": updates["review_matrix"]["media_use"],
            "Rate limit": updates["review_matrix"]["rate_limit"],
            "Next action": updates["review_matrix"]["next_action"],
        },
    )
    update_markdown_table_row(
        REGISTRY_PATH,
        source_id,
        {
            "Eligibility notes": updates["source_registry"]["eligibility_notes"],
        },
    )
    update_access_policy(payload)
    update_owner_queue(payload)
    print(f"APPLIED source owner decision: {source_id} -> {decision}")


def apply_decision(path: Path, dry_run: bool) -> int:
    apply_payload(validated_payload(path), dry_run)
    return 0


def apply_all_decisions(evidence_dir: Path, dry_run: bool) -> int:
    payloads, invalid, missing = checked_decision_payloads(evidence_dir)
    if invalid or missing:
        print("ERROR not applying source owner decisions until every open decision is valid")
        return 1
    if dry_run:
        for payload in payloads:
            apply_payload(payload, dry_run=True)
        print(f"DRY-RUN would apply {len(payloads)} source owner decisions")
        return 0

    artifact_paths = [REVIEW_PATH, REGISTRY_PATH, POLICY_PATH, QUEUE_PATH]
    snapshots = {path: path.read_text(encoding="utf-8") for path in artifact_paths}
    try:
        for payload in payloads:
            apply_payload(payload, dry_run=False)
    except Exception as error:
        for path, text in snapshots.items():
            path.write_text(text, encoding="utf-8")
        print(f"ERROR rolled back batch source owner decisions: {error}")
        return 1

    print(f"APPLIED {len(payloads)} source owner decisions")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list-open", action="store_true", help="List open owner review queue items.")
    group.add_argument("--status", action="store_true", help="Report status for every open owner review decision file.")
    group.add_argument("--draft", metavar="SOURCE_ID", help="Write a fillable decision draft under evidence/.")
    group.add_argument("--draft-all", action="store_true", help="Write missing decision drafts for all open owner reviews.")
    group.add_argument("--packet", metavar="SOURCE_ID", help="Write a derived Markdown review packet under evidence/.")
    group.add_argument("--packet-all", action="store_true", help="Write derived Markdown review packets for all open owner reviews.")
    group.add_argument("--packet-index", action="store_true", help="Write a derived Markdown review index under evidence/.")
    group.add_argument("--worksheet", action="store_true", help="Write a consolidated owner review worksheet under evidence/.")
    group.add_argument("--batch-plan", action="store_true", help="Write a prioritized owner review batch plan under evidence/.")
    group.add_argument("--refresh-context-all", action="store_true", help="Refresh current artifact context in existing owner review drafts.")
    group.add_argument("--validate", metavar="PATH", help="Validate a completed source owner decision file.")
    group.add_argument("--validate-all", action="store_true", help="Validate every open owner review decision file.")
    group.add_argument("--apply", metavar="PATH", help="Validate and apply a completed source owner decision to tracked artifacts.")
    group.add_argument("--apply-all", action="store_true", help="Validate and apply every open owner review decision file.")
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    parser.add_argument("--dry-run", action="store_true", help="With --apply or --apply-all, validate and print the planned action without writing.")
    args = parser.parse_args()

    try:
        if args.list_open:
            return list_open()
        if args.status:
            return decision_status(Path(args.evidence_dir))
        if args.draft:
            return write_draft(args.draft, Path(args.evidence_dir))
        if args.draft_all:
            return write_all_drafts(Path(args.evidence_dir))
        if args.packet:
            return write_packet(args.packet, Path(args.evidence_dir))
        if args.packet_all:
            return write_all_packets(Path(args.evidence_dir))
        if args.packet_index:
            return write_packet_index(Path(args.evidence_dir))
        if args.worksheet:
            return write_worksheet(Path(args.evidence_dir))
        if args.batch_plan:
            return write_batch_plan(Path(args.evidence_dir))
        if args.refresh_context_all:
            return refresh_all_context(Path(args.evidence_dir))
        if args.validate:
            return validate_decision(Path(args.validate))
        if args.validate_all:
            return validate_all_decisions(Path(args.evidence_dir))
        if args.apply_all:
            return apply_all_decisions(Path(args.evidence_dir), args.dry_run)
        return apply_decision(Path(args.apply), args.dry_run)
    except ReviewError as error:
        print(f"ERROR {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
