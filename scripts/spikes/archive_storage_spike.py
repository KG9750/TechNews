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
        "package_path": str(local_package),
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
            "target": str(remote_package),
            "file_count": len([p for p in remote_package.rglob("*") if p.is_file()]),
            "retryable": False,
        }
        (evidence_dir / "remote-tree.txt").write_text("\n".join(tree_lines(remote_package)) + "\n", encoding="utf-8")
        exit_code = 0
    except OSError as error:
        result["remote_sync"] = {
            "status": "failed",
            "target": str(remote_package),
            "failure_reason": str(error),
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Validate copy plan without writing archive roots.")
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    args = parser.parse_args()
    try:
        return run(dry_run=args.dry_run, evidence_dir=Path(args.evidence_dir))
    except SpikeError as error:
        print(f"ERROR {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
