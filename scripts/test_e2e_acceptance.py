#!/usr/bin/env python3
"""Regression tests for the MVP E2E acceptance flow."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from technews_briefing.e2e_acceptance import run_fixture_e2e_acceptance, write_redacted_report  # noqa: E402
from technews_briefing.feishu_delivery import redact_feishu_payload  # noqa: E402


def test_fixture_e2e_acceptance_passes_mvp_checklist() -> None:
    with TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        result = run_fixture_e2e_acceptance(
            repo_root=ROOT,
            archive_root=tmp / "archives",
            sync_target=tmp / "sync-target",
        )
        report = result.report

        assert result.passed
        assert report["passed"] is True
        assert all(report["checklist"].values())
        assert report["configured_source_types"] == ["academic_source", "manual_url", "public_feed"]
        assert report["connector_status"]["src-manual-url"]["status"] == "skipped"
        assert report["connector_status"]["src-kubernetes-blog"]["status"] == "timeout"
        assert report["delivery_status"] == {
            "feishu_group_demo": "sent",
            "feishu_user_demo": "sent",
        }
        assert report["low_confidence_item_ids"]
        assert report["source_media_item_ids"]
        assert report["no_media_fallback_item_ids"]
        assert report["related_history_item_ids"]
        assert report["operations_console"]["delivery_status_count"] == 2


def test_fixture_e2e_acceptance_ties_run_id_across_artifacts() -> None:
    with TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        result = run_fixture_e2e_acceptance(
            repo_root=ROOT,
            archive_root=tmp / "archives",
            sync_target=tmp / "sync-target",
        )
        run_id = result.report["run_id"]
        metadata = result.archive.metadata

        assert {candidate.run_id for candidate in result.run.accepted_candidates} == {run_id}
        assert {item.run_id for item in result.briefing.items} == {run_id}
        assert metadata.run_id == run_id
        assert result.console_view.runs[0]["run_id"] == run_id
        assert {row["run_id"] for row in result.console_view.delivery_status} == {run_id}
        assert {row["run_id"] for row in result.console_view.sync_status} == {run_id}
        assert metadata.model_usage_summary.provider == "fixture"
        assert metadata.delivery_status["feishu_user_demo"].status == "sent"
        assert metadata.delivery_status["feishu_group_demo"].status == "sent"


def test_fixture_e2e_acceptance_outputs_archive_and_redacted_report() -> None:
    with TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        result = run_fixture_e2e_acceptance(
            repo_root=ROOT,
            archive_root=tmp / "archives",
            sync_target=tmp / "sync-target",
        )
        report_path = tmp / "evidence" / "e2e-report.json"
        write_redacted_report(result.report, report_path)
        serialized = report_path.read_text(encoding="utf-8")

        assert (result.archive.local_package_path / "briefing.html").exists()
        assert (result.archive.local_package_path / "briefing.md").exists()
        assert (result.archive.local_package_path / "metadata.json").exists()
        assert result.archive.remote_package_path is not None
        assert (result.archive.remote_package_path / "metadata.json").exists()
        for detail in result.briefing.deep_dive_details:
            assert (result.archive.local_package_path / detail.href).exists()
        assert str(tmp) not in serialized
        assert "fixture_user_open_id" not in serialized
        assert "fixture_group_chat_id" not in serialized


def test_fixture_e2e_acceptance_feishu_requests_are_redactable() -> None:
    with TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        result = run_fixture_e2e_acceptance(
            repo_root=ROOT,
            archive_root=tmp / "archives",
            sync_target=tmp / "sync-target",
        )
        evidence_shapes = [request.as_evidence_shape() for request in result.feishu_requests]
        serialized = json.dumps(evidence_shapes, ensure_ascii=False)

        assert len(evidence_shapes) == 2
        assert "fixture_user_open_id" not in serialized
        assert "fixture_group_chat_id" not in serialized
        assert all(shape["body"]["receive_id"] == "REDACTED" for shape in evidence_shapes)
        assert "Open Archive" in json.dumps(redact_feishu_payload(evidence_shapes), ensure_ascii=False)


def test_e2e_acceptance_script_prints_redacted_passing_report() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/run_e2e_acceptance.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    report = json.loads(completed.stdout)

    assert completed.returncode == 0
    assert report["passed"] is True
    assert "ARCHIVE_LOCAL_ROOT" not in completed.stdout
    assert "fixture_user_open_id" not in completed.stdout


def main() -> int:
    tests = [
        test_fixture_e2e_acceptance_passes_mvp_checklist,
        test_fixture_e2e_acceptance_ties_run_id_across_artifacts,
        test_fixture_e2e_acceptance_outputs_archive_and_redacted_report,
        test_fixture_e2e_acceptance_feishu_requests_are_redactable,
        test_e2e_acceptance_script_prints_redacted_passing_report,
    ]
    for test in tests:
        test()
    print("e2e acceptance tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
