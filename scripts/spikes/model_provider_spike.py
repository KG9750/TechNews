#!/usr/bin/env python3
"""Throwaway Model Provider spike helper.

This script does not call a model provider. The first provider/API is still a
product decision, so the helper creates provider-neutral request envelopes and
validates redacted live evidence after the calls are made by the chosen tool.
Generated evidence is written under evidence/model-provider/ and should not be
committed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GOLDEN_SAMPLES_PATH = ROOT / "fixtures/golden-samples/items.json"
PROMPT_CONTRACT_PATH = ROOT / "fixtures/model-provider/prompt-contract.md"
DEFAULT_EVIDENCE_DIR = ROOT / "evidence/model-provider"
RUN_ID = "run_2026-06-01_model_provider_spike"

PROFILES = [
    ("high-confidence-news", "sample-001-openai-gpt-4o"),
    ("low-confidence-news", "sample-020-single-source-leak"),
    ("academic-paper", "sample-018-rt-2"),
]
DISALLOWED_RAW_METADATA_KEYS = {
    "article_body",
    "body",
    "content",
    "full_text",
    "html",
    "text",
    "transcript",
}
SENSITIVE_VALUE_PATTERNS = [
    re.compile(r"Authorization\s*[:=]\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Bearer\s+(?!REDACTED\b)[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"/Users/[^/\s\"]+"),
    re.compile(r"(?<![A-Za-z0-9_./-])/private/"),
    re.compile(r"Mobile Documents/com~apple~CloudDocs"),
]
SENSITIVE_ENV_NAMES = [
    "MODEL_API_KEY",
]


class SpikeError(Exception):
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


def slug(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def load_golden_samples() -> dict[str, dict]:
    items = json.loads(GOLDEN_SAMPLES_PATH.read_text(encoding="utf-8"))
    return {item["fixture_id"]: item for item in items}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_evidence_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_evidence_redaction(path: Path) -> None:
    text = read_evidence_text(path)
    if "TEMPLATE_" in text:
        raise SpikeError(f"{path}: evidence still contains TEMPLATE_ placeholder")
    for pattern in SENSITIVE_VALUE_PATTERNS:
        if pattern.search(text):
            raise SpikeError(f"{path}: evidence may leak model provider token, authorization header, or private path")
    for env_name in SENSITIVE_ENV_NAMES:
        value = os.environ.get(env_name, "")
        if len(value) >= 8 and value in text:
            raise SpikeError(f"{path}: evidence contains raw environment value {env_name}")


def build_candidate_item(fixture: dict) -> dict:
    metadata = fixture["raw_source_metadata"]
    classification = fixture["expected_classification"]
    expected_candidate = fixture["expected_candidate_item"]
    candidate_slug = slug(fixture["fixture_id"].replace("sample-", ""))
    return {
        "id": f"cand_{candidate_slug}",
        "run_id": RUN_ID,
        "source_id": f"fixture-{fixture['fixture_id']}",
        "source_type": expected_candidate["source_type"],
        "source_name": metadata["source_name"],
        "original_title": metadata["original_title"],
        "source_url": metadata["source_url"],
        "original_source_anchor": {
            "source_name": metadata["source_name"],
            "original_title": metadata["original_title"],
            "source_url": metadata["source_url"],
        },
        "dedupe_key": f"fixture|{metadata['source_url']}",
        "event_key": None,
        "published_at": metadata.get("published_at"),
        "discovered_at": "2026-06-01T08:00:00Z",
        "language": "en",
        "section_hints": [classification["section"]],
        "source_media": None,
        "eligibility_state": expected_candidate["eligibility_state"],
        "eligibility_notes": fixture.get("fixture_note", "Golden sample metadata-only fixture."),
        "raw_metadata": {
            "fixture_id": fixture["fixture_id"],
            "scenario_tags": fixture.get("scenario_tags", []),
            "raw_metadata_only": expected_candidate["raw_metadata_only"],
        },
    }


def build_request_envelope(profile_name: str, fixture: dict) -> dict:
    return {
        "run_id": RUN_ID,
        "profile": profile_name,
        "input_fixture_id": fixture["fixture_id"],
        "task_type": "briefing_item_generation",
        "system_instruction": (
            "Generate concise Chinese technology briefing items from metadata-only CandidateItems. "
            "Preserve the original source anchor exactly. Do not invent citations, source media, "
            "publication facts, funding details, benchmark results, or article body content."
        ),
        "candidate_item": build_candidate_item(fixture),
        "expected_classification": fixture["expected_classification"],
        "expected_selection": fixture["expected_selection"],
        "expected_push_briefing_shape": fixture["expected_push_briefing_shape"],
        "expected_section_options": [
            "AI",
            "Software",
            "Hardware",
            "Embodied Intelligence",
            "Academic Progress",
            "Technology Industry Progress",
        ],
        "style_rules": {
            "title_zh": "one sentence",
            "bullets_zh": "three or four compact bullets",
            "confidence_notice_required_when": ["medium", "low"],
            "no_full_article_body_storage": True,
            "do_not_invent_media_or_citations": True,
        },
        "output_contract": {
            "briefing_item": "required BriefingItem fields from docs/schemas/minimal-contracts.md",
            "model_usage": "provider, model, task type, request count, token usage when available, latency, failure reason",
            "guardrail_notes": "uncertainty, missing metadata, and source/media restrictions",
        },
    }


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


def validate_request_envelope(envelope: dict, fixture: dict) -> None:
    if envelope.get("input_fixture_id") != fixture["fixture_id"]:
        raise SpikeError(f"{envelope.get('profile', 'request')}: input_fixture_id must be {fixture['fixture_id']}")
    if envelope.get("run_id") != RUN_ID:
        raise SpikeError(f"{envelope.get('profile', 'request')}: run_id must be {RUN_ID}")
    if envelope.get("task_type") != "briefing_item_generation":
        raise SpikeError(f"{envelope.get('profile', 'request')}: task_type must be briefing_item_generation")

    candidate = envelope.get("candidate_item")
    if not isinstance(candidate, dict):
        raise SpikeError(f"{envelope.get('profile', 'request')}: candidate_item is required")
    expected_anchor = fixture["raw_source_metadata"]
    anchor = candidate.get("original_source_anchor", {})
    for field in ["source_name", "original_title", "source_url"]:
        if candidate.get(field) != expected_anchor[field]:
            raise SpikeError(f"{envelope['profile']}: candidate_item.{field} changed from fixture metadata")
        if anchor.get(field) != expected_anchor[field]:
            raise SpikeError(f"{envelope['profile']}: original_source_anchor.{field} changed from fixture metadata")

    raw_metadata = candidate.get("raw_metadata", {})
    if raw_metadata.get("raw_metadata_only") is not True:
        raise SpikeError(f"{envelope['profile']}: raw_metadata.raw_metadata_only must be true")
    disallowed = sorted(nested_keys(raw_metadata) & DISALLOWED_RAW_METADATA_KEYS)
    if disallowed:
        raise SpikeError(f"{envelope['profile']}: raw_metadata includes disallowed full-body keys: {', '.join(disallowed)}")
    if candidate.get("source_media") is not None:
        raise SpikeError(f"{envelope['profile']}: model spike request must not include source_media")

    style_rules = envelope.get("style_rules", {})
    if style_rules.get("no_full_article_body_storage") is not True:
        raise SpikeError(f"{envelope['profile']}: style_rules.no_full_article_body_storage must be true")
    if style_rules.get("do_not_invent_media_or_citations") is not True:
        raise SpikeError(f"{envelope['profile']}: style_rules.do_not_invent_media_or_citations must be true")


def dry_run(evidence_dir: Path) -> int:
    samples = load_golden_samples()
    request_dir = evidence_dir / "requests"
    request_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PROMPT_CONTRACT_PATH, evidence_dir / "prompt-contract.md")
    for profile_name, fixture_id in PROFILES:
        envelope = build_request_envelope(profile_name, samples[fixture_id])
        validate_request_envelope(envelope, samples[fixture_id])
        write_json(request_dir / f"{profile_name}.request.json", envelope)
    write_json(
        evidence_dir / "dry-run-summary.json",
        {
            "run_id": RUN_ID,
            "dry_run": True,
            "generated_at_epoch": int(time.time()),
            "request_count": len(PROFILES),
            "request_validation": "passed",
            "next_step": "Run these request envelopes with the chosen provider and place redacted outputs under evidence/model-provider/outputs/.",
        },
    )
    print(f"DRY-RUN wrote validated model request envelopes to {evidence_dir}")
    return 0


def validate_requests(evidence_dir: Path) -> int:
    samples = load_golden_samples()
    request_dir = evidence_dir / "requests"
    if not request_dir.exists():
        raise SpikeError(f"missing request directory: {request_dir}")
    for profile_name, fixture_id in PROFILES:
        path = request_dir / f"{profile_name}.request.json"
        envelope = json.loads(path.read_text(encoding="utf-8"))
        validate_request_envelope(envelope, samples[fixture_id])
    print(f"Model request envelopes validate as metadata-only: {request_dir}")
    return 0


def validate_briefing_output(path: Path, fixture: dict, profile_name: str) -> None:
    check_evidence_redaction(path)
    payload = json.loads(read_evidence_text(path))
    if payload.get("input_fixture_id") != fixture["fixture_id"]:
        raise SpikeError(f"{path}: input_fixture_id must be {fixture['fixture_id']}")
    item = payload.get("briefing_item")
    if not isinstance(item, dict):
        raise SpikeError(f"{path}: missing briefing_item object")
    required_fields = [
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
    missing = [field for field in required_fields if field not in item]
    if missing:
        raise SpikeError(f"{path}: missing briefing_item fields: {', '.join(missing)}")
    if not 3 <= len(item["bullets_zh"]) <= 4:
        raise SpikeError(f"{path}: bullets_zh must contain 3-4 bullets")
    expected_anchor = fixture["raw_source_metadata"]
    anchor = item["original_source_anchor"]
    for field in ["source_name", "original_title", "source_url"]:
        if anchor.get(field) != expected_anchor[field]:
            raise SpikeError(f"{path}: original_source_anchor.{field} changed")
    if item["confidence_level"] in {"medium", "low"} and not item.get("confidence_notice"):
        raise SpikeError(f"{path}: confidence_notice required for {item['confidence_level']} confidence")
    if profile_name == "low-confidence-news" and item["confidence_level"] != "low":
        raise SpikeError(f"{path}: low-confidence fixture must remain low")
    usage = payload.get("model_usage", {})
    if usage.get("provider") in {"fixture", None, ""}:
        raise SpikeError(f"{path}: model_usage.provider must identify a live provider")
    if usage.get("model") in {"not_called", None, ""}:
        raise SpikeError(f"{path}: model_usage.model must identify a live model")
    if int(usage.get("request_count") or 0) <= 0:
        raise SpikeError(f"{path}: model_usage.request_count must be > 0")
    if usage.get("failure_reason"):
        raise SpikeError(f"{path}: successful live output must not include failure_reason")


def validate_usage_log(path: Path) -> None:
    check_evidence_redaction(path)
    payload = json.loads(read_evidence_text(path))
    if payload.get("provider") in {"fixture", None, ""}:
        raise SpikeError(f"{path}: provider must identify a live provider")
    if payload.get("model") in {"not_called", None, ""}:
        raise SpikeError(f"{path}: model must identify a live model")
    tasks = payload.get("tasks", [])
    if len(tasks) != 3:
        raise SpikeError(f"{path}: expected three usage tasks")
    expected_tasks = {f"outputs/{profile_name}.json": fixture_id for profile_name, fixture_id in PROFILES}
    actual_tasks = {
        task.get("output_fixture"): task.get("input_fixture_id")
        for task in tasks
        if task.get("output_fixture")
    }
    if actual_tasks != expected_tasks:
        raise SpikeError(f"{path}: usage tasks must match expected output fixtures and input fixture ids")
    for task in tasks:
        if task.get("task_type") != "briefing_item_generation":
            raise SpikeError(f"{path}: every task task_type must be briefing_item_generation")
        if int(task.get("request_count") or 0) <= 0:
            raise SpikeError(f"{path}: every task request_count must be > 0")
        if "latency_ms" not in task:
            raise SpikeError(f"{path}: every task must include latency_ms")


def validate_evidence(evidence_dir: Path) -> int:
    load_env_file(ROOT / ".env")
    samples = load_golden_samples()
    output_dir = evidence_dir / "outputs"
    if not output_dir.exists():
        raise SpikeError(f"missing live output directory: {output_dir}")
    for profile_name, fixture_id in PROFILES:
        validate_briefing_output(output_dir / f"{profile_name}.json", samples[fixture_id], profile_name)
    validate_usage_log(evidence_dir / "usage-log.json")
    print(f"LIVE model evidence validates: {evidence_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Generate provider-neutral request envelopes.")
    parser.add_argument("--validate-requests", action="store_true", help="Validate generated request envelopes before live provider calls.")
    parser.add_argument("--validate-evidence", action="store_true", help="Validate redacted live provider evidence.")
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    args = parser.parse_args()

    evidence_dir = Path(args.evidence_dir)
    try:
        if args.dry_run:
            return dry_run(evidence_dir)
        if args.validate_requests:
            return validate_requests(evidence_dir)
        if args.validate_evidence:
            return validate_evidence(evidence_dir)
        print("Choose --dry-run, --validate-requests, or --validate-evidence")
        return 1
    except (FileNotFoundError, json.JSONDecodeError, SpikeError) as error:
        print(f"ERROR {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
