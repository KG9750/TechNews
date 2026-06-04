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
from datetime import datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = ROOT / "evidence"
TEMPLATE_MARKER = "TEMPLATE_"
DISALLOWED_FULL_BODY_KEYS = {
    "article_body",
    "body",
    "body_text",
    "complete_article_text",
    "content",
    "full_text",
    "html",
    "text",
    "transcript",
}
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
    "fixtures/live-evidence-templates/feishu-delivery/user-request.redacted.json",
    "fixtures/live-evidence-templates/feishu-delivery/user-response.redacted.json",
    "fixtures/live-evidence-templates/feishu-delivery/group-request.redacted.json",
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


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def load_json(path: str):
    return json.loads(read(path))


def load_json_path(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def nested_keys(value) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for child in value.values():
            keys.update(nested_keys(child))
        return keys
    if isinstance(value, list):
        keys = set()
        for child in value:
            keys.update(nested_keys(child))
        return keys
    return set()


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
        "scripts/test_live_evidence_helpers.py",
        "scripts/readiness_action_packet.py",
        "scripts/test_readiness_action_packet.py",
        "scripts/source_owner_review_decision.py",
        "scripts/test_source_owner_review_decision.py",
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
    eligible_mode_by_source_type = {
        "academic_source": "arxiv_api_metadata_only",
        "public_feed": "rss_metadata_only",
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
            expected_mode = eligible_mode_by_source_type.get(source["source_type"])
            require(expected_mode is not None, f"{source_id}: eligible source type lacks a production metadata connector")
            require(source["connector_mode"] == expected_mode, f"{source_id}: eligible source must use {expected_mode}")
            production_enabled += 1
        if source["eligibility_state"] == "needs_review":
            require(
                source["production_auto_ingestion"] is False,
                f"{source_id}: needs_review source must not be production auto-ingested",
            )
            require(source["requires_owner_review"] is True, f"{source_id}: needs_review source must require owner review")
            needs_review_locked += 1
        if source_id == "src-manual-url":
            require(source["eligibility_state"] != "eligible", "manual URL policy must stay per-item reviewed")
            require(source["production_auto_ingestion"] is False, "manual URL policy must not be production auto-ingested")
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


def check_source_owner_review_decision_helper() -> list[str]:
    text = read("scripts/source_owner_review_decision.py")
    test_text = read("scripts/test_source_owner_review_decision.py")
    for needle in [
        "fixtures/source-ingestion/source-owner-review-queue.json",
        "fixtures/source-ingestion/source-access-policy.json",
        "evidence/source-owner-reviews",
        "--list-open",
        "--status",
        "--draft",
        "--draft-all",
        "--packet",
        "--packet-all",
        "--packet-index",
        "--worksheet",
        "--batch-plan",
        "--request-packet",
        "--refresh-context-all",
        "--validate",
        "--validate-all",
        "--apply",
        "--apply-all",
        "current_artifact_context",
        "artifact_updates",
        "TEMPLATE_",
        "INCOMPLETE_REVIEW_TEXT",
        "require_completed_review_text",
        "require_evidence_reference",
        "EVIDENCE_NOTE_PREFIXES",
        "require_owner_answer",
        "OWNER_ANSWER_DECISION_TERMS",
        "evidence_checked missing required evidence",
        "evidence_checked duplicates required evidence",
        "evidence_checked has unexpected required_evidence values",
        "parse_review_date",
        "checked_at must be on or before reviewed_at",
        "expected_source_id_from_path",
        "decision source_id must match expected source",
        "ELIGIBLE_CONNECTOR_MODE_BY_SOURCE_TYPE",
        "eligible decisions for {source_type} must use connector_mode",
        "decisions must keep connector_mode at default",
        "request-packet.md",
        "review_request_packet",
        "write_request_packet",
        "Source Owner Decision Request Packet",
    ]:
        require(needle in text, f"source owner review decision helper missing: {needle}")
    for needle in [
        "test_draft_includes_current_artifact_context",
        "test_draft_all_writes_every_open_review_without_overwriting_existing",
        "test_packet_includes_review_context_and_commands",
        "test_packet_all_writes_every_open_packet",
        "test_packet_index_groups_status_and_paths",
        "test_packet_index_writes_index_file",
        "test_review_worksheet_includes_decision_fields_and_prompts",
        "test_review_worksheet_writes_worksheet_file",
        "test_batch_plan_groups_open_items_and_paths",
        "test_batch_plan_writes_batch_plan_file",
        "test_request_packet_groups_batches_and_owner_prompts",
        "test_request_packet_writes_request_packet_file",
        "test_refresh_context_all_updates_existing_drafts_without_overwriting_answers",
        "test_status_reports_template_drafts_as_invalid",
        "test_status_reports_completed_drafts_as_valid",
        "test_validate_all_fails_for_template_drafts",
        "test_validate_all_passes_completed_open_reviews",
        "test_decision_rejects_placeholder_evidence_note",
        "test_decision_rejects_evidence_note_without_reference_type",
        "test_decision_rejects_short_internal_evidence_note",
        "test_decision_rejects_placeholder_owner_answer",
        "test_decision_rejects_short_owner_answer",
        "test_decision_rejects_generic_owner_answer",
        "test_decision_rejects_missing_required_evidence_item",
        "test_decision_rejects_duplicate_required_evidence_item",
        "test_decision_rejects_unexpected_required_evidence_item",
        "test_decision_rejects_invalid_reviewed_at_date",
        "test_decision_rejects_evidence_checked_after_review_date",
        "test_decision_rejects_placeholder_reviewer",
        "test_decision_rejects_placeholder_policy_field",
        "test_decision_rejects_mismatched_source_id_filename",
        "test_eligible_decision_accepts_metadata_only_connector_mode",
        "test_eligible_decision_rejects_probe_connector_mode",
        "test_needs_review_decision_rejects_production_connector_mode",
        "test_manual_url_decision_cannot_be_marked_eligible",
        "test_apply_all_rejects_template_drafts_without_writing",
        "test_apply_all_dry_run_validates_without_writing",
        "test_apply_all_applies_completed_open_reviews",
        "test_blocked_decision_updates_artifacts_and_closes_queue",
        "test_needs_review_decision_keeps_queue_open",
        "isolated_artifacts",
    ]:
        require(needle in test_text, f"source owner review decision tests missing: {needle}")
    for path in ["docs/source-owner-review-runbook.md", "docs/source-eligibility-checklist.md"]:
        require("scripts/source_owner_review_decision.py" in read(path), f"{path} must document source owner decision helper")
    return ["source owner review decision helper: list, status, context-rich batch draft, review packets, index, worksheet, batch plan, owner request packet, batch validation, batch apply, and regression tests present"]


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
    for item in items:
        present = DISALLOWED_FULL_BODY_KEYS & set(item.keys())
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
    for needle in ["AI / Multimodal AI", "Hardware / AI accelerators", "置信提示", "Source", "Archive"]:
        require(needle in rendered or needle in card_text, f"Feishu fixture missing {needle}")
    require(request["user_delivery"]["query"]["receive_id_type"] == "open_id", "user delivery must use open_id")
    require(request["group_delivery"]["query"]["receive_id_type"] == "chat_id", "group delivery must use chat_id")
    forbidden = ["FEISHU_APP_SECRET=", "Bearer ey", "ou_", "oc_"]
    request_text = json.dumps(request)
    leaked = [value for value in forbidden if value in request_text]
    require(not leaked, f"possible Feishu secret or recipient id leaked: {', '.join(leaked)}")
    return ["Feishu fixture: user/group request shapes, archive link, and message content valid"]


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
    archive_text = read("scripts/spikes/archive_storage_spike.py")
    require("redact_archive_text" in archive_text, "archive runner must redact sync failure paths")
    require("failure_reason" in archive_text and "redact_archive_text(str(error))" in archive_text, "archive runner must redact OSError failure reasons")
    require("--validate-evidence" in archive_text, "archive runner must validate redacted live evidence")
    require(
        "archive evidence local and remote tree listings must match" in archive_text,
        "archive runner must validate matching local and remote tree evidence",
    )
    require(
        "file_count must match local tree file entries" in archive_text,
        "archive runner must validate file counts against tree file entries",
    )
    feishu_text = read("scripts/spikes/feishu_delivery_spike.py")
    require("--attempt-group-webhook-fallback" in feishu_text, "Feishu runner must expose explicit group webhook fallback")
    require("build_group_webhook_payload" in feishu_text, "Feishu runner must build group webhook fallback payloads")
    require("does_not_replace_internal_app_group_evidence" in feishu_text, "Feishu fallback must not replace internal-app group evidence")
    require("--validate-evidence" in feishu_text, "Feishu runner must validate redacted live evidence")
    require("validate_delivery_request" in feishu_text, "Feishu runner must validate internal-app request evidence")
    require("receive_id_type must be" in feishu_text, "Feishu runner must validate user/group receive_id_type evidence")
    require(
        "Feishu rendered message missing Archive or Deep-Dive link" in feishu_text,
        "Feishu runner must validate rendered message archive/deep-dive link evidence",
    )
    model_provider_text = read("scripts/spikes/model_provider_spike.py")
    require("--validate-evidence" in model_provider_text, "model provider runner must validate evidence")
    require("--validate-requests" in model_provider_text, "model provider runner must validate request envelopes")
    require("DISALLOWED_RAW_METADATA_KEYS" in model_provider_text, "model provider runner must guard against full-body metadata")
    require("evidence includes disallowed full-body keys" in model_provider_text, "model provider runner must reject full-body keys in live evidence")
    require(
        "usage tasks must match expected output fixtures and input fixture ids" in model_provider_text,
        "model provider runner must validate usage-log task coverage",
    )
    require(
        "briefing_item.run_id must match usage-log run_id" in model_provider_text,
        "model provider runner must validate output run ids against usage log",
    )
    require(
        "model_usage.provider must match usage-log provider" in model_provider_text,
        "model provider runner must validate output provider metadata against usage log",
    )
    require("evidence still contains TEMPLATE_ placeholder" in model_provider_text, "model provider runner must reject template evidence")
    require("may leak model provider token" in model_provider_text, "model provider runner must reject leaky evidence")
    manifest_text = read("scripts/spikes/readiness_manifest.py")
    require("--write-final-review-packet" in manifest_text, "readiness manifest helper must write a final redaction review packet")
    require("build_final_review_packet" in manifest_text, "readiness manifest helper must build final redaction review packets")
    require("Final Redaction Review Packet" in manifest_text, "readiness manifest helper must label final redaction review packets")
    require("Validation Basis" in manifest_text, "final redaction review packet must explain validation basis")
    require(
        "does not replace per-spike validators, strict preflight, or the final readiness gate" in manifest_text,
        "final redaction review packet must not imply manifest status replaces validators",
    )
    require("require_clean_tracked_worktree" in manifest_text, "readiness manifest helper must require a clean tracked worktree for final manifests")
    require("tracked_worktree_changes_from_status" in manifest_text, "readiness manifest helper must expose tracked worktree status parsing")
    readiness_text = read("scripts/check_readiness.py")
    require("load_env_file(ROOT / \".env\")" in readiness_text, "readiness gate CLI must load local .env")
    require("check_utc_iso_timestamp" in readiness_text, "live evidence manifest gate must validate UTC ISO timestamps")
    preflight_text = read("scripts/spikes/live_readiness_preflight.py")
    require("readiness.load_env_file(ROOT / \".env\")" in preflight_text, "live readiness preflight CLI must load local .env")
    require("--write-packet" in preflight_text, "live readiness preflight must support Markdown packet output")
    require("build_markdown_packet" in preflight_text, "live readiness preflight must build Markdown packets")
    require("--write-spike-packets" in preflight_text, "live readiness preflight must support per-spike packet output")
    require("build_spike_packet" in preflight_text, "live readiness preflight must build per-spike packets")
    require("helper_dry_runs_enabled" in preflight_text, "live readiness preflight must centralize helper dry-run mode selection")
    require("(dry_run or strict) and not skip_helper_dry_runs" in preflight_text, "strict live readiness preflight must run helper dry-runs by default")
    require("check_live_evidence" in preflight_text, "live readiness preflight must validate live evidence content")
    require("evidence_validation" in preflight_text, "live readiness preflight must summarize live evidence validation")
    require("DRY_RUN_ARTIFACT_FILES" in preflight_text, "live readiness preflight must define dry-run artifact inventory")
    require("dry_run_artifacts" in preflight_text, "live readiness preflight must summarize dry-run artifacts separately")
    require("final-redaction-review.md" in preflight_text, "live readiness preflight must inventory the final redaction review packet")
    require("FINAL_EVIDENCE_GROUPS" in preflight_text, "live readiness preflight must define final evidence groups")
    require("final_evidence_groups" in preflight_text, "live readiness preflight must summarize final evidence groups")
    require("Final Evidence Group Status" in preflight_text, "live readiness preflight packet must report final evidence group status")
    require("Closure gate:" in preflight_text, "live readiness spike packets must report issue closure gate status")
    require(
        "finish this group before closing the issue" in preflight_text,
        "live readiness spike packets must block issue closure for partial final evidence groups",
    )
    require("incomplete_final_groups" in preflight_text, "strict live readiness preflight must block incomplete final evidence groups")
    require(
        "complete final evidence groups" in preflight_text,
        "strict live readiness preflight must describe final evidence group completion",
    )
    require(
        "live_readiness_preflight.py --dry-run --write-packet --write-spike-packets" in preflight_text,
        "live readiness preflight packet must document per-spike dry-run packet generation",
    )
    require(
        "live_readiness_preflight.py --strict --write-packet --write-spike-packets" in preflight_text,
        "live readiness preflight packet must document per-spike strict packet generation",
    )
    for command in [
        "python3 scripts/spikes/feishu_delivery_spike.py --validate-evidence",
        "python3 scripts/spikes/model_provider_spike.py --validate-evidence",
        "python3 scripts/spikes/archive_storage_spike.py --validate-evidence",
    ]:
        require(command in preflight_text, f"live readiness preflight packet must document validation command: {command}")
    require("--validate-requests" in preflight_text, "live readiness preflight must validate model request envelopes")
    require("require_clean_worktree=args.strict" in preflight_text, "strict live readiness preflight must require a clean tracked worktree")
    test_text = read("scripts/test_live_evidence_helpers.py")
    for needle in [
        "test_readiness_load_env_file_preserves_process_env",
        "test_strict_preflight_runs_helper_dry_runs_by_default",
        "test_preflight_redacts_workspace_and_env_values",
        "test_preflight_dry_runs_write_to_temp_evidence",
        "test_preflight_reports_partial_final_evidence_groups",
        "test_preflight_packet_lists_status_without_secret_values",
        "test_preflight_writes_issue_facing_spike_packets",
        "test_spike_packet_status_blocks_partial_final_evidence_group",
        "test_feishu_dry_run_documents_group_webhook_fallback",
        "test_feishu_group_webhook_payload_redacts_signature",
        "test_preflight_reports_template_evidence_validation_failures",
        "test_model_request_envelopes_validate_metadata_only",
        "test_model_request_validation_rejects_full_body_metadata",
        "test_model_usage_log_requires_expected_tasks",
        "test_model_live_evidence_requires_usage_metadata_consistency",
        "test_model_live_evidence_rejects_full_body_keys",
        "test_model_live_evidence_rejects_template_and_leaky_content",
        "test_archive_failure_reason_redacts_private_paths",
        "test_archive_live_evidence_requires_matching_counts_and_trees",
        "test_archive_live_evidence_requires_counts_match_tree_entries",
        "test_readiness_manifest_dry_run_shape",
        "test_readiness_manifest_final_review_packet_shape",
        "test_readiness_manifest_tracks_dirty_worktree_guard",
        "test_synthetic_live_evidence_package_passes_gate",
        "test_live_evidence_manifest_rejects_stale_commit",
        "test_live_evidence_manifest_rejects_invalid_timestamps",
        "test_feishu_live_evidence_requires_archive_or_deep_dive_link",
        "test_feishu_live_evidence_requires_internal_app_request_types",
        "test_feishu_live_evidence_requires_message_ids",
        "test_preflight_accepts_synthetic_valid_evidence",
        "test_live_evidence_rejects_raw_environment_values",
    ]:
        require(needle in test_text, f"live evidence helper tests missing: {needle}")
    for needle in [
        "summary[\"dry_run_artifacts\"][\"present\"]",
        "summary[\"final_evidence_groups\"][\"feishu_delivery\"]",
        "current_git_commit()",
        "must be a valid UTC ISO timestamp ending in Z",
        "data.message_id",
        "receive_id_type must be chat_id",
        "feishu_spike.validate_evidence",
        "model_spike.validate_evidence",
        "Model usage log tasks must match expected output fixtures and input fixture ids",
        "briefing_item.run_id must match usage-log run_id",
        "model_usage.provider must match usage-log provider",
        "must not include full-body keys",
        "archive_spike.validate_evidence",
        "local and remote tree listings must match",
        "file_count must match local tree file entries",
        "final-redaction-review.md",
        "Validation Basis",
        "does not replace per-spike validators, strict preflight, or the final readiness gate",
        "They do not count as final live evidence.",
        "some final evidence files exist",
        "Closure gate: blocked",
        "finish this group before closing the issue",
        "preflight.has_missing_required(summary) is True",
        "helper_dry_runs_enabled",
        "Strict mode requires a clean tracked worktree",
        "complete final evidence groups",
        "live_readiness_preflight.py --dry-run --write-packet --write-spike-packets",
        "live_readiness_preflight.py --strict --write-packet --write-spike-packets",
        "python3 scripts/spikes/feishu_delivery_spike.py --validate-evidence",
        "python3 scripts/spikes/model_provider_spike.py --validate-evidence",
        "python3 scripts/spikes/archive_storage_spike.py --validate-evidence",
    ]:
        require(needle in test_text, f"live evidence helper tests missing dry-run inventory assertion: {needle}")
    return ["spike runners: Feishu fallback guardrails, archive redaction, model-provider request guardrails, readiness-manifest, final redaction review packet, preflight packet helper with live evidence validation, dry-run artifact inventory, final evidence group status, per-spike packets, and live evidence tests present"]


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


def check_readiness_action_packet_helper() -> list[str]:
    text = read("scripts/readiness_action_packet.py")
    test_text = read("scripts/test_readiness_action_packet.py")
    for needle in [
        "readiness-action-packet.md",
        "external-input-request.md",
        "github-update-packet.md",
        "live-readiness-packet.md",
        "live-spike-packets",
        "source-owner-reviews/index.md",
        "source-owner-reviews/worksheet.md",
        "source-owner-reviews/batch-plan.md",
        "source-owner-reviews/request-packet.md",
        "mvp-issue-packets",
        "readiness-manifest.json",
        "final-redaction-review.md",
        "EXTERNAL_INPUT_REQUESTS",
        "External Input Request Checklist",
        "External Input Request Packet",
        "GitHub Update Packet",
        "Label Guardrails",
        "Copy-Safe Issue Comments",
        "external_input_request_rows",
        "build_external_input_request_packet",
        "write_external_input_request_packet",
        "build_github_update_packet",
        "write_github_update_packet",
        "Required evidence files",
        "Briefing Host secret store or local `.env`; never GitHub.",
        "GitHub Issue Links",
        "MVP Issue Unlock Matrix",
        "MVP_ISSUE_UNLOCKS",
        "mvp_issue_unlock_rows",
        "mvp_issue_statuses",
        "evidence_group",
        "final_group_status",
        "incomplete final evidence group",
        "global_readiness_gate",
        "Global readiness gate",
        "write_source_owner_packets",
        "--write-source-owner-packets",
        "write_mvp_issue_packets",
        "--write-mvp-issue-packets",
        "batch_plan_path",
        "https://github.com/KG9750/TechNews/issues/3",
        "build_packet",
        "source_owner_summary",
        "python3 scripts/check_readiness.py --require-live --require-evidence",
        "python3 scripts/spikes/feishu_delivery_spike.py --validate-evidence",
        "python3 scripts/spikes/model_provider_spike.py --validate-evidence",
        "python3 scripts/spikes/archive_storage_spike.py --validate-evidence",
        "--write-spike-packets",
        "--write-final-review-packet",
        "python3 scripts/check_readiness.py --require-github",
        "live_preflight.readiness.load_env_file(ROOT / \".env\")",
    ]:
        require(needle in text, f"readiness action packet helper missing: {needle}")
    for needle in [
        "test_action_packet_summarizes_blockers_without_secret_values",
        "test_github_update_packet_names_label_guardrails_without_secret_values",
        "test_action_packet_blocks_unlocks_on_partial_final_evidence_group",
        "test_action_packet_writes_markdown",
        "test_source_owner_packets_can_be_written_from_action_packet",
        "test_mvp_issue_packets_are_written_with_label_guardrails",
        "MVP Issue Unlock Matrix",
        "Final evidence group",
        "Feishu delivery spike: final evidence group partial",
        "Global readiness gate: blocked",
        "External Input Request Packet",
        "GitHub Update Packet",
        "Label Guardrails",
        "Required evidence files",
        "External Input Request Checklist",
        "FEISHU_APP_ID, FEISHU_APP_SECRET",
        "ARCHIVE_LOCAL_ROOT, ARCHIVE_SYNC_TARGET",
        "source-owner-reviews/batch-plan.md",
        "source-owner-reviews/request-packet.md",
        "--write-source-owner-packets",
        "mvp-issue-packets",
        "github-update-packet.md",
        "final-redaction-review.md",
        "python3 scripts/spikes/feishu_delivery_spike.py --validate-evidence",
        "python3 scripts/spikes/model_provider_spike.py --validate-evidence",
        "python3 scripts/spikes/archive_storage_spike.py --validate-evidence",
    ]:
        require(needle in test_text, f"readiness action packet tests missing: {needle}")
    for path in ["docs/readiness-gate-status.md", "docs/PRE-DEVELOPMENT-PLAN.md", "docs/live-spike-evidence-runbook.md"]:
        require("scripts/readiness_action_packet.py" in read(path), f"{path} must document readiness action packet helper")
        require("--write-mvp-issue-packets" in read(path), f"{path} must document MVP issue packet generation")
        require("--write-source-owner-packets" in read(path), f"{path} must document source-owner packet generation")
    for path in ["docs/readiness-gate-status.md", "docs/live-spike-evidence-runbook.md"]:
        require("--write-spike-packets" in read(path), f"{path} must document per-spike packet generation")
    return ["readiness action packet helper: blocked-workstream, MVP issue unlock, GitHub update, and per-issue triage packets with regression tests present"]


def check_readiness_ci_workflow() -> list[str]:
    text = read(".github/workflows/pre-development-readiness.yml")
    for needle in [
        "actions/checkout@v6",
        "actions/setup-python@v6",
        "python scripts/check_readiness.py",
        "python -m py_compile",
        "scripts/spikes/readiness_manifest.py",
        "scripts/spikes/live_readiness_preflight.py",
        "scripts/test_live_evidence_helpers.py",
        "scripts/readiness_action_packet.py",
        "scripts/test_readiness_action_packet.py",
        "scripts/source_owner_review_decision.py",
        "scripts/test_source_owner_review_decision.py",
        "--require-evidence --evidence-root fixtures/live-evidence-templates",
        "Expected template evidence validation to fail",
        "--require-evidence --evidence-root \"$root\"",
        "fixtures/live-evidence-negative/leaky-feishu",
        "fixtures/live-evidence-negative/leaky-model-provider",
        "fixtures/live-evidence-negative/leaky-archive-storage",
        "Expected leaky evidence validation to fail",
    ]:
        require(needle in text, f"readiness CI workflow missing: {needle}")
    require("--require-live" not in text, "readiness CI must not require live external credentials")
    require("--require-github" not in text, "readiness CI must not require GitHub tracker access")
    return ["readiness CI workflow: Node 24-native actions, local gate, script compile, template-negative, and redaction-negative checks present"]


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
    accepted_count = 0
    for path, expectations in REQUIRED_ADRS.items():
        text = read(path)
        require(text.startswith("# "), f"{path} missing title")
        status_match = re.search(r"^Status:\s+([a-z-]+)\s*$", text, re.MULTILINE)
        require(status_match is not None, f"{path} missing Status")
        status = status_match.group(1)
        require(status == "accepted", f"{path} status must be accepted")
        accepted_count += 1
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
        f"required ADRs: accepted={accepted_count}",
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


def current_git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def check_utc_iso_timestamp(value: object, label: str, failures: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        failures.append(f"{label} must be a non-empty UTC ISO timestamp")
        return
    if not value.endswith("Z"):
        failures.append(f"{label} must be a valid UTC ISO timestamp ending in Z")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        failures.append(f"{label} must be a valid UTC ISO timestamp ending in Z")


def tracked_worktree_changes_from_status(status_output: str) -> list[str]:
    return [line for line in status_output.splitlines() if line.strip()]


def tracked_worktree_changes() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ["unable to inspect tracked git worktree status"]
    return tracked_worktree_changes_from_status(result.stdout)


def check_clean_tracked_worktree_for_live_evidence(failures: list[str]) -> None:
    changes = tracked_worktree_changes()
    if not changes:
        return
    preview = ", ".join(changes[:5])
    if len(changes) > 5:
        preview += ", ..."
    failures.append(f"Live evidence manifest requires a clean tracked worktree before final gate: {preview}")


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
        "user request": evidence_dir / "user-request.redacted.json",
        "user response": evidence_dir / "user-response.redacted.json",
        "group request": evidence_dir / "group-request.redacted.json",
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
    for label, path, expected_receive_id_type in [
        ("user", required_files["user request"], "open_id"),
        ("group", required_files["group request"], "chat_id"),
    ]:
        payload = load_json_path(path)
        if payload.get("path") != "internal_app_bot":
            failures.append(f"Feishu {label} request path must be internal_app_bot")
        if payload.get("receive_id_type") != expected_receive_id_type:
            failures.append(f"Feishu {label} request receive_id_type must be {expected_receive_id_type}")
        body = payload.get("body", {})
        if not isinstance(body, dict):
            failures.append(f"Feishu {label} request body must be an object")
            continue
        if body.get("msg_type") != "interactive":
            failures.append(f"Feishu {label} request msg_type must be interactive")
        if not body.get("receive_id"):
            failures.append(f"Feishu {label} request must include redacted receive_id")
        content = body.get("content")
        if not isinstance(content, str) or not content.strip():
            failures.append(f"Feishu {label} request must include card content")
        else:
            try:
                json.loads(content)
            except json.JSONDecodeError:
                failures.append(f"Feishu {label} request content must be JSON")
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
            continue
        message_id = data.get("message_id")
        if not isinstance(message_id, str) or not message_id.strip():
            failures.append(f"Feishu {label} response must include data.message_id")
    rendered = required_files["rendered message"].read_text(encoding="utf-8")
    for needle in ["Source", "置信提示"]:
        if needle not in rendered:
            failures.append(f"Feishu rendered message missing {needle}")
    if not any(needle in rendered for needle in ["Archive", "Deep-Dive", "Deep Dive", "归档"]):
        failures.append("Feishu rendered message missing Archive or Deep-Dive link")
    if not failures:
        passed.append("Feishu live evidence: internal-app user/group requests and delivery responses with archive/deep-dive link present")
    return passed, missing, failures


def check_live_evidence_redaction_negative_fixture() -> list[str]:
    fixture_specs = [
        ("Feishu", ROOT / "fixtures/live-evidence-negative/leaky-feishu", check_feishu_live_evidence),
        ("Model", ROOT / "fixtures/live-evidence-negative/leaky-model-provider", check_model_live_evidence),
        ("Archive", ROOT / "fixtures/live-evidence-negative/leaky-archive-storage", check_archive_live_evidence),
    ]
    total_leaks = 0
    fixture_summaries = []
    for label, evidence_root, checker in fixture_specs:
        _, missing, failures = checker(evidence_root)
        require(not missing, f"live evidence redaction negative fixture must include all {label} files")
        leak_failures = [failure for failure in failures if "may leak" in failure]
        require(leak_failures, f"live evidence redaction negative fixture must fail on {label} sensitive leak patterns")
        total_leaks += len(leak_failures)
        fixture_summaries.append(f"{label.lower()}={len(leak_failures)}")
    return [f"live evidence redaction negative fixtures: {total_leaks} leak checks fire ({', '.join(fixture_summaries)})"]


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
    local_file_count = int(payload.get("local_archive", {}).get("file_count") or 0)
    remote_file_count = int(payload.get("remote_sync", {}).get("file_count") or 0)
    if local_file_count <= 0:
        failures.append("Archive live evidence local_archive.file_count must be > 0")
    if remote_file_count <= 0:
        failures.append("Archive live evidence remote_sync.file_count must be > 0")
    if local_file_count > 0 and remote_file_count > 0 and local_file_count != remote_file_count:
        failures.append("Archive live evidence local and remote file_count values must match")
    tree_lines: dict[str, list[str]] = {}
    for label, path in [
        ("local tree", evidence_dir / "local-tree.txt"),
        ("remote tree", evidence_dir / "remote-tree.txt"),
    ]:
        if not path.exists():
            missing.append(f"Archive live evidence missing {label}: {path}")
        else:
            check_live_evidence_file(path, failures, f"Archive live evidence {label}")
            lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if not lines:
                failures.append(f"Archive live evidence {label} must list at least one file")
            tree_lines[label] = lines
    if tree_lines.get("local tree") and local_file_count > 0:
        local_tree_file_count = len([line for line in tree_lines["local tree"] if not line.endswith("/")])
        if local_file_count != local_tree_file_count:
            failures.append("Archive live evidence local_archive.file_count must match local tree file entries")
    if tree_lines.get("remote tree") and remote_file_count > 0:
        remote_tree_file_count = len([line for line in tree_lines["remote tree"] if not line.endswith("/")])
        if remote_file_count != remote_tree_file_count:
            failures.append("Archive live evidence remote_sync.file_count must match remote tree file entries")
    if tree_lines.get("local tree") and tree_lines.get("remote tree") and tree_lines["local tree"] != tree_lines["remote tree"]:
        failures.append("Archive live evidence local and remote tree listings must match")
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
    outputs: list[tuple[Path, dict]] = []
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
        outputs.append((path, payload))
        disallowed = sorted(nested_keys(payload) & DISALLOWED_FULL_BODY_KEYS)
        if disallowed:
            failures.append(f"{path}: model live evidence must not include full-body keys: {', '.join(disallowed)}")
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
        if usage.get("task_type") != "briefing_item_generation":
            failures.append(f"{path}: model_usage.task_type must be briefing_item_generation")
    if not usage_path.exists():
        missing.append(f"Model live evidence missing usage log: {usage_path}")
    else:
        check_live_evidence_file(usage_path, failures, "Model live evidence usage log")
        usage_log = load_json_path(usage_path)
        disallowed = sorted(nested_keys(usage_log) & DISALLOWED_FULL_BODY_KEYS)
        if disallowed:
            failures.append(f"{usage_path}: model usage log must not include full-body keys: {', '.join(disallowed)}")
        if usage_log.get("provider") in {"fixture", None, ""}:
            failures.append("Model usage log provider must identify a live provider")
        if usage_log.get("model") in {"not_called", None, ""}:
            failures.append("Model usage log model must identify a live model")
        tasks = usage_log.get("tasks", [])
        if len(tasks) != 3:
            failures.append("Model usage log must include three tasks")
        expected_tasks = {
            f"outputs/{profile}.json": fixture_id
            for profile, fixture_id in MODEL_OUTPUT_PROFILES.items()
        }
        actual_tasks = {
            task.get("output_fixture"): task.get("input_fixture_id")
            for task in tasks
            if task.get("output_fixture")
        }
        if actual_tasks != expected_tasks:
            failures.append("Model usage log tasks must match expected output fixtures and input fixture ids")
        for task in tasks:
            if task.get("task_type") != "briefing_item_generation":
                failures.append("Model usage log every task task_type must be briefing_item_generation")
            if int(task.get("request_count") or 0) <= 0:
                failures.append("Model usage log every task request_count must be > 0")
            if "latency_ms" not in task:
                failures.append("Model usage log every task must include latency_ms")
        for path, output in outputs:
            item = output.get("briefing_item", {})
            usage = output.get("model_usage", {})
            if item.get("run_id") != usage_log.get("run_id"):
                failures.append(f"{path}: briefing_item.run_id must match usage-log run_id")
            if usage.get("provider") != usage_log.get("provider"):
                failures.append(f"{path}: model_usage.provider must match usage-log provider")
            if usage.get("model") != usage_log.get("model"):
                failures.append(f"{path}: model_usage.model must match usage-log model")
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


def check_live_evidence_manifest(
    evidence_root: Path,
    require_clean_worktree: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    path = evidence_root / "readiness-manifest.json"
    missing: list[str] = []
    failures: list[str] = []
    passed: list[str] = []
    if not path.exists():
        missing.append(f"Live evidence manifest missing: {path}")
        return passed, missing, failures

    if require_clean_worktree:
        check_clean_tracked_worktree_for_live_evidence(failures)
    check_live_evidence_file(path, failures, "Live evidence manifest")
    manifest = load_json_path(path)
    if manifest.get("repository") != EXPECTED_GITHUB_REPO:
        failures.append(f"Live evidence manifest repository must be {EXPECTED_GITHUB_REPO}")
    for field in ["readiness_evidence_id", "generated_at", "commit", "reviewed_by"]:
        if not manifest.get(field):
            failures.append(f"Live evidence manifest missing {field}")
    if manifest.get("generated_at"):
        check_utc_iso_timestamp(manifest.get("generated_at"), "Live evidence manifest generated_at", failures)
    manifest_commit = manifest.get("commit")
    head_commit = current_git_commit()
    if manifest_commit and head_commit and manifest_commit != head_commit:
        failures.append("Live evidence manifest commit must match current git HEAD")
    redaction_review = manifest.get("redaction_review", {})
    if not isinstance(redaction_review, dict) or not redaction_review.get("reviewed_at") or not redaction_review.get("notes"):
        failures.append("Live evidence manifest redaction_review must include reviewed_at and notes")
    elif redaction_review.get("reviewed_at"):
        check_utc_iso_timestamp(redaction_review.get("reviewed_at"), "Live evidence manifest redaction_review.reviewed_at", failures)

    feishu = require_manifest_files(
        manifest,
        evidence_root,
        "feishu_delivery",
        {
            "feishu-delivery/user-request.redacted.json",
            "feishu-delivery/user-response.redacted.json",
            "feishu-delivery/group-request.redacted.json",
            "feishu-delivery/group-response.redacted.json",
            "feishu-delivery/rendered-message.md",
        },
        missing,
        failures,
    )
    requirements = set(feishu.get("requirements", []))
    for requirement in [
        "one_user_delivery",
        "one_group_delivery",
        "internal_app_user_open_id_request",
        "internal_app_group_chat_id_request",
        "source_line_present",
        "confidence_notice_present",
    ]:
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


def check_live_evidence(
    evidence_root: Path,
    require_clean_worktree: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    passed: list[str] = []
    missing: list[str] = []
    failures: list[str] = []
    manifest_passed, manifest_missing, manifest_failures = check_live_evidence_manifest(
        evidence_root,
        require_clean_worktree=require_clean_worktree,
    )
    passed.extend(manifest_passed)
    missing.extend(manifest_missing)
    failures.extend(manifest_failures)
    for checker in [check_feishu_live_evidence, check_archive_live_evidence, check_model_live_evidence]:
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
        check_source_owner_review_decision_helper,
        check_taxonomy_template,
        check_briefing_style_guide,
        check_golden_samples,
        check_archive_fixture,
        check_model_fixtures,
        check_feishu_fixture,
        check_spike_runners,
        check_feishu_runner_redaction,
        check_readiness_action_packet_helper,
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
        evidence_ok, evidence_missing, evidence_failures = check_live_evidence(
            evidence_root,
            require_clean_worktree=True,
        )
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
    load_env_file(ROOT / ".env")
    return run(
        require_live=args.require_live,
        require_evidence=args.require_evidence,
        require_github=args.require_github,
        evidence_root=Path(args.evidence_root),
    )


if __name__ == "__main__":
    raise SystemExit(main())
