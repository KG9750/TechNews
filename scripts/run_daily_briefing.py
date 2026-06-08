#!/usr/bin/env python3
"""Run the live metadata-only daily TechNews briefing."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from technews_briefing.daily_run import DailyRunError, run_live_daily_briefing  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live metadata-only TechNews daily briefing")
    parser.add_argument("--no-deliver", action="store_true", help="Build archive and report without sending to Feishu")
    parser.add_argument("--no-report", action="store_true", help="Do not write the ignored redacted daily-run report")
    parser.add_argument("--arxiv-delay-seconds", type=float, default=3.0)
    parser.add_argument("--max-feed-bytes", type=int, default=6_000_000)
    args = parser.parse_args()

    try:
        result = run_live_daily_briefing(
            repo_root=ROOT,
            deliver=not args.no_deliver,
            write_report=not args.no_report,
            arxiv_delay_seconds=args.arxiv_delay_seconds,
            max_feed_bytes=args.max_feed_bytes,
        )
    except DailyRunError as error:
        print(f"daily briefing failed: {error}", file=sys.stderr)
        return 1

    summary = {
        "run_id": result.run.run.run_id,
        "fetched": sum(1 for report in result.fetch_reports if report.status == "fetched"),
        "accepted_candidates": len(result.run.accepted_candidates),
        "selected": len(result.ranking.selected),
        "delivered": result.delivered,
        "archive_local_status": result.archive.metadata.sync_status["local_archive"].status,
        "archive_remote_status": result.archive.metadata.sync_status["remote_sync"].status,
        "report": str(result.report_path.relative_to(ROOT)) if result.report_path else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
