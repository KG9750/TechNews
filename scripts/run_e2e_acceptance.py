#!/usr/bin/env python3
"""Run the fixture-backed MVP E2E acceptance flow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from technews_briefing.e2e_acceptance import run_fixture_e2e_acceptance, write_redacted_report  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run fixture-backed TechNews MVP E2E acceptance")
    parser.add_argument("--archive-root", type=Path, help="Archive root to use for the acceptance package")
    parser.add_argument("--sync-target", type=Path, help="Archive sync target to use for the acceptance package")
    parser.add_argument("--write-report", type=Path, help="Write a redacted JSON acceptance report")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.archive_root and args.sync_target:
        result = run_fixture_e2e_acceptance(
            repo_root=ROOT,
            archive_root=args.archive_root,
            sync_target=args.sync_target,
        )
        return _finish(result.report, args.write_report)

    with TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        result = run_fixture_e2e_acceptance(
            repo_root=ROOT,
            archive_root=tmp / "archives",
            sync_target=tmp / "sync-target",
        )
        return _finish(result.report, args.write_report)


def _finish(report: dict[str, object], write_report: Path | None) -> int:
    if write_report is not None:
        write_redacted_report(report, write_report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.get("passed") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
