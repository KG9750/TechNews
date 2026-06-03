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
    "feishu-delivery/user-request.redacted.json",
    "feishu-delivery/user-response.redacted.json",
    "feishu-delivery/group-request.redacted.json",
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
FINAL_REVIEW_PACKET = "final-redaction-review.md"
FINAL_EVIDENCE_FILES = [
    "readiness-manifest.json",
    *FEISHU_FILES,
    *MODEL_FILES,
    *ARCHIVE_FILES,
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
        raise ManifestError("unable to inspect tracked git worktree status")
    return tracked_worktree_changes_from_status(result.stdout)


def require_clean_tracked_worktree() -> None:
    changes = tracked_worktree_changes()
    if not changes:
        return
    preview = ", ".join(changes[:5])
    if len(changes) > 5:
        preview += ", ..."
    raise ManifestError(f"tracked worktree must be clean before writing final readiness manifest: {preview}")


def read_json_if_present(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def missing_files(evidence_root: Path, files: list[str]) -> list[str]:
    return [path for path in files if not (evidence_root / path).exists()]


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


def evidence_file_rows(evidence_root: Path) -> list[str]:
    rows = []
    for path in FINAL_EVIDENCE_FILES:
        status = "present" if (evidence_root / path).exists() else "missing"
        rows.append(f"- `{path}`: {status}")
    return rows


def spike_status(evidence_root: Path, files: list[str]) -> str:
    return "passed" if not missing_files(evidence_root, files) else "missing"


def require_complete_live_evidence(evidence_root: Path) -> None:
    missing = missing_files(evidence_root, FEISHU_FILES + MODEL_FILES + ARCHIVE_FILES)
    if missing:
        raise ManifestError("missing live evidence files: " + ", ".join(missing))


def build_manifest(evidence_root: Path, reviewed_by: str, redaction_notes: str, dry_run: bool) -> dict:
    if not dry_run:
        require_complete_live_evidence(evidence_root)
        require_clean_tracked_worktree()

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
                    "internal_app_user_open_id_request",
                    "internal_app_group_chat_id_request",
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


def build_final_review_packet(evidence_root: Path, manifest: dict, packet_path: Path) -> str:
    spikes = manifest.get("spikes", {})
    spike_rows = [
        f"`{name}`: {spike.get('status', 'missing')}"
        for name, spike in spikes.items()
    ]
    return "\n".join(
        [
            "# Final Redaction Review Packet",
            "",
            "This packet is context only. It is not readiness evidence and must stay under ignored `evidence/`.",
            "",
            f"- Generated at: {utc_now()}",
            f"- Evidence root: `{display_path(evidence_root)}`",
            f"- Packet path: `{display_path(packet_path)}`",
            f"- Manifest id: `{manifest.get('readiness_evidence_id', 'not_available')}`",
            f"- Manifest commit: `{manifest.get('commit', 'not_available')}`",
            f"- Reviewed by: {manifest.get('reviewed_by', 'not_available')}",
            "- Final gate: `python3 scripts/check_readiness.py --require-live --require-evidence`",
            "",
            "## Evidence Files",
            "",
            *evidence_file_rows(evidence_root),
            "",
            "## Manifest Spike Status",
            "",
            markdown_bullets(spike_rows, empty_label="No spike status available."),
            "",
            "## Validation Basis",
            "",
            "- Manifest spike status declares that required final evidence files are present for each spike.",
            "- It does not replace per-spike validators, strict preflight, or the final readiness gate.",
            "- Treat the manifest as shareable only after the required commands below pass on the same commit.",
            "",
            "## Redaction Checklist",
            "",
            "- Confirm no `TEMPLATE_` markers remain.",
            "- Confirm no raw Feishu recipient ids, app ids, authorization headers, API keys, local paths, or NAS/cloud targets remain.",
            "- Confirm source names, original titles, source URLs, run ids, provider/model names, request counts, latency, status codes, Feishu receive_id_type values, and failure reasons remain visible where required for validation.",
            "- Confirm rendered Feishu evidence includes Source, Confidence Notice, and Archive or Deep-Dive link text.",
            "- Confirm model evidence is metadata-only and does not include full article bodies, PDFs, transcripts, or unapproved media.",
            "- Confirm archive evidence redacts local and remote roots while preserving file counts, sync status, and retryability.",
            "- Confirm tracked git worktree is clean; ignored evidence files may remain untracked.",
            "",
            "## Share Guardrails",
            "",
            "- Do not paste raw evidence files into GitHub comments.",
            "- Share only validation summaries, commit ids, CI links, and redacted paths when updating issues.",
            "- Re-run strict preflight after any evidence file changes.",
            "",
            "## Required Commands",
            "",
            "```bash",
            "python3 scripts/spikes/model_provider_spike.py --validate-evidence",
            "python3 scripts/spikes/live_readiness_preflight.py --strict --write-packet --write-spike-packets",
            "python3 scripts/check_readiness.py --require-live --require-evidence",
            "```",
        ]
    )


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")


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
    parser.add_argument("--write-final-review-packet", action="store_true", help="Also write an ignored final redaction review packet.")
    parser.add_argument("--review-packet-output", help="Override final redaction review packet output path.")
    args = parser.parse_args()

    evidence_root = Path(args.evidence_root)
    output_path = Path(args.output) if args.output else evidence_root / ("readiness-manifest.dry-run.json" if args.dry_run else "readiness-manifest.json")
    review_packet_path = Path(args.review_packet_output) if args.review_packet_output else evidence_root / FINAL_REVIEW_PACKET
    try:
        manifest = build_manifest(evidence_root, args.reviewed_by, args.redaction_notes, args.dry_run)
        write_json(output_path, manifest)
        if args.write_final_review_packet:
            write_markdown(review_packet_path, build_final_review_packet(evidence_root, manifest, review_packet_path))
    except ManifestError as error:
        print(f"ERROR {error}")
        return 1

    print(f"{'DRY-RUN' if args.dry_run else 'LIVE'} readiness manifest written to {output_path}")
    if args.write_final_review_packet:
        print(f"Final redaction review packet written to {review_packet_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
