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


def split_markdown_row(line: str) -> list[str]:
    return [part.strip() for part in line.strip().strip("|").split("|")]


def build_markdown_row(columns: list[str]) -> str:
    return "| " + " | ".join(columns) + " |"


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


def apply_decision(path: Path, dry_run: bool) -> int:
    payload = validated_payload(path)
    source_id = payload["source_id"]
    decision = payload["decision"]
    if dry_run:
        print(f"DRY-RUN would apply source owner decision: {source_id} -> {decision}")
        return 0

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
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list-open", action="store_true", help="List open owner review queue items.")
    group.add_argument("--draft", metavar="SOURCE_ID", help="Write a fillable decision draft under evidence/.")
    group.add_argument("--validate", metavar="PATH", help="Validate a completed source owner decision file.")
    group.add_argument("--apply", metavar="PATH", help="Validate and apply a completed source owner decision to tracked artifacts.")
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    parser.add_argument("--dry-run", action="store_true", help="With --apply, validate and print the planned action without writing.")
    args = parser.parse_args()

    try:
        if args.list_open:
            return list_open()
        if args.draft:
            return write_draft(args.draft, Path(args.evidence_dir))
        if args.validate:
            return validate_decision(Path(args.validate))
        return apply_decision(Path(args.apply), args.dry_run)
    except ReviewError as error:
        print(f"ERROR {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
