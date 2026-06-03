#!/usr/bin/env python3
"""Validate the local pre-development readiness evidence.

This script checks repo-local artifacts only. It does not prove live Feishu,
model-provider, or NAS/cloud sync success. Use --require-live to fail when the
required external environment variables are not present.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = ROOT / "evidence"
TEMPLATE_MARKER = "TEMPLATE_"
SOURCE_REVIEW_PLACEHOLDERS = [
    "terms/feed policy not yet recorded",
    "feed/api availability and terms not yet recorded",
    "validate feed terms",
    "terms not yet recorded",
    "review terms, robots guidance, feed policy",
]
LIVE_EVIDENCE_SECRET_PATTERNS = [
    ("authorization header", re.compile(r"Authorization\s*[:=]\s*Bearer\s+\S+", re.IGNORECASE)),
    ("bearer token", re.compile(r"Bearer\s+(?!REDACTED\b)[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE)),
    ("tenant access token", re.compile(r"tenant_access_token")),
    ("Feishu user open_id", re.compile(r"\bou_[A-Za-z0-9]{8,}\b")),
    ("Feishu chat_id", re.compile(r"\boc_[A-Za-z0-9]{8,}\b")),
    ("Feishu app id", re.compile(r"\bcli_[A-Za-z0-9]{8,}\b")),
    ("local user path", re.compile(r"/Users/[^/\s\"]+")),
    ("private tmp path", re.compile(r"(?<![A-Za-z0-9_./-])/private/")),
    ("iCloud workspace path", re.compile(r"Mobile Documents/com~apple~CloudDocs")),
]
EXPECTED_ENV_EXAMPLE_VARS = [
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "FEISHU_TENANT_KEY",
    "FEISHU_DEFAULT_USER_OPEN_ID",
    "FEISHU_DEFAULT_CHAT_ID",
    "FEISHU_GROUP_WEBHOOK_URL",
    "FEISHU_GROUP_WEBHOOK_SECRET",
    "MODEL_PROVIDER",
    "MODEL_API_KEY",
    "MODEL_DEFAULT_MODEL",
    "ARCHIVE_LOCAL_ROOT",
    "ARCHIVE_SYNC_TARGET",
    "ADMIN_USERNAME",
    "ADMIN_PASSWORD_HASH",
    "SESSION_SECRET",
]
SENSITIVE_ENV_NAMES = [
    "FEISHU_APP_ID",
    "FEISHU_APP_SECRET",
    "FEISHU_TENANT_KEY",
    "FEISHU_DEFAULT_USER_OPEN_ID",
    "FEISHU_DEFAULT_CHAT_ID",
    "FEISHU_GROUP_WEBHOOK_URL",
    "FEISHU_GROUP_WEBHOOK_SECRET",
    "MODEL_API_KEY",
    "ARCHIVE_LOCAL_ROOT",
    "ARCHIVE_SYNC_TARGET",
    "ADMIN_PASSWORD_HASH",
    "SESSION_SECRET",
]
LIVE_EVIDENCE_TEMPLATE_FILES = [
    "fixtures/live-evidence-templates/readiness-manifest.json",
    "fixtures/live-evidence-templates/feishu-delivery/user-response.redacted.json",
    "fixtures/live-evidence-templates/feishu-delivery/group-response.redacted.json",
    "fixtures/live-evidence-templates/feishu-delivery/rendered-message.md",
    "fixtures/live-evidence-templates/model-provider/outputs/high-confidence-news.json",
    "fixtures/live-evidence-templates/model-provider/outputs/low-confidence-news.json",
    "fixtures/live-evidence-templates/model-provider/outputs/academic-paper.json",
    "fixtures/live-evidence-templates/model-provider/usage-log.json",
    "fixtures/live-evidence-templates/archive-storage/sync-result.json",
    "fixtures/live-evidence-templates/archive-storage/local-tree.txt",
    "fixtures/live-evidence-templates/archive-storage/remote-tree.txt",
]
EXPECTED_GITHUB_REPO = "KG9750/TechNews"
ALLOWED_ORIGIN_URLS = {
    "https://github.com/KG9750/TechNews.git",
    "git@github.com:KG9750/TechNews.git",
    "ssh://git@github.com/KG9750/TechNews.git",
}
GITHUB_WRITE_PERMISSIONS = {"ADMIN", "MAINTAIN", "WRITE"}
REQUIRED_GITHUB_LABELS = {
    "needs-triage",
    "needs-info",
    "ready-for-agent",
    "ready-for-human",
    "wontfix",
}
REQUIRED_GITHUB_MILESTONES = {
    "pre-development",
    "mvp",
    "post-mvp",
}
PREDEVELOPMENT_ISSUES = set(range(1, 10))
MVP_ISSUES = set(range(10, 21))
MVP_ISSUE_DRAFTS = {
    10: "docs/issues/mvp/01-repo-ci-foundation.md",
    11: "docs/issues/mvp/02-contract-schemas.md",
    12: "docs/issues/mvp/03-taxonomy-source-registry.md",
    13: "docs/issues/mvp/04-source-connectors.md",
    14: "docs/issues/mvp/05-ranking-selection-rationale.md",
    15: "docs/issues/mvp/06-briefing-generation-confidence.md",
    16: "docs/issues/mvp/07-archive-package.md",
    17: "docs/issues/mvp/08-feishu-delivery.md",
    18: "docs/issues/mvp/09-operations-console.md",
    19: "docs/issues/mvp/10-deployment-secrets.md",
    20: "docs/issues/mvp/11-e2e-mvp-acceptance.md",
}
MVP_ISSUE_REQUIRED_SECTIONS = [
    "Problem",
    "Scope",
    "Out of scope",
    "Acceptance criteria",
    "Test expectations",
    "Relevant docs",
    "Dependencies",
    "Triage label",
]
MVP_COVERAGE_KEYWORDS = [
    "First-Version Source type",
    "Automatic Briefing Run",
    "Delivery Deadline",
    "Feishu user",
    "Feishu group",
    "Archived Briefing",
    "Deep-Dive Detail",
    "Confidence Notice",
    "Source Media",
    "without source media",
    "Related History",
    "run status",
    "delivery status",
]
CONTRACT_REQUIRED_FIELDS = {
    "CandidateItem": {
        "id",
        "run_id",
        "source_id",
        "source_type",
        "source_name",
        "original_title",
        "source_url",
        "original_source_anchor",
        "dedupe_key",
        "discovered_at",
        "section_hints",
        "source_media",
        "eligibility_state",
        "raw_metadata",
    },
    "BriefingItem": {
        "id",
        "run_id",
        "candidate_id",
        "section",
        "subcategory",
        "title_zh",
        "bullets_zh",
        "original_source_anchor",
        "selection_rationale",
        "confidence_level",
        "confidence_notice",
        "media_attribution",
        "related_history",
    },
    "ArchiveMetadata": {
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
    },
    "BriefingRun": {
        "run_id",
        "domain_template",
        "scheduled_for",
        "delivery_deadline",
        "started_at",
        "connector_status",
        "model_task_status",
        "archive_status",
        "feishu_delivery_status",
        "run_warnings",
    },
}
CONTRACT_NESTED_SHAPES = {
    "OriginalSourceAnchor",
    "SourceMedia",
    "SelectionRationale",
    "ConfidenceNotice",
    "ModelUsage",
}
EXPECTED_TECHNOLOGY_SECTIONS = {
    "AI",
    "Software",
    "Hardware",
    "Embodied Intelligence",
    "Academic Progress",
    "Technology Industry Progress",
}
REQUIRED_EMBODIED_SUBCATEGORIES = {
    "Robot body",
    "Data collection",
    "Model training",
    "Recent papers",
    "Financing",
}
STYLE_GUIDE_REQUIRED_HEADINGS = [
    "Push Briefing Structure",
    "Title Rules",
    "Bullet Rules",
    "Confidence Notice Rules",
    "Source And Media Attribution",
    "Deep-Dive Detail",
    "Quality Checklist",
]
REQUIRED_ADRS = {
    "docs/adr/0002-feishu-internal-app-bot-first.md": {
        "keywords": ["internal app bot", "custom group bot", "personal delivery", "group delivery"],
        "architecture_default": "Feishu delivery:",
    },
    "docs/adr/0003-python-single-service-stack.md": {
        "keywords": ["Python 3.12", "FastAPI", "single service"],
        "architecture_default": "Application stack:",
    },
    "docs/adr/0004-docker-compose-briefing-host.md": {
        "keywords": ["Docker Compose", "Briefing Host", "mounted archive"],
        "architecture_default": "Deployment target:",
    },
    "docs/adr/0005-sqlite-operational-store.md": {
        "keywords": ["SQLite", "Archive Packages remain file-based", "Secrets must not be stored"],
        "architecture_default": "Operational data:",
    },
    "docs/adr/0006-local-first-archive-sync.md": {
        "keywords": ["local-first", "ARCHIVE_LOCAL_ROOT", "sync failure"],
        "architecture_default": "Archive strategy:",
    },
    "docs/adr/0007-model-provider-boundary.md": {
        "keywords": ["generation boundary", "provider adapter", "usage metadata"],
        "architecture_default": "Model boundary:",
    },
    "docs/adr/0008-single-admin-console-access.md": {
        "keywords": ["ADMIN_USERNAME", "ADMIN_PASSWORD_HASH", "SESSION_SECRET"],
        "architecture_default": "Console access:",
    },
}


class CheckFailure(Exception):
    pass


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def load_json(path: str):
    return json.loads(read(path))


def load_json_path(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def run_command(args: list[str], failure_message: str) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            args,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise CheckFailure(failure_message) from exc
    if result.returncode != 0:
        raise CheckFailure(failure_message)
    return result


def run_gh_json(args: list[str]):
    try:
        result = subprocess.run(
            ["gh", *args],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise CheckFailure("gh CLI is required for --require-github") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise CheckFailure(f"gh {' '.join(args)} failed: {detail}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CheckFailure(f"gh {' '.join(args)} did not return JSON") from exc


def read_path(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
        ".github/workflows/pre-development-readiness.yml",
        "docs/PRE-DEVELOPMENT-PLAN.md",
        "docs/PRD.md",
        "docs/MVP-SCOPE.md",
        "docs/ARCHITECTURE-NOTES.md",
        "docs/readiness-gate-status.md",
        "docs/live-spike-evidence-runbook.md",
        "docs/schemas/minimal-contracts.md",
        "docs/spikes/feishu-delivery.md",
        "docs/spikes/source-ingestion.md",
        "docs/spikes/model-provider.md",
        "docs/spikes/archive-storage.md",
        "docs/source-registry.md",
        "docs/source-eligibility-reviews.md",
        "docs/source-eligibility-checklist.md",
        "docs/source-owner-review-runbook.md",
        "fixtures/source-ingestion/source-access-policy.json",
        "fixtures/source-ingestion/source-owner-review-queue.json",
        "docs/taxonomy/technology-domain-template.md",
        "docs/briefing-style-guide.md",
        "docs/secrets.md",
        ".env.example",
        ".gitignore",
        "scripts/spikes/feishu_delivery_spike.py",
        "scripts/spikes/archive_storage_spike.py",
        "scripts/spikes/model_provider_spike.py",
        "scripts/spikes/readiness_manifest.py",
        "scripts/spikes/live_readiness_preflight.py",
    ]
    require_files(files)
    return [f"required files present: {len(files)}"]


def check_live_evidence_templates() -> list[str]:
    require_files(LIVE_EVIDENCE_TEMPLATE_FILES)
    json_paths = [path for path in LIVE_EVIDENCE_TEMPLATE_FILES if path.endswith(".json")]
    for path in json_paths:
        load_json(path)
    for path in LIVE_EVIDENCE_TEMPLATE_FILES:
        require(TEMPLATE_MARKER in read(path), f"{path} must contain a TEMPLATE_ placeholder")
    return [f"live evidence templates: {len(LIVE_EVIDENCE_TEMPLATE_FILES)} files present, parseable, and marked"]


def parse_env_example() -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, line in enumerate(read(".env.example").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        require("=" in stripped, f".env.example line {line_number} must be KEY=")
        key, value = stripped.split("=", 1)
        require(key and re.match(r"^[A-Z0-9_]+$", key), f".env.example line {line_number} has invalid key")
        require(key not in values, f".env.example duplicates {key}")
        values[key] = value
    return values


def parse_secrets_table() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    header: list[str] | None = None
    for line in read("docs/secrets.md").splitlines():
        if not line.startswith("|"):
            continue
        columns = [part.strip() for part in line.strip().strip("|").split("|")]
        if columns and columns[0] == "Variable":
            header = columns
            continue
        if not header or not columns or columns[0].startswith("---"):
            continue
        variable = columns[0].strip("`")
        if variable.startswith("_"):
            continue
        require(variable and re.match(r"^[A-Z0-9_]+$", variable), f"docs/secrets.md invalid variable row: {columns[0]}")
        require(len(columns) == len(header), f"docs/secrets.md row {variable} has wrong column count")
        require(variable not in rows, f"docs/secrets.md duplicates {variable}")
        rows[variable] = dict(zip(header, columns))
    return rows


def check_secrets_inventory() -> list[str]:
    expected = set(EXPECTED_ENV_EXAMPLE_VARS)
    env_values = parse_env_example()
    env_vars = set(env_values)
    require(env_vars == expected, ".env.example variables differ from expected secrets inventory")
    non_empty = sorted(key for key, value in env_values.items() if value)
    require(not non_empty, ".env.example must not contain real or placeholder values: " + ", ".join(non_empty))

    secrets_rows = parse_secrets_table()
    secret_vars = set(secrets_rows)
    require(secret_vars == expected, "docs/secrets.md variables differ from .env.example")
    for variable, row in secrets_rows.items():
        for column in ["Purpose", "Required for", "Owner", "Setup note"]:
            require(row[column].strip(), f"docs/secrets.md {variable} missing {column}")
        require(row["Owner"] == "Briefing Administrator", f"docs/secrets.md {variable} owner must be Briefing Administrator")

    gitignore = read(".gitignore")
    for needle in [".env", ".env.*", "!.env.example"]:
        require(needle in gitignore, f".gitignore missing {needle}")
    handling = read("docs/secrets.md")
    for needle in ["Commit `.env.example`, never `.env`", "Redact secrets", "rotate it immediately"]:
        require(needle in handling, f"docs/secrets.md missing handling rule: {needle}")

    return [f"secrets inventory: {len(expected)} variables documented with empty .env.example values"]


def markdown_section(text: str, heading: str, context: str = "minimal contracts") -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    require(match is not None, f"{context} missing section: {heading}")
    next_match = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(text)
    return text[match.end() : end]


def check_minimal_contracts() -> list[str]:
    text = read("docs/schemas/minimal-contracts.md")
    for heading in ["Shared Conventions", "Canonical Values", "Shared Nested Shapes", "Spike Acceptance Checklist"]:
        require(f"## {heading}" in text, f"minimal contracts missing {heading}")
    for shape in CONTRACT_NESTED_SHAPES:
        require(f"### {shape}" in text, f"minimal contracts missing nested shape {shape}")

    for concept in [
        "source_type",
        "eligibility_state",
        "confidence_level",
        "delivery_status.status",
        "sync_status.status",
        "model_task_status.status",
    ]:
        require(f"`{concept}`" in text, f"minimal contracts missing canonical value {concept}")

    for section, fields in CONTRACT_REQUIRED_FIELDS.items():
        section_text = markdown_section(text, section)
        for field in fields:
            require(f"`{field}`" in section_text, f"{section} missing field {field}")

    for needle in [
        "`run_id` is required",
        "`confidence_notice` is required when `confidence_level` is `medium` or `low`",
        "`media_attribution` is required whenever SourceMedia is displayed",
        "`delivery_status` must be keyed by Briefing Recipient id",
        "`raw_metadata` must not include full article body text",
    ]:
        require(needle in text, f"minimal contracts missing rule: {needle}")

    for path in [
        "docs/spikes/feishu-delivery.md",
        "docs/spikes/model-provider.md",
        "docs/spikes/archive-storage.md",
        "docs/spikes/source-ingestion.md",
    ]:
        require("docs/schemas/minimal-contracts.md" in read(path), f"{path} must reference minimal contracts")

    return [
        f"minimal contracts: {len(CONTRACT_REQUIRED_FIELDS)} top-level contracts and {len(CONTRACT_NESTED_SHAPES)} nested shapes verified",
        "minimal contracts: Feishu, model, archive, and source spikes reference shared contracts",
    ]


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


def require_no_source_review_placeholder(value: str, label: str) -> None:
    lowered = value.lower()
    for placeholder in SOURCE_REVIEW_PLACEHOLDERS:
        require(placeholder not in lowered, f"{label}: source review placeholder remains: {placeholder}")


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
            require_no_source_review_placeholder(row[column], f"{source_id} {column}")
        require("not stored" in row["Full text storage"], f"{source_id}: full text storage must be not stored")
        require("source name" in row["Attribution"], f"{source_id}: attribution must preserve source name")
        if source_id == "src-manual-url":
            require("per submitted url" in row["Terms evidence"].lower(), f"{source_id}: manual URLs need per-URL review")
            require("per-url" in row["Next action"].lower(), f"{source_id}: manual URLs need per-URL next action")
        else:
            require("reviewed" in row["Terms evidence"].lower(), f"{source_id}: terms evidence must cite a reviewed source")

    for row in registry_rows:
        columns = [part.strip() for part in row.strip().strip("|").split("|")]
        source_id = columns[0]
        notes = columns[-1]
        require_no_source_review_placeholder(notes, f"{source_id} registry notes")

    return [
        f"source eligibility reviews: {len(review_rows)} first-version sources covered",
        "source eligibility reviews: "
        + ", ".join(f"{state}={count}" for state, count in sorted(state_counts.items()) if count),
        "source eligibility reviews: no generic terms-evidence placeholders remain",
    ]


def check_source_access_policy() -> list[str]:
    registry_rows = parse_markdown_table("docs/source-registry.md")
    first_version = {row["ID"]: row for row in registry_rows if row["MVP state"] == "first-version"}
    review_by_id = {row["ID"]: row for row in parse_source_eligibility_reviews()}
    policy = load_json("fixtures/source-ingestion/source-access-policy.json")
    require(policy.get("policy_version"), "source access policy must include policy_version")
    source_policies = policy.get("sources")
    require(isinstance(source_policies, list), "source access policy must include sources list")
    policy_by_id = {row["source_id"]: row for row in source_policies}
    require(len(policy_by_id) == len(source_policies), "source access policy source_id values must be unique")

    missing = sorted(set(first_version) - set(policy_by_id))
    extra = sorted(set(policy_by_id) - set(first_version))
    require(not missing, f"source access policy missing first-version sources: {', '.join(missing)}")
    require(not extra, f"source access policy includes non-first-version sources: {', '.join(extra)}")

    allowed_modes = {
        "rss_metadata_probe",
        "rss_metadata_only",
        "arxiv_api_metadata_only",
        "manual_url_metadata_per_item_review",
        "manual_url_metadata_pending_permission",
        "public_metadata_probe",
    }
    production_enabled = 0
    needs_review_locked = 0
    for source_id, source in policy_by_id.items():
        registry = first_version[source_id]
        review = review_by_id[source_id]
        require(source["source_type"] == registry["Type"], f"{source_id}: source_type must match registry")
        require(
            source["eligibility_state"] == review["Eligibility state"],
            f"{source_id}: eligibility_state must match source review",
        )
        require(source["connector_mode"] in allowed_modes, f"{source_id}: invalid connector_mode")
        require(source["full_text_storage"] == "not_stored", f"{source_id}: full_text_storage must be not_stored")
        require(source["media_policy"] != "source_media_allowed", f"{source_id}: media reuse cannot be blanket allowed")

        if source["eligibility_state"] == "eligible":
            require(source["production_auto_ingestion"] is True, f"{source_id}: eligible source should be enabled")
            require(source["requires_owner_review"] is False, f"{source_id}: eligible source should not require owner review")
            production_enabled += 1
        if source["eligibility_state"] == "needs_review":
            require(
                source["production_auto_ingestion"] is False,
                f"{source_id}: needs_review source must not be production auto-ingested",
            )
            require(source["requires_owner_review"] is True, f"{source_id}: needs_review source must require owner review")
            needs_review_locked += 1
        if source_id == "src-manual-url":
            require(source["requires_per_item_review"] is True, "manual URL policy must require per-item review")
            require(
                source["connector_mode"] == "manual_url_metadata_per_item_review",
                "manual URL policy must use per-item review connector mode",
            )
        if source["connector_mode"] == "arxiv_api_metadata_only":
            require("arxiv" in source["rate_policy"], f"{source_id}: arXiv policy must use arXiv rate guidance")

    return [
        f"source access policy: {len(source_policies)} first-version sources covered",
        f"source access policy: production-enabled={production_enabled}, needs-review-locked={needs_review_locked}",
    ]


def check_source_owner_review_queue() -> list[str]:
    review_rows = parse_source_eligibility_reviews()
    needs_review = {row["ID"]: row for row in review_rows if row["Eligibility state"] == "needs_review"}
    policy = load_json("fixtures/source-ingestion/source-access-policy.json")
    policy_by_id = {row["source_id"]: row for row in policy["sources"]}
    queue = load_json("fixtures/source-ingestion/source-owner-review-queue.json")
    require(queue.get("queue_version"), "source owner review queue must include queue_version")
    require(queue.get("default_owner") == "Briefing Administrator", "source owner review queue owner must be Briefing Administrator")
    require(queue.get("source") == "docs/source-eligibility-reviews.md", "source owner review queue must cite review matrix")
    items = queue.get("items")
    require(isinstance(items, list), "source owner review queue must include items list")
    item_by_id = {item.get("source_id"): item for item in items}
    require(len(item_by_id) == len(items), "source owner review queue source_id values must be unique")
    missing = sorted(set(needs_review) - set(item_by_id))
    extra = sorted(set(item_by_id) - set(needs_review))
    require(not missing, "source owner review queue missing needs_review sources: " + ", ".join(missing))
    require(not extra, "source owner review queue includes non-needs_review sources: " + ", ".join(extra))

    allowed_decisions = {
        "summary_permission",
        "feed_reuse_scope",
        "license_obligation",
        "automated_access_permission",
        "manual_per_item_review",
    }
    for source_id, item in item_by_id.items():
        source_label = f"source owner review queue {source_id}"
        policy_row = policy_by_id[source_id]
        require(item.get("review_owner") == "Briefing Administrator", f"{source_label}: wrong review_owner")
        require(item.get("default_connector_mode") == policy_row["connector_mode"], f"{source_label}: default_connector_mode must match access policy")
        require(item.get("production_auto_ingestion_until_resolved") is False, f"{source_label}: production auto-ingestion must stay false")
        require(item.get("media_use_until_resolved") == "none_until_approved", f"{source_label}: media must stay blocked until approved")
        decision = item.get("decision_needed")
        require(decision in allowed_decisions, f"{source_label}: invalid decision_needed {decision}")
        evidence_required = item.get("evidence_required")
        owner_questions = item.get("owner_questions")
        require(isinstance(evidence_required, list) and evidence_required, f"{source_label}: evidence_required must be a non-empty list")
        require(isinstance(owner_questions, list) and owner_questions, f"{source_label}: owner_questions must be a non-empty list")
        require(item.get("review_status") == "open", f"{source_label}: review_status must remain open")
        require(item.get("next_action"), f"{source_label}: missing next_action")
        if source_id == "src-manual-url":
            require(decision == "manual_per_item_review", f"{source_label}: manual URL must require per-item review")
        if policy_row["connector_mode"] == "manual_url_metadata_pending_permission":
            require(decision == "automated_access_permission", f"{source_label}: pending-permission sources need automated access approval")

    return [f"source owner review queue: {len(items)} needs_review sources tracked for owner decisions"]


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


def check_taxonomy_template() -> list[str]:
    text = read("docs/taxonomy/technology-domain-template.md")
    rows: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("| ---") or line.startswith("| Section"):
            continue
        columns = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(columns) != 2:
            continue
        section, subcategories = columns
        if section in EXPECTED_TECHNOLOGY_SECTIONS:
            rows[section] = [part.strip() for part in subcategories.split(";") if part.strip()]

    missing_sections = sorted(EXPECTED_TECHNOLOGY_SECTIONS - set(rows))
    extra_sections = sorted(set(rows) - EXPECTED_TECHNOLOGY_SECTIONS)
    require(not missing_sections, f"taxonomy missing MVP sections: {', '.join(missing_sections)}")
    require(not extra_sections, f"taxonomy has unexpected MVP sections: {', '.join(extra_sections)}")
    for section, subcategories in rows.items():
        require(len(subcategories) >= 3, f"taxonomy section {section} must have at least three subcategories")

    embodied = set(rows["Embodied Intelligence"])
    missing_embodied = sorted(REQUIRED_EMBODIED_SUBCATEGORIES - embodied)
    require(not missing_embodied, "Embodied Intelligence missing subcategories: " + ", ".join(missing_embodied))

    for needle in [
        "One primary `section`",
        "Zero or one primary `subcategory`",
        "Selection Rationale",
        "duplicate coverage",
        "classification confidence is low",
    ]:
        require(needle in text, f"taxonomy template missing rule: {needle}")

    return [
        f"taxonomy template: {len(rows)} MVP sections verified",
        "taxonomy template: Embodied Intelligence required subcategories present",
    ]


def check_briefing_style_guide() -> list[str]:
    text = read("docs/briefing-style-guide.md")
    for heading in STYLE_GUIDE_REQUIRED_HEADINGS:
        require(f"## {heading}" in text, f"briefing style guide missing {heading}")

    for needle in [
        "One Chinese title sentence",
        "Three to four concise Chinese bullets",
        "Original Source Anchor",
        "Confidence Notice when confidence is `medium` or `low`",
        "Media attribution when Source Media is displayed",
        "Do not copy long source passages",
        "Use this shape:",
        "Source name",
        "Never generate news imagery with AI for MVP briefings",
        "It must not include AI chat in the MVP",
        "Section and subcategory names match `docs/taxonomy/technology-domain-template.md`",
    ]:
        require(needle in text, f"briefing style guide missing rule: {needle}")

    for banned in ["震撼发布", "颠覆行业", "史诗级", "炸裂", "杀疯了"]:
        require(banned in text, f"briefing style guide missing sensational wording ban: {banned}")

    return ["briefing style guide: push, confidence, source/media, and deep-dive rules verified"]


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
        "fixtures/source-ingestion/source-access-policy.json",
        "fixtures/source-ingestion/source-owner-review-queue.json",
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


MODEL_OUTPUT_PROFILES = {
    "high-confidence-news": "sample-001-openai-gpt-4o",
    "low-confidence-news": "sample-020-single-source-leak",
    "academic-paper": "sample-018-rt-2",
}


def golden_sample_by_id() -> dict[str, dict]:
    items = load_json("fixtures/golden-samples/items.json")
    return {item["fixture_id"]: item for item in items}


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


def check_spike_runners() -> list[str]:
    gitignore = read(".gitignore")
    require("evidence/" in gitignore, ".gitignore must ignore generated evidence/")
    for path in [
        "scripts/spikes/feishu_delivery_spike.py",
        "scripts/spikes/archive_storage_spike.py",
        "scripts/spikes/model_provider_spike.py",
        "scripts/spikes/readiness_manifest.py",
        "scripts/spikes/live_readiness_preflight.py",
    ]:
        text = read(path)
        require("evidence/" in text, f"{path} must write generated evidence outside tracked docs")
        require("--dry-run" in text, f"{path} must support --dry-run")
    require("--validate-evidence" in read("scripts/spikes/model_provider_spike.py"), "model provider runner must validate evidence")
    return ["spike runners: Feishu, archive, model-provider, readiness-manifest, and preflight helpers present"]


def check_feishu_runner_redaction() -> list[str]:
    path = ROOT / "scripts/spikes/feishu_delivery_spike.py"
    spec = importlib.util.spec_from_file_location("feishu_delivery_spike", path)
    require(spec and spec.loader, "unable to load Feishu delivery spike module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = {
        "receive_id": "ou_syntheticuserid12345",
        "receive_id_type": "open_id",
        "open_id": "ou_syntheticuserid12345",
        "chat_id": "oc_syntheticchatid12345",
        "app_id": "cli_syntheticappid12345",
        "headers": {"Authorization": "Bearer syntheticBearerToken1234567890"},
        "nested": ["ok", "oc_syntheticchatid98765"],
    }
    redacted = module.redact(payload)
    redacted_text = json.dumps(redacted, ensure_ascii=False)
    leaked = [
        pattern_label
        for pattern_label, pattern in LIVE_EVIDENCE_SECRET_PATTERNS
        if pattern.search(redacted_text)
    ]
    require(not leaked, f"Feishu runner redaction leaked patterns: {', '.join(leaked)}")
    require(redacted["receive_id"] == "REDACTED", "Feishu runner must redact receive_id")
    require(redacted["receive_id_type"] == "open_id", "Feishu runner must preserve receive_id_type")
    return ["Feishu runner redaction: ids and bearer tokens are scrubbed"]


def check_readiness_ci_workflow() -> list[str]:
    text = read(".github/workflows/pre-development-readiness.yml")
    for needle in [
        "python scripts/check_readiness.py",
        "python -m py_compile",
        "scripts/spikes/readiness_manifest.py",
        "scripts/spikes/live_readiness_preflight.py",
        "--require-evidence --evidence-root fixtures/live-evidence-templates",
        "Expected template evidence validation to fail",
        "--require-evidence --evidence-root fixtures/live-evidence-negative/leaky-feishu",
        "Expected leaky evidence validation to fail",
    ]:
        require(needle in text, f"readiness CI workflow missing: {needle}")
    require("--require-live" not in text, "readiness CI must not require live external credentials")
    require("--require-github" not in text, "readiness CI must not require GitHub tracker access")
    return ["readiness CI workflow: local gate, script compile, template-negative, and redaction-negative checks present"]


def adr_section_bullet_count(text: str, marker: str) -> int:
    require(marker in text, f"ADR missing {marker}")
    section = text.split(marker, 1)[1]
    next_marker = re.search(r"\n\*\*[^*]+\*\*", section)
    if next_marker:
        section = section[: next_marker.start()]
    return sum(1 for line in section.splitlines() if line.strip().startswith("- "))


def check_adrs() -> list[str]:
    required = list(REQUIRED_ADRS)
    require_files(required)
    architecture_notes = read("docs/ARCHITECTURE-NOTES.md")
    statuses: dict[str, int] = {"accepted": 0, "proposed": 0}
    for path, expectations in REQUIRED_ADRS.items():
        text = read(path)
        require(text.startswith("# "), f"{path} missing title")
        status_match = re.search(r"^Status:\s+([a-z-]+)\s*$", text, re.MULTILINE)
        require(status_match is not None, f"{path} missing Status")
        status = status_match.group(1)
        require(status in statuses, f"{path} status must be accepted or proposed")
        statuses[status] += 1
        require(adr_section_bullet_count(text, "**Tradeoffs**") >= 2, f"{path} must record real tradeoffs")
        require(adr_section_bullet_count(text, "**Consequences**") >= 2, f"{path} must record consequences")
        for keyword in expectations["keywords"]:
            require(keyword in text, f"{path} missing decision keyword: {keyword}")
        require(
            expectations["architecture_default"] in architecture_notes,
            f"ARCHITECTURE-NOTES.md missing ADR default: {expectations['architecture_default']}",
        )

    require("AI chat can later be added" in architecture_notes, "ARCHITECTURE-NOTES.md must keep post-MVP AI chat extension")
    return [
        f"required ADRs present: {len(required)}",
        "required ADRs: "
        + ", ".join(f"{status}={count}" for status, count in sorted(statuses.items()) if count),
        "required ADRs: tradeoffs, consequences, decision keywords, and architecture defaults verified",
    ]


def markdown_bullet_count(section: str) -> int:
    return sum(1 for line in section.splitlines() if line.strip().startswith("- "))


def parse_issue_markdown_table(section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or all(not cell for cell in cells):
            continue
        if all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append(cells)
    return rows


def check_issue_relevant_docs(path_label: str, section: str) -> None:
    refs = re.findall(r"`([^`]+)`", section)
    require(refs, f"{path_label} Relevant docs must include backticked repo paths")
    for ref in refs:
        require(
            ref.startswith(("docs/", "fixtures/", ".env.example", ".gitignore")),
            f"{path_label} Relevant docs contains unsupported path: {ref}",
        )
        require((ROOT / ref).exists(), f"{path_label} Relevant docs path does not exist: {ref}")


def check_mvp_issue_drafts() -> list[str]:
    files = sorted((ROOT / "docs/issues/mvp").glob("*.md"))
    expected_paths = {ROOT / path for path in MVP_ISSUE_DRAFTS.values()}
    actual_paths = set(files)
    missing_paths = sorted(path.relative_to(ROOT).as_posix() for path in expected_paths - actual_paths)
    extra_paths = sorted(path.relative_to(ROOT).as_posix() for path in actual_paths - expected_paths)
    require(not missing_paths, "MVP issue drafts missing: " + ", ".join(missing_paths))
    require(not extra_paths, "unexpected MVP issue drafts: " + ", ".join(extra_paths))

    for number, draft_path in MVP_ISSUE_DRAFTS.items():
        path = ROOT / draft_path
        path_label = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        require(text.startswith("# MVP: "), f"{path_label} must start with an MVP issue title")
        sections = {
            heading: markdown_section(text, heading, path_label).strip()
            for heading in MVP_ISSUE_REQUIRED_SECTIONS
        }
        for heading, section in sections.items():
            require(section, f"{path_label} {heading} section must not be empty")
            require("TODO" not in section, f"{path_label} {heading} section must not contain TODO")
        require(len(sections["Problem"].split()) >= 8, f"{path_label} Problem section is too thin")
        for heading in ["Scope", "Out of scope", "Acceptance criteria", "Test expectations"]:
            require(markdown_bullet_count(sections[heading]) >= 2, f"{path_label} {heading} must have at least two bullets")
        require(markdown_bullet_count(sections["Acceptance criteria"]) >= 3, f"{path_label} Acceptance criteria must be concrete")
        require(markdown_bullet_count(sections["Relevant docs"]) >= 1, f"{path_label} Relevant docs must list repo paths")
        require(markdown_bullet_count(sections["Dependencies"]) >= 1, f"{path_label} Dependencies must name blockers or prerequisites")
        check_issue_relevant_docs(path_label, sections["Relevant docs"])
        require("`needs-triage`" in sections["Triage label"], f"{path_label} must stay needs-triage")
        require("ready-for-agent" not in sections["Triage label"], f"{path_label} must not be ready-for-agent yet")

    breakdown = read("docs/github-issue-breakdown.md")
    issue_rows = parse_issue_markdown_table(markdown_section(breakdown, "MVP Issue Drafts", "docs/github-issue-breakdown.md"))
    issue_rows = [row for row in issue_rows if row[0] != "Module"]
    for number, draft_path in MVP_ISSUE_DRAFTS.items():
        matching_rows = [row for row in issue_rows if f"#{number}" in row and f"`{draft_path}`" in row]
        require(matching_rows, f"issue breakdown missing #{number} mapped to {draft_path}")
        row_text = " | ".join(matching_rows[0])
        require("`needs-triage`" in row_text, f"issue breakdown #{number} must stay needs-triage")
        require("ready-for-agent" not in row_text, f"issue breakdown #{number} must not be ready-for-agent yet")

    coverage_section = markdown_section(breakdown, "Acceptance Coverage Map", "docs/github-issue-breakdown.md")
    coverage_rows = parse_issue_markdown_table(coverage_section)
    coverage_rows = [row for row in coverage_rows if row[0] != "MVP acceptance item"]
    checklist_items = [
        line
        for line in markdown_section(read("docs/MVP-SCOPE.md"), "MVP Acceptance Checklist", "docs/MVP-SCOPE.md").splitlines()
        if line.strip().startswith("- ")
    ]
    require(
        len(coverage_rows) == len(checklist_items),
        f"acceptance coverage map must have {len(checklist_items)} rows, found {len(coverage_rows)}",
    )
    known_stems = {Path(path).stem for path in MVP_ISSUE_DRAFTS.values()}
    for row in coverage_rows:
        require(len(row) >= 2, "acceptance coverage map rows must include item and primary issue draft")
        item, primary = row[0], row[1]
        require(item and primary, "acceptance coverage map rows must not be empty")
        require("TODO" not in item and "TODO" not in primary, "acceptance coverage map must not contain TODO")
        require(
            any(stem in primary for stem in known_stems),
            f"acceptance coverage row must reference a known MVP issue draft: {item}",
        )
    for keyword in MVP_COVERAGE_KEYWORDS:
        require(keyword in coverage_section, f"acceptance coverage map missing keyword: {keyword}")

    return [
        f"MVP issue drafts: {len(MVP_ISSUE_DRAFTS)} mapped drafts linked to #10-#20",
        "MVP issue drafts: required sections, relevant docs, dependencies, labels, and acceptance coverage verified",
    ]


def check_github_tracker() -> list[str]:
    run_command(["gh", "auth", "status", "--hostname", "github.com"], "gh auth status must succeed for github.com")
    origin_url = run_command(["git", "remote", "get-url", "origin"], "git origin remote must exist").stdout.strip()
    require(
        origin_url in ALLOWED_ORIGIN_URLS,
        f"git origin must point to {EXPECTED_GITHUB_REPO} via SSH or HTTPS",
    )

    repo = run_gh_json(
        [
            "repo",
            "view",
            EXPECTED_GITHUB_REPO,
            "--json",
            "defaultBranchRef,viewerPermission,nameWithOwner",
        ]
    )
    require(repo["nameWithOwner"] == EXPECTED_GITHUB_REPO, f"GitHub repo must be {EXPECTED_GITHUB_REPO}")
    require(repo["defaultBranchRef"]["name"] == "main", "GitHub default branch must be main")
    require(
        repo["viewerPermission"] in GITHUB_WRITE_PERMISSIONS,
        "GitHub viewer must have write, maintain, or admin permission",
    )

    label_rows = run_gh_json(["label", "list", "--limit", "100", "--json", "name"])
    labels = {row["name"] for row in label_rows}
    missing_labels = sorted(REQUIRED_GITHUB_LABELS - labels)
    require(not missing_labels, f"GitHub labels missing: {', '.join(missing_labels)}")

    milestone_rows = run_gh_json(["api", "repos/KG9750/TechNews/milestones"])
    milestones = {row["title"]: row for row in milestone_rows}
    missing_milestones = sorted(REQUIRED_GITHUB_MILESTONES - set(milestones))
    require(not missing_milestones, f"GitHub milestones missing: {', '.join(missing_milestones)}")
    for title in REQUIRED_GITHUB_MILESTONES:
        require(milestones[title]["state"] == "open", f"GitHub milestone {title} must be open")

    issue_rows = run_gh_json(
        [
            "issue",
            "list",
            "--state",
            "all",
            "--limit",
            "100",
            "--json",
            "number,title,state,labels,milestone",
        ]
    )
    issues = {int(row["number"]): row for row in issue_rows}
    required_issues = PREDEVELOPMENT_ISSUES | MVP_ISSUES
    missing_issues = sorted(required_issues - set(issues))
    require(not missing_issues, "GitHub issues missing: " + ", ".join(f"#{number}" for number in missing_issues))

    for number in PREDEVELOPMENT_ISSUES:
        issue = issues[number]
        milestone = issue.get("milestone") or {}
        require(milestone.get("title") == "pre-development", f"GitHub issue #{number} must use pre-development milestone")

    for number in MVP_ISSUES:
        issue = issues[number]
        labels = {label["name"] for label in issue.get("labels", [])}
        milestone = issue.get("milestone") or {}
        require(issue["state"] == "OPEN", f"GitHub issue #{number} must remain open before MVP work starts")
        require(milestone.get("title") == "mvp", f"GitHub issue #{number} must use mvp milestone")
        require("needs-triage" in labels, f"GitHub issue #{number} must keep needs-triage before readiness passes")
        require("ready-for-agent" not in labels, f"GitHub issue #{number} must not be ready-for-agent before readiness passes")
        require("ready-for-human" not in labels, f"GitHub issue #{number} must not be ready-for-human before readiness passes")

    for number in [3, 5, 6]:
        issue = issues[number]
        labels = {label["name"] for label in issue.get("labels", [])}
        require(issue["state"] == "OPEN", f"GitHub issue #{number} must remain open until live evidence is attached")
        require("needs-info" in labels, f"GitHub issue #{number} must keep needs-info while external evidence is blocked")

    issue_1_labels = {label["name"] for label in issues[1].get("labels", [])}
    require(issues[1]["state"] == "OPEN", "GitHub issue #1 must remain open until the readiness gate passes")
    require("needs-triage" in issue_1_labels, "GitHub issue #1 must keep needs-triage while gate is not passed")

    return [
        f"GitHub tracker: origin targets {EXPECTED_GITHUB_REPO} and default branch is main",
        f"GitHub tracker: viewer permission is {repo['viewerPermission']}",
        f"GitHub tracker: {len(REQUIRED_GITHUB_LABELS)} triage labels present",
        f"GitHub tracker: {len(REQUIRED_GITHUB_MILESTONES)} milestones open",
        f"GitHub tracker: {len(MVP_ISSUES)} MVP issues remain needs-triage",
        "GitHub tracker: Feishu, model, and archive spike issues remain needs-info",
    ]


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


def check_no_template_marker(path: Path, failures: list[str], label: str) -> None:
    if TEMPLATE_MARKER in read_path(path):
        failures.append(f"{label} still contains a TEMPLATE_ placeholder: {path}")


def check_no_sensitive_live_evidence(path: Path, failures: list[str], label: str) -> None:
    text = read_path(path)
    for pattern_label, pattern in LIVE_EVIDENCE_SECRET_PATTERNS:
        if pattern.search(text):
            failures.append(f"{label} may leak {pattern_label}: {path}")
    for env_name in SENSITIVE_ENV_NAMES:
        value = os.environ.get(env_name, "")
        if len(value) >= 8 and value in text:
            failures.append(f"{label} contains raw environment value {env_name}: {path}")


def check_live_evidence_file(path: Path, failures: list[str], label: str) -> None:
    check_no_template_marker(path, failures, label)
    check_no_sensitive_live_evidence(path, failures, label)


def check_feishu_live_evidence(evidence_root: Path) -> tuple[list[str], list[str], list[str]]:
    evidence_dir = evidence_root / "feishu-delivery"
    missing: list[str] = []
    failures: list[str] = []
    passed: list[str] = []
    required_files = {
        "user response": evidence_dir / "user-response.redacted.json",
        "group response": evidence_dir / "group-response.redacted.json",
        "rendered message": evidence_dir / "rendered-message.md",
    }
    for label, path in required_files.items():
        if not path.exists():
            missing.append(f"Feishu live evidence missing {label}: {path}")
    if missing:
        return passed, missing, failures
    for label, path in required_files.items():
        check_live_evidence_file(path, failures, f"Feishu live evidence {label}")
    for label, path in [
        ("user", required_files["user response"]),
        ("group", required_files["group response"]),
    ]:
        payload = load_json_path(path)
        if payload.get("code") != 0:
            failures.append(f"Feishu {label} response code must be 0")
        data = payload.get("data", {})
        if not isinstance(data, dict) or not data:
            failures.append(f"Feishu {label} response must include data")
    rendered = required_files["rendered message"].read_text(encoding="utf-8")
    for needle in ["Source", "置信提示"]:
        if needle not in rendered:
            failures.append(f"Feishu rendered message missing {needle}")
    if not failures:
        passed.append("Feishu live evidence: user and group delivery responses present")
    return passed, missing, failures


def check_live_evidence_redaction_negative_fixture() -> list[str]:
    evidence_root = ROOT / "fixtures/live-evidence-negative/leaky-feishu"
    _, missing, failures = check_feishu_live_evidence(evidence_root)
    require(not missing, "live evidence redaction negative fixture must include all Feishu files")
    leak_failures = [failure for failure in failures if "may leak" in failure]
    require(leak_failures, "live evidence redaction negative fixture must fail on sensitive leak patterns")
    return [f"live evidence redaction negative fixture: {len(leak_failures)} leak checks fire"]


def check_archive_live_evidence(evidence_root: Path) -> tuple[list[str], list[str], list[str]]:
    evidence_dir = evidence_root / "archive-storage"
    result_path = evidence_dir / "sync-result.json"
    missing: list[str] = []
    failures: list[str] = []
    passed: list[str] = []
    if not result_path.exists():
        missing.append(f"Archive live evidence missing sync result: {result_path}")
        return passed, missing, failures
    check_live_evidence_file(result_path, failures, "Archive live evidence sync result")
    payload = load_json_path(result_path)
    local_status = payload.get("local_archive", {}).get("status")
    remote_status = payload.get("remote_sync", {}).get("status")
    if local_status != "written":
        failures.append("Archive live evidence local_archive.status must be written")
    if remote_status != "synced":
        failures.append("Archive live evidence remote_sync.status must be synced")
    if int(payload.get("local_archive", {}).get("file_count") or 0) <= 0:
        failures.append("Archive live evidence local_archive.file_count must be > 0")
    if int(payload.get("remote_sync", {}).get("file_count") or 0) <= 0:
        failures.append("Archive live evidence remote_sync.file_count must be > 0")
    for label, path in [
        ("local tree", evidence_dir / "local-tree.txt"),
        ("remote tree", evidence_dir / "remote-tree.txt"),
    ]:
        if not path.exists():
            missing.append(f"Archive live evidence missing {label}: {path}")
        else:
            check_live_evidence_file(path, failures, f"Archive live evidence {label}")
    if not failures and not missing:
        passed.append("Archive live evidence: local write and remote sync success present")
    return passed, missing, failures


def check_model_live_evidence(evidence_root: Path) -> tuple[list[str], list[str], list[str]]:
    evidence_dir = evidence_root / "model-provider"
    output_dir = evidence_dir / "outputs"
    usage_path = evidence_dir / "usage-log.json"
    missing: list[str] = []
    failures: list[str] = []
    passed: list[str] = []
    samples = golden_sample_by_id()
    if not output_dir.exists():
        missing.append(f"Model live evidence missing output directory: {output_dir}")
    for profile, fixture_id in MODEL_OUTPUT_PROFILES.items():
        path = output_dir / f"{profile}.json"
        if not path.exists():
            missing.append(f"Model live evidence missing output: {path}")
            continue
        check_live_evidence_file(path, failures, f"Model live evidence {profile} output")
        payload = load_json_path(path)
        fixture = samples[fixture_id]
        if payload.get("input_fixture_id") != fixture_id:
            failures.append(f"{path}: input_fixture_id must be {fixture_id}")
        item = payload.get("briefing_item")
        if not isinstance(item, dict):
            failures.append(f"{path}: missing briefing_item")
            continue
        required = [
            "id",
            "run_id",
            "candidate_id",
            "section",
            "title_zh",
            "bullets_zh",
            "original_source_anchor",
            "selection_rationale",
            "confidence_level",
        ]
        for field in required:
            if field not in item:
                failures.append(f"{path}: missing briefing_item.{field}")
        bullets = item.get("bullets_zh", [])
        if not isinstance(bullets, list) or not 3 <= len(bullets) <= 4:
            failures.append(f"{path}: bullets_zh must contain 3-4 bullets")
        anchor = item.get("original_source_anchor", {})
        expected_anchor = fixture["raw_source_metadata"]
        for field in ["source_name", "original_title", "source_url"]:
            if anchor.get(field) != expected_anchor[field]:
                failures.append(f"{path}: original_source_anchor.{field} changed")
        if item.get("confidence_level") in {"medium", "low"} and not item.get("confidence_notice"):
            failures.append(f"{path}: confidence_notice required for {item.get('confidence_level')} confidence")
        if profile == "low-confidence-news" and item.get("confidence_level") != "low":
            failures.append(f"{path}: low-confidence fixture must remain low")
        usage = payload.get("model_usage", {})
        if usage.get("provider") in {"fixture", None, ""}:
            failures.append(f"{path}: model_usage.provider must identify a live provider")
        if usage.get("model") in {"not_called", None, ""}:
            failures.append(f"{path}: model_usage.model must identify a live model")
        if int(usage.get("request_count") or 0) <= 0:
            failures.append(f"{path}: model_usage.request_count must be > 0")
    if not usage_path.exists():
        missing.append(f"Model live evidence missing usage log: {usage_path}")
    else:
        check_live_evidence_file(usage_path, failures, "Model live evidence usage log")
        usage_log = load_json_path(usage_path)
        if usage_log.get("provider") in {"fixture", None, ""}:
            failures.append("Model usage log provider must identify a live provider")
        if usage_log.get("model") in {"not_called", None, ""}:
            failures.append("Model usage log model must identify a live model")
        tasks = usage_log.get("tasks", [])
        if len(tasks) != 3:
            failures.append("Model usage log must include three tasks")
        for task in tasks:
            if int(task.get("request_count") or 0) <= 0:
                failures.append("Model usage log every task request_count must be > 0")
            if "latency_ms" not in task:
                failures.append("Model usage log every task must include latency_ms")
    if not failures and not missing:
        passed.append("Model live evidence: three live outputs and usage log valid")
    return passed, missing, failures


def require_manifest_files(
    manifest: dict,
    evidence_root: Path,
    spike_name: str,
    expected_files: set[str],
    missing: list[str],
    failures: list[str],
) -> dict:
    spikes = manifest.get("spikes", {})
    spike = spikes.get(spike_name)
    if not isinstance(spike, dict):
        failures.append(f"Live evidence manifest missing spikes.{spike_name}")
        return {}
    if spike.get("status") != "passed":
        failures.append(f"Live evidence manifest {spike_name}.status must be passed")
    files = spike.get("evidence_files", [])
    if not isinstance(files, list):
        failures.append(f"Live evidence manifest {spike_name}.evidence_files must be a list")
        return spike
    actual_files = set(files)
    missing_declared = sorted(expected_files - actual_files)
    extra_declared = sorted(actual_files - expected_files)
    if missing_declared:
        failures.append(f"Live evidence manifest {spike_name} missing file declarations: {', '.join(missing_declared)}")
    if extra_declared:
        failures.append(f"Live evidence manifest {spike_name} has unexpected file declarations: {', '.join(extra_declared)}")
    for relative in files:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            failures.append(f"Live evidence manifest {spike_name} has unsafe evidence path: {relative}")
            continue
        if not (evidence_root / path).exists():
            missing.append(f"Live evidence manifest referenced file missing: {evidence_root / path}")
    return spike


def check_live_evidence_manifest(evidence_root: Path) -> tuple[list[str], list[str], list[str]]:
    path = evidence_root / "readiness-manifest.json"
    missing: list[str] = []
    failures: list[str] = []
    passed: list[str] = []
    if not path.exists():
        missing.append(f"Live evidence manifest missing: {path}")
        return passed, missing, failures

    check_live_evidence_file(path, failures, "Live evidence manifest")
    manifest = load_json_path(path)
    if manifest.get("repository") != EXPECTED_GITHUB_REPO:
        failures.append(f"Live evidence manifest repository must be {EXPECTED_GITHUB_REPO}")
    for field in ["readiness_evidence_id", "generated_at", "commit", "reviewed_by"]:
        if not manifest.get(field):
            failures.append(f"Live evidence manifest missing {field}")
    redaction_review = manifest.get("redaction_review", {})
    if not isinstance(redaction_review, dict) or not redaction_review.get("reviewed_at") or not redaction_review.get("notes"):
        failures.append("Live evidence manifest redaction_review must include reviewed_at and notes")

    feishu = require_manifest_files(
        manifest,
        evidence_root,
        "feishu_delivery",
        {
            "feishu-delivery/user-response.redacted.json",
            "feishu-delivery/group-response.redacted.json",
            "feishu-delivery/rendered-message.md",
        },
        missing,
        failures,
    )
    requirements = set(feishu.get("requirements", []))
    for requirement in ["one_user_delivery", "one_group_delivery", "source_line_present", "confidence_notice_present"]:
        if requirement not in requirements:
            failures.append(f"Live evidence manifest Feishu requirements missing {requirement}")

    model = require_manifest_files(
        manifest,
        evidence_root,
        "model_provider",
        {
            "model-provider/outputs/high-confidence-news.json",
            "model-provider/outputs/low-confidence-news.json",
            "model-provider/outputs/academic-paper.json",
            "model-provider/usage-log.json",
        },
        missing,
        failures,
    )
    model_usage_path = evidence_root / "model-provider/usage-log.json"
    if model_usage_path.exists():
        usage = load_json_path(model_usage_path)
        if model.get("run_id") != usage.get("run_id"):
            failures.append("Live evidence manifest model_provider.run_id must match usage-log run_id")
        if model.get("provider") != usage.get("provider"):
            failures.append("Live evidence manifest model_provider.provider must match usage-log provider")
        if model.get("model") != usage.get("model"):
            failures.append("Live evidence manifest model_provider.model must match usage-log model")
        for output_name in ["high-confidence-news", "low-confidence-news", "academic-paper"]:
            output_path = evidence_root / f"model-provider/outputs/{output_name}.json"
            if output_path.exists():
                output = load_json_path(output_path)
                output_run_id = output.get("briefing_item", {}).get("run_id")
                if output_run_id != usage.get("run_id"):
                    failures.append(f"Live evidence manifest model run_id mismatch in {output_path}")

    archive = require_manifest_files(
        manifest,
        evidence_root,
        "archive_storage",
        {
            "archive-storage/sync-result.json",
            "archive-storage/local-tree.txt",
            "archive-storage/remote-tree.txt",
        },
        missing,
        failures,
    )
    archive_sync_path = evidence_root / "archive-storage/sync-result.json"
    if archive_sync_path.exists():
        sync_result = load_json_path(archive_sync_path)
        if archive.get("run_id") != sync_result.get("run_id"):
            failures.append("Live evidence manifest archive_storage.run_id must match sync-result run_id")

    if not failures and not missing:
        passed.append("Live evidence manifest: declared files and spike run metadata are consistent")
    return passed, missing, failures


def check_live_evidence(evidence_root: Path) -> tuple[list[str], list[str], list[str]]:
    passed: list[str] = []
    missing: list[str] = []
    failures: list[str] = []
    for checker in [
        check_live_evidence_manifest,
        check_feishu_live_evidence,
        check_archive_live_evidence,
        check_model_live_evidence,
    ]:
        check_passed, check_missing, check_failures = checker(evidence_root)
        passed.extend(check_passed)
        missing.extend(check_missing)
        failures.extend(check_failures)
    return passed, missing, failures


def run(require_live: bool, require_evidence: bool, require_github: bool, evidence_root: Path) -> int:
    checks = [
        check_required_files,
        check_json_fixtures,
        check_live_evidence_templates,
        check_secrets_inventory,
        check_minimal_contracts,
        check_source_registry,
        check_source_eligibility_reviews,
        check_source_access_policy,
        check_source_owner_review_queue,
        check_taxonomy_template,
        check_briefing_style_guide,
        check_golden_samples,
        check_archive_fixture,
        check_model_fixtures,
        check_feishu_fixture,
        check_spike_runners,
        check_feishu_runner_redaction,
        check_live_evidence_redaction_negative_fixture,
        check_readiness_ci_workflow,
        check_adrs,
        check_mvp_issue_drafts,
    ]
    if require_github:
        checks.append(check_github_tracker)
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
    evidence_missing: list[str] = []
    evidence_failures: list[str] = []
    if require_evidence:
        evidence_ok, evidence_missing, evidence_failures = check_live_evidence(evidence_root)
        passed.extend(evidence_ok)
        failures.extend(evidence_failures)

    for item in passed:
        print(f"PASS {item}")
    for item in failures:
        print(f"FAIL {item}")
    for item in review_notes:
        print(f"REVIEW {item}")
    for item in external_missing:
        print(f"BLOCKED {item}")
    for item in evidence_missing:
        print(f"BLOCKED {item}")

    if failures:
        return 1
    if require_live and external_missing:
        return 2
    if require_evidence and evidence_missing:
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
    parser.add_argument(
        "--require-evidence",
        action="store_true",
        help="Fail when redacted live spike evidence is missing or incomplete.",
    )
    parser.add_argument(
        "--require-github",
        action="store_true",
        help="Fail when GitHub labels, milestones, or issue tracker gates drift.",
    )
    parser.add_argument(
        "--evidence-root",
        default=str(DEFAULT_EVIDENCE_ROOT),
        help="Directory containing redacted live spike evidence.",
    )
    args = parser.parse_args()
    return run(
        require_live=args.require_live,
        require_evidence=args.require_evidence,
        require_github=args.require_github,
        evidence_root=Path(args.evidence_root),
    )


if __name__ == "__main__":
    raise SystemExit(main())
