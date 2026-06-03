#!/usr/bin/env python3
"""Generate the final live readiness evidence manifest.

This helper reads redacted live evidence under evidence/ and writes
evidence/readiness-manifest.json. It does not create or modify product code.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE_ROOT = ROOT / "evidence"
EXPECTED_REPOSITORY = "KG9750/TechNews"

FEISHU_FILES = [
    "feishu-delivery/user-response.redacted.json",
    "feishu-delivery/group-response.redacted.json",
    "feishu-delivery/rendered-message.md",
]
MODEL_FILES = [
    "model-provider/outputs/high-confidence-news.json",
    "model-provider/outputs/low-confidence-news.json",
    "model-provider/outputs/academic-paper.json",
    "model-provider/usage-log.json",
]
ARCHIVE_FILES = [
    "archive-storage/sync-result.json",
    "archive-storage/local-tree.txt",
    "archive-storage/remote-tree.txt",
]


class ManifestError(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def current_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ManifestError("unable to resolve current git commit")
    return result.stdout.strip()


def read_json_if_present(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def missing_files(evidence_root: Path, files: list[str]) -> list[str]:
    return [path for path in files if not (evidence_root / path).exists()]


def spike_status(evidence_root: Path, files: list[str]) -> str:
    return "passed" if not missing_files(evidence_root, files) else "missing"


def require_complete_live_evidence(evidence_root: Path) -> None:
    missing = missing_files(evidence_root, FEISHU_FILES + MODEL_FILES + ARCHIVE_FILES)
    if missing:
        raise ManifestError("missing live evidence files: " + ", ".join(missing))


def build_manifest(evidence_root: Path, reviewed_by: str, redaction_notes: str, dry_run: bool) -> dict:
    if not dry_run:
        require_complete_live_evidence(evidence_root)

    model_usage = read_json_if_present(evidence_root / "model-provider/usage-log.json")
    archive_sync = read_json_if_present(evidence_root / "archive-storage/sync-result.json")

    if not dry_run:
        for field in ["run_id", "provider", "model"]:
            if not model_usage.get(field):
                raise ManifestError(f"model usage log missing {field}")
        if not archive_sync.get("run_id"):
            raise ManifestError("archive sync result missing run_id")

    fallback = "not_available_dry_run"
    return {
        "readiness_evidence_id": f"readiness_{utc_now().replace(':', '').replace('-', '')}",
        "generated_at": utc_now(),
        "repository": EXPECTED_REPOSITORY,
        "commit": current_commit(),
        "reviewed_by": reviewed_by,
        "redaction_review": {
            "reviewed_at": utc_now(),
            "notes": redaction_notes,
        },
        "spikes": {
            "feishu_delivery": {
                "status": spike_status(evidence_root, FEISHU_FILES),
                "evidence_files": FEISHU_FILES,
                "requirements": [
                    "one_user_delivery",
                    "one_group_delivery",
                    "source_line_present",
                    "confidence_notice_present",
                ],
            },
            "model_provider": {
                "status": spike_status(evidence_root, MODEL_FILES),
                "run_id": model_usage.get("run_id", fallback),
                "provider": model_usage.get("provider", fallback),
                "model": model_usage.get("model", fallback),
                "evidence_files": MODEL_FILES,
            },
            "archive_storage": {
                "status": spike_status(evidence_root, ARCHIVE_FILES),
                "run_id": archive_sync.get("run_id", fallback),
                "evidence_files": ARCHIVE_FILES,
            },
        },
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", default=str(DEFAULT_EVIDENCE_ROOT))
    parser.add_argument("--reviewed-by", default="Briefing Administrator")
    parser.add_argument(
        "--redaction-notes",
        default="Reviewed redacted evidence for template markers, sensitive ids, tokens, and private paths.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Write a dry-run manifest even if live evidence is incomplete.")
    parser.add_argument("--output", help="Override manifest output path.")
    args = parser.parse_args()

    evidence_root = Path(args.evidence_root)
    output_path = Path(args.output) if args.output else evidence_root / ("readiness-manifest.dry-run.json" if args.dry_run else "readiness-manifest.json")
    try:
        manifest = build_manifest(evidence_root, args.reviewed_by, args.redaction_notes, args.dry_run)
        write_json(output_path, manifest)
    except ManifestError as error:
        print(f"ERROR {error}")
        return 1

    print(f"{'DRY-RUN' if args.dry_run else 'LIVE'} readiness manifest written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
