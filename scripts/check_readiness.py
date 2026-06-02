#!/usr/bin/env python3
"""Validate the local pre-development readiness evidence.

This script checks repo-local artifacts only. It does not prove live Feishu,
model-provider, or NAS/cloud sync success. Use --require-live to fail when the
required external environment variables are not present.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]


class CheckFailure(Exception):
    pass


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def load_json(path: str):
    return json.loads(read(path))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailure(message)


def require_files(paths: Iterable[str]) -> None:
    for path in paths:
        require((ROOT / path).exists(), f"missing required file: {path}")


def check_required_files() -> list[str]:
    files = [
        "AGENTS.md",
        "CONTEXT.md",
        "docs/PRE-DEVELOPMENT-PLAN.md",
        "docs/PRD.md",
        "docs/MVP-SCOPE.md",
        "docs/ARCHITECTURE-NOTES.md",
        "docs/readiness-gate-status.md",
        "docs/schemas/minimal-contracts.md",
        "docs/spikes/feishu-delivery.md",
        "docs/spikes/source-ingestion.md",
        "docs/spikes/model-provider.md",
        "docs/spikes/archive-storage.md",
        "docs/source-registry.md",
        "docs/source-eligibility-reviews.md",
        "docs/source-eligibility-checklist.md",
        "docs/taxonomy/technology-domain-template.md",
        "docs/briefing-style-guide.md",
        "docs/secrets.md",
        ".env.example",
        ".gitignore",
    ]
    require_files(files)
    return [f"required files present: {len(files)}"]


def check_source_registry() -> list[str]:
    text = read("docs/source-registry.md")
    rows = [line for line in text.splitlines() if line.startswith("| src-")]
    first_version = [line for line in rows if "| first-version |" in line]
    deferred = [line for line in rows if "| deferred |" in line]
    require(len(rows) >= 30, f"expected at least 30 seed sources, found {len(rows)}")
    require(first_version, "expected first-version sources")
    require(deferred, "expected deferred sources")
    return [
        f"source registry: {len(rows)} seed sources",
        f"source registry: {len(first_version)} first-version, {len(deferred)} deferred",
    ]


def check_source_registry_review_notes() -> list[str]:
    rows = parse_source_eligibility_reviews()
    needs_terms_review = [row["ID"] for row in rows if row["Eligibility state"] == "needs_review"]
    blocked = [row["ID"] for row in rows if row["Eligibility state"] == "blocked"]
    deferred = [row["ID"] for row in rows if row["Eligibility state"] == "deferred"]
    notes = []
    if needs_terms_review:
        notes.append(
            "source eligibility: "
            f"{len(needs_terms_review)} first-version source reviews remain needs_review "
            "(terms, media reuse, rate limits, or disallowed behavior need owner confirmation)"
        )
    if blocked:
        notes.append(f"source eligibility: blocked source reviews present: {', '.join(blocked)}")
    if deferred:
        notes.append(f"source eligibility: deferred source reviews present: {', '.join(deferred)}")
    return notes


def parse_markdown_table(path: str) -> list[dict[str, str]]:
    lines = read(path).splitlines()
    header = None
    rows: list[dict[str, str]] = []
    for line in lines:
        if not line.startswith("|"):
            continue
        cols = [part.strip() for part in line.strip().strip("|").split("|")]
        if cols and cols[0] == "ID":
            header = cols
            continue
        if not header or not cols or cols[0].startswith("---"):
            continue
        if cols[0].startswith("src-"):
            require(len(cols) == len(header), f"{path}: row {cols[0]} has wrong column count")
            rows.append(dict(zip(header, cols)))
    return rows


def parse_source_eligibility_reviews() -> list[dict[str, str]]:
    return parse_markdown_table("docs/source-eligibility-reviews.md")


def check_source_eligibility_reviews() -> list[str]:
    registry_text = read("docs/source-registry.md")
    registry_rows = [
        line for line in registry_text.splitlines() if line.startswith("| src-") and "| first-version |" in line
    ]
    first_version_ids = []
    for row in registry_rows:
        columns = [part.strip() for part in row.strip().strip("|").split("|")]
        first_version_ids.append(columns[0])

    review_rows = parse_source_eligibility_reviews()
    review_by_id = {row["ID"]: row for row in review_rows}
    missing = sorted(set(first_version_ids) - set(review_by_id))
    extra = sorted(set(review_by_id) - set(first_version_ids))
    require(not missing, f"source eligibility reviews missing first-version sources: {', '.join(missing)}")
    require(not extra, f"source eligibility reviews include non-first-version sources: {', '.join(extra)}")

    allowed_states = {"eligible", "needs_review", "deferred", "blocked"}
    required_columns = [
        "Access method",
        "Terms evidence",
        "Full text storage",
        "Summary/storage",
        "Media use",
        "Rate limit",
        "Attribution",
        "Disallowed behavior",
        "Next action",
    ]
    state_counts = {state: 0 for state in allowed_states}
    for source_id in first_version_ids:
        row = review_by_id[source_id]
        state = row["Eligibility state"]
        require(state in allowed_states, f"{source_id}: invalid eligibility state {state}")
        state_counts[state] += 1
        for column in required_columns:
            require(row[column] and row[column] != "-", f"{source_id}: missing {column}")
        require("not stored" in row["Full text storage"], f"{source_id}: full text storage must be not stored")
        require("source name" in row["Attribution"], f"{source_id}: attribution must preserve source name")

    return [
        f"source eligibility reviews: {len(review_rows)} first-version sources covered",
        "source eligibility reviews: "
        + ", ".join(f"{state}={count}" for state, count in sorted(state_counts.items()) if count),
    ]


def _legacy_source_registry_review_notes() -> list[str]:
    text = read("docs/source-registry.md")
    rows = [line for line in text.splitlines() if line.startswith("| src-") and "| first-version |" in line]
    needs_terms_review = []
    for row in rows:
        columns = [part.strip() for part in row.strip().strip("|").split("|")]
        source_id = columns[0]
        notes = columns[-1].lower()
        if "validate" in notes or "terms" in notes or "fallback" in notes:
            needs_terms_review.append(source_id)
    if not needs_terms_review:
        return []
    return [
        "source registry: "
        f"{len(needs_terms_review)} first-version seed sources still need full eligibility checklist review "
        "(terms, media reuse, rate limits, and disallowed behavior) before automated ingestion"
    ]


def check_golden_samples() -> list[str]:
    items = load_json("fixtures/golden-samples/items.json")
    require(isinstance(items, list), "golden samples must be a JSON list")
    ids = [item["fixture_id"] for item in items]
    require(len(ids) == len(set(ids)), "golden sample fixture_id values must be unique")
    synthetic = [item for item in items if "synthetic_behavior_exercise" in item.get("scenario_tags", [])]
    real_world = [item for item in items if item not in synthetic]
    require(len(real_world) >= 20, f"expected at least 20 real-world samples, found {len(real_world)}")
    require(len(synthetic) == 1, f"expected exactly one synthetic behavior exercise, found {len(synthetic)}")
    required_tags = {
        "duplicate_coverage",
        "low_confidence",
        "academic_source",
        "no_media",
        "source_media",
    }
    tags = {tag for item in items for tag in item.get("scenario_tags", [])}
    missing = sorted(required_tags - tags)
    require(not missing, f"golden samples missing scenario tags: {', '.join(missing)}")
    forbidden_keys = {"article_body", "full_text", "body_text", "complete_article_text"}
    for item in items:
        present = forbidden_keys & set(item.keys())
        require(not present, f"{item['fixture_id']} contains forbidden full-text keys: {sorted(present)}")
    return [
        f"golden samples: {len(items)} total",
        f"golden samples: {len(real_world)} real-world, {len(synthetic)} synthetic",
    ]


def check_json_fixtures() -> list[str]:
    paths = [
        "fixtures/source-ingestion/candidate-items.json",
        "fixtures/archive-storage/local-archive/2026-06-01/technology/metadata.json",
        "fixtures/feishu-delivery/push-briefing-card-content.json",
        "fixtures/feishu-delivery/internal-app-send-message.request-shape.json",
        "fixtures/feishu-delivery/delivery-status-examples.json",
        "fixtures/model-provider/outputs/high-confidence-news.json",
        "fixtures/model-provider/outputs/low-confidence-news.json",
        "fixtures/model-provider/outputs/academic-paper.json",
        "fixtures/model-provider/usage-log.json",
    ]
    for path in paths:
        load_json(path)
    return [f"json fixtures parse: {len(paths)}"]


def check_archive_fixture() -> list[str]:
    base = ROOT / "fixtures/archive-storage/local-archive/2026-06-01/technology"
    require_files(
        [
            "fixtures/archive-storage/local-archive/2026-06-01/technology/briefing.html",
            "fixtures/archive-storage/local-archive/2026-06-01/technology/briefing.md",
            "fixtures/archive-storage/local-archive/2026-06-01/technology/metadata.json",
            "fixtures/archive-storage/local-archive/2026-06-01/technology/media/README.md",
        ]
    )
    metadata = json.loads((base / "metadata.json").read_text(encoding="utf-8"))
    required = {
        "run_id",
        "domain_template",
        "generated_at",
        "files",
        "selected_items",
        "excluded_candidates",
        "connector_status",
        "delivery_status",
        "media_inventory",
        "sync_status",
        "model_usage_summary",
    }
    missing = sorted(required - set(metadata))
    require(not missing, f"archive metadata missing fields: {', '.join(missing)}")
    require(metadata["sync_status"]["local_archive"]["status"] == "written", "local archive status must be written")
    require(metadata["sync_status"]["remote_sync"]["status"] == "failed", "fixture remote sync must record failure")
    require(metadata["sync_status"]["remote_sync"]["retryable"] is True, "fixture sync failure must be retryable")
    return ["archive fixture: local write and retryable sync failure represented"]


def check_model_fixtures() -> list[str]:
    outputs = [
        "fixtures/model-provider/outputs/high-confidence-news.json",
        "fixtures/model-provider/outputs/low-confidence-news.json",
        "fixtures/model-provider/outputs/academic-paper.json",
    ]
    required_fields = {
        "id",
        "run_id",
        "candidate_id",
        "section",
        "title_zh",
        "bullets_zh",
        "original_source_anchor",
        "selection_rationale",
        "confidence_level",
    }
    for path in outputs:
        payload = load_json(path)
        item = payload["briefing_item"]
        missing = sorted(required_fields - set(item))
        require(not missing, f"{path} missing briefing fields: {', '.join(missing)}")
        require(3 <= len(item["bullets_zh"]) <= 4, f"{path} must contain 3-4 bullets")
        if item["confidence_level"] in {"medium", "low"}:
            require(item.get("confidence_notice"), f"{path} missing required confidence_notice")
        usage = payload["model_usage"]
        for field in ["provider", "model", "task_type", "request_count", "failure_reason"]:
            require(field in usage, f"{path} missing model_usage.{field}")
    usage_log = load_json("fixtures/model-provider/usage-log.json")
    require(len(usage_log["tasks"]) == 3, "usage log must include three model tasks")
    return ["model fixtures: three structured outputs and usage log valid"]


def check_feishu_fixture() -> list[str]:
    card = load_json("fixtures/feishu-delivery/push-briefing-card-content.json")
    request = load_json("fixtures/feishu-delivery/internal-app-send-message.request-shape.json")
    rendered = read("fixtures/feishu-delivery/rendered-message.md")
    card_text = json.dumps(card, ensure_ascii=False)
    for needle in ["AI / Multimodal AI", "Hardware / AI accelerators", "置信提示", "Source"]:
        require(needle in rendered or needle in card_text, f"Feishu fixture missing {needle}")
    require(request["user_delivery"]["query"]["receive_id_type"] == "open_id", "user delivery must use open_id")
    require(request["group_delivery"]["query"]["receive_id_type"] == "chat_id", "group delivery must use chat_id")
    forbidden = ["FEISHU_APP_SECRET=", "Bearer ey", "ou_", "oc_"]
    request_text = json.dumps(request)
    leaked = [value for value in forbidden if value in request_text]
    require(not leaked, f"possible Feishu secret or recipient id leaked: {', '.join(leaked)}")
    return ["Feishu fixture: user/group request shapes and message content valid"]


def check_adrs() -> list[str]:
    required = [
        "docs/adr/0002-feishu-internal-app-bot-first.md",
        "docs/adr/0003-python-single-service-stack.md",
        "docs/adr/0004-docker-compose-briefing-host.md",
        "docs/adr/0005-sqlite-operational-store.md",
        "docs/adr/0006-local-first-archive-sync.md",
        "docs/adr/0007-model-provider-boundary.md",
        "docs/adr/0008-single-admin-console-access.md",
    ]
    require_files(required)
    for path in required:
        text = read(path)
        require("Status:" in text, f"{path} missing Status")
        require("**Consequences**" in text, f"{path} missing Consequences")
    return [f"required ADRs present: {len(required)}"]


def check_mvp_issue_drafts() -> list[str]:
    files = sorted((ROOT / "docs/issues/mvp").glob("*.md"))
    require(len(files) == 11, f"expected 11 MVP issue drafts, found {len(files)}")
    required = [
        "## Problem",
        "## Scope",
        "## Out of scope",
        "## Acceptance criteria",
        "## Test expectations",
        "## Relevant docs",
        "## Dependencies",
        "## Triage label",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        for heading in required:
            require(heading in text, f"{path.relative_to(ROOT)} missing {heading}")
        require("`needs-triage`" in text, f"{path.relative_to(ROOT)} must stay needs-triage")
    breakdown = read("docs/github-issue-breakdown.md")
    for number in range(10, 21):
        require(f"#{number}" in breakdown, f"issue breakdown missing #{number}")
    return ["MVP issue drafts: 11 complete drafts linked to #10-#20"]


def check_external_environment() -> tuple[list[str], list[str]]:
    groups = {
        "Feishu": [
            "FEISHU_APP_ID",
            "FEISHU_APP_SECRET",
            "FEISHU_DEFAULT_USER_OPEN_ID",
            "FEISHU_DEFAULT_CHAT_ID",
        ],
        "Model Provider": [
            "MODEL_PROVIDER",
            "MODEL_DEFAULT_MODEL",
            "MODEL_API_KEY",
        ],
        "Archive Sync": [
            "ARCHIVE_LOCAL_ROOT",
            "ARCHIVE_SYNC_TARGET",
        ],
    }
    ok: list[str] = []
    missing_messages: list[str] = []
    for group, names in groups.items():
        missing = [name for name in names if not os.environ.get(name)]
        if missing:
            missing_messages.append(f"{group}: missing {', '.join(missing)}")
        else:
            ok.append(f"{group}: required environment variables present")
    return ok, missing_messages


def run(require_live: bool) -> int:
    checks = [
        check_required_files,
        check_json_fixtures,
        check_source_registry,
        check_source_eligibility_reviews,
        check_golden_samples,
        check_archive_fixture,
        check_model_fixtures,
        check_feishu_fixture,
        check_adrs,
        check_mvp_issue_drafts,
    ]
    passed: list[str] = []
    failures: list[str] = []
    review_notes: list[str] = []
    for check in checks:
        try:
            passed.extend(check())
        except CheckFailure as exc:
            failures.append(str(exc))
    review_notes.extend(check_source_registry_review_notes())

    external_ok, external_missing = check_external_environment()
    passed.extend(external_ok)

    for item in passed:
        print(f"PASS {item}")
    for item in failures:
        print(f"FAIL {item}")
    for item in review_notes:
        print(f"REVIEW {item}")
    for item in external_missing:
        print(f"BLOCKED {item}")

    if failures:
        return 1
    if require_live and external_missing:
        return 2
    if external_missing:
        print("SUMMARY local readiness evidence is valid; live external spike evidence is still pending")
    else:
        print("SUMMARY local readiness evidence and required environment variables are present; live spike evidence still needs manual verification")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="Fail when required external environment variables are missing.",
    )
    args = parser.parse_args()
    return run(require_live=args.require_live)


if __name__ == "__main__":
    raise SystemExit(main())
