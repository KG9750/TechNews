#!/usr/bin/env python3
"""Throwaway Archive/storage spike runner.

Copies the sample Archive Package to ARCHIVE_LOCAL_ROOT, then copies it to a
mounted/local ARCHIVE_SYNC_TARGET when available. Evidence is written under
evidence/archive-storage/ and should not be committed.
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
FIXTURE_PACKAGE = ROOT / "fixtures/archive-storage/local-archive/2026-06-01/technology"
DEFAULT_EVIDENCE_DIR = ROOT / "evidence/archive-storage"


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


def copy_package(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def tree_lines(path: Path) -> list[str]:
    lines = []
    for child in sorted(path.rglob("*")):
        relative = child.relative_to(path)
        suffix = "/" if child.is_dir() else ""
        lines.append(f"{relative}{suffix}")
    return lines


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_evidence_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def redacted_archive_path(root_label: str) -> str:
    return f"{root_label}/2026-06-01/technology"


def redact_archive_text(text: str) -> str:
    replacements = {
        str(ROOT): "REDACTED_WORKSPACE",
        str(Path.home()): "REDACTED_HOME",
    }
    for env_name, label in [
        ("ARCHIVE_LOCAL_ROOT", "REDACTED_LOCAL_ARCHIVE_ROOT"),
        ("ARCHIVE_SYNC_TARGET", "REDACTED_SYNC_TARGET"),
    ]:
        value = os.environ.get(env_name)
        if not value:
            continue
        replacements[value] = label
        replacements[str(Path(value).expanduser())] = label

    redacted = text
    for needle, replacement in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        if needle:
            redacted = redacted.replace(needle, replacement)
    redacted = re.sub(r"/Users/[^/\s\"]+", "REDACTED_HOME", redacted)
    redacted = re.sub(r"(?<![A-Za-z0-9_./-])/private/", "REDACTED_PRIVATE/", redacted)
    redacted = redacted.replace("Mobile Documents/com~apple~CloudDocs", "REDACTED_ICLOUD_PATH")
    return redacted


def run(dry_run: bool, evidence_dir: Path) -> int:
    load_env_file(ROOT / ".env")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    require_fixture()

    local_root = os.environ.get("ARCHIVE_LOCAL_ROOT")
    sync_target = os.environ.get("ARCHIVE_SYNC_TARGET")
    result = {
        "run_id": "run_2026-06-01_archive_storage_spike",
        "dry_run": dry_run,
        "generated_at_epoch": int(time.time()),
        "local_archive": {},
        "remote_sync": {},
    }

    if dry_run:
        result["local_archive"] = {
            "status": "would_write",
            "source_fixture": str(FIXTURE_PACKAGE.relative_to(ROOT)),
            "target": "${ARCHIVE_LOCAL_ROOT}/2026-06-01/technology",
        }
        result["remote_sync"] = {
            "status": "would_sync_or_record_failure",
            "target": "${ARCHIVE_SYNC_TARGET}/2026-06-01/technology",
            "retryable": True,
        }
        write_json(evidence_dir / "dry-run-sync-result.json", result)
        print(f"DRY-RUN wrote archive sync plan to {evidence_dir}")
        return 0

    if not local_root:
        raise SpikeError("missing ARCHIVE_LOCAL_ROOT")

    local_package = Path(local_root).expanduser() / "2026-06-01/technology"
    copy_package(FIXTURE_PACKAGE, local_package)
    result["local_archive"] = {
        "status": "written",
        "package_path": redacted_archive_path("REDACTED_LOCAL_ARCHIVE_ROOT"),
        "file_count": len([p for p in local_package.rglob("*") if p.is_file()]),
    }
    (evidence_dir / "local-tree.txt").write_text("\n".join(tree_lines(local_package)) + "\n", encoding="utf-8")

    if not sync_target:
        result["remote_sync"] = {
            "status": "failed",
            "target": "ARCHIVE_SYNC_TARGET_UNSET",
            "failure_reason": "ARCHIVE_SYNC_TARGET is not configured.",
            "retryable": True,
        }
        write_json(evidence_dir / "sync-result.json", result)
        print(f"LIVE local write completed; sync target missing. Evidence written to {evidence_dir}")
        return 2

    remote_package = Path(sync_target).expanduser() / "2026-06-01/technology"
    try:
        copy_package(local_package, remote_package)
        result["remote_sync"] = {
            "status": "synced",
            "target": redacted_archive_path("REDACTED_SYNC_TARGET"),
            "file_count": len([p for p in remote_package.rglob("*") if p.is_file()]),
            "retryable": False,
        }
        (evidence_dir / "remote-tree.txt").write_text("\n".join(tree_lines(remote_package)) + "\n", encoding="utf-8")
        exit_code = 0
    except OSError as error:
        result["remote_sync"] = {
            "status": "failed",
            "target": redacted_archive_path("REDACTED_SYNC_TARGET"),
            "failure_reason": redact_archive_text(str(error)),
            "retryable": True,
        }
        exit_code = 2

    write_json(evidence_dir / "sync-result.json", result)
    print(f"LIVE archive evidence written to {evidence_dir}")
    return exit_code


def require_fixture() -> None:
    for name in ["briefing.html", "briefing.md", "metadata.json", "media/README.md"]:
        path = FIXTURE_PACKAGE / name
        if not path.exists():
            raise SpikeError(f"missing archive fixture file: {path}")


def check_evidence_redaction(path: Path) -> None:
    text = read_evidence_text(path)
    if "TEMPLATE_" in text:
        raise SpikeError(f"{path}: evidence still contains TEMPLATE_ placeholder")
    for label, pattern in [
        ("local user path", r"/Users/[^/\s\"]+"),
        ("private tmp path", r"(?<![A-Za-z0-9_./-])/private/"),
        ("iCloud workspace path", r"Mobile Documents/com~apple~CloudDocs"),
    ]:
        if re.search(pattern, text):
            raise SpikeError(f"{path}: evidence may leak {label}")
    for env_name in ["ARCHIVE_LOCAL_ROOT", "ARCHIVE_SYNC_TARGET"]:
        value = os.environ.get(env_name, "")
        if len(value) >= 8 and value in text:
            raise SpikeError(f"{path}: evidence contains raw environment value {env_name}")


def read_tree(path: Path) -> list[str]:
    if not path.exists():
        raise SpikeError(f"missing archive evidence tree file: {path}")
    check_evidence_redaction(path)
    lines = [line.strip() for line in read_evidence_text(path).splitlines() if line.strip()]
    if not lines:
        raise SpikeError(f"{path}: archive evidence tree must list at least one file")
    return lines


def positive_int(value: object, label: str) -> int:
    try:
        number = int(value or 0)
    except (TypeError, ValueError) as error:
        raise SpikeError(f"{label} must be an integer") from error
    if number <= 0:
        raise SpikeError(f"{label} must be > 0")
    return number


def validate_evidence(evidence_dir: Path) -> int:
    load_env_file(ROOT / ".env")
    result_path = evidence_dir / "sync-result.json"
    if not result_path.exists():
        raise SpikeError(f"missing archive evidence sync result: {result_path}")
    check_evidence_redaction(result_path)
    payload = json.loads(read_evidence_text(result_path))
    if payload.get("local_archive", {}).get("status") != "written":
        raise SpikeError(f"{result_path}: local_archive.status must be written")
    if payload.get("remote_sync", {}).get("status") != "synced":
        raise SpikeError(f"{result_path}: remote_sync.status must be synced")

    local_count = positive_int(payload.get("local_archive", {}).get("file_count"), "local_archive.file_count")
    remote_count = positive_int(payload.get("remote_sync", {}).get("file_count"), "remote_sync.file_count")
    if local_count != remote_count:
        raise SpikeError(f"{result_path}: local and remote file_count values must match")

    local_tree = read_tree(evidence_dir / "local-tree.txt")
    remote_tree = read_tree(evidence_dir / "remote-tree.txt")
    if local_tree != remote_tree:
        raise SpikeError("archive evidence local and remote tree listings must match")
    print(f"LIVE archive evidence validates: {evidence_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Validate copy plan without writing archive roots.")
    parser.add_argument("--validate-evidence", action="store_true", help="Validate redacted live archive sync evidence.")
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    args = parser.parse_args()
    try:
        if args.validate_evidence:
            return validate_evidence(Path(args.evidence_dir))
        return run(dry_run=args.dry_run, evidence_dir=Path(args.evidence_dir))
    except (FileNotFoundError, json.JSONDecodeError, SpikeError) as error:
        print(f"ERROR {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
