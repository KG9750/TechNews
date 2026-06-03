#!/usr/bin/env python3
"""Regression tests for readiness_action_packet.py."""

from __future__ import annotations

import importlib.util
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


packet = load_module("readiness_action_packet", ROOT / "scripts/readiness_action_packet.py")


def with_env(name: str, value: str):
    class EnvGuard:
        def __enter__(self):
            self.old = os.environ.get(name)
            os.environ[name] = value

        def __exit__(self, exc_type, exc, tb):
            if self.old is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = self.old

    return EnvGuard()


def test_action_packet_summarizes_blockers_without_secret_values() -> None:
    secret = "action-packet-secret-123456789"
    with with_env("MODEL_API_KEY", secret):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp_name:
            evidence_root = Path(tmp_name) / "evidence"
            text = packet.build_packet(evidence_root)

    assert "# Pre-development Readiness Action Packet" in text
    assert "Missing live environment variables:" in text
    assert "Incomplete final evidence groups:" in text
    assert "Missing live evidence validation inputs:" in text
    assert "Open source owner decisions: 25" in text
    assert "Missing source owner decisions: 25" in text
    assert "python3 scripts/check_readiness.py --require-live --require-evidence" in text
    assert "Final evidence group | Missing env vars" in text
    assert "Readiness manifest | blocked | missing | 0 | 1" in text
    assert "Missing validation inputs | Validation failures" in text
    assert "## External Input Request Checklist" in text
    assert "Use this checklist to request missing live-spike inputs without collecting real values" in text
    assert "| Feishu delivery | https://github.com/KG9750/TechNews/issues/3 |" in text
    assert "FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_DEFAULT_USER_OPEN_ID, FEISHU_DEFAULT_CHAT_ID" in text
    assert "MODEL_PROVIDER, MODEL_DEFAULT_MODEL, MODEL_API_KEY" in text
    assert "ARCHIVE_LOCAL_ROOT, ARCHIVE_SYNC_TARGET" in text
    assert "Briefing Host secret store or local `.env`; never GitHub." in text
    assert "## MVP Issue Unlock Matrix" in text
    assert "| #17 | Feishu delivery | blocked | Feishu delivery spike:" in text
    assert "| #18 | Operations Console | ready for final triage | None." in text
    assert "Core MVP issues: core MVP issues #10-#19 must complete before E2E acceptance" in text
    assert "Keep `needs-triage` until final readiness and GitHub tracker gates pass." in text
    assert "https://github.com/KG9750/TechNews/issues/3" in text
    assert "source-owner-reviews/index.md" in text
    assert "source-owner-reviews/worksheet.md" in text
    assert "source-owner-reviews/batch-plan.md" in text
    assert "source-owner-reviews/request-packet.md" in text
    assert "mvp-issue-packets" in text
    assert "live-spike-packets" in text
    assert "external-input-request.md" in text
    assert "github-update-packet.md" in text
    assert "final-redaction-review.md" in text
    assert "python3 scripts/spikes/live_readiness_preflight.py --dry-run --write-packet --write-spike-packets" in text
    assert "python3 scripts/spikes/readiness_manifest.py --write-final-review-packet" in text
    assert "python3 scripts/spikes/feishu_delivery_spike.py --validate-evidence" in text
    assert "python3 scripts/spikes/model_provider_spike.py --validate-requests" in text
    assert "python3 scripts/spikes/model_provider_spike.py --validate-evidence" in text
    assert "python3 scripts/spikes/archive_storage_spike.py --validate-evidence" in text
    assert "python3 scripts/readiness_action_packet.py --write-source-owner-packets --write-mvp-issue-packets" in text
    assert "MODEL_API_KEY" in text
    assert secret not in text
    assert str(packet.ROOT) not in text
    assert str(Path.home()) not in text


def test_github_update_packet_names_label_guardrails_without_secret_values() -> None:
    secret = "github-update-secret-123456789"
    with with_env("ARCHIVE_SYNC_TARGET", secret):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp_name:
            evidence_root = Path(tmp_name) / "evidence"
            text = packet.build_github_update_packet(evidence_root)

    assert "# GitHub Update Packet" in text
    assert "Label Guardrails" in text
    assert "Keep #1 `needs-triage` while the final readiness gate is blocked." in text
    assert "Keep #3, #5, and #6 `needs-info` while their live evidence groups are incomplete." in text
    assert "Keep #10 through #20 `needs-triage` until final readiness and GitHub tracker gates pass." in text
    assert "Copy-Safe Issue Comments" in text
    assert "### #1 Pre-development Tracking" in text
    assert "### #10-#20 MVP Issue Triage" in text
    assert "Final readiness gate: blocked" in text
    assert "Source owner decisions: blocked" in text
    assert "FEISHU_APP_ID" in text
    assert "MODEL_PROVIDER" in text
    assert "ARCHIVE_LOCAL_ROOT" in text
    assert "ARCHIVE_SYNC_TARGET" in text
    assert "evidence/readiness-action-packet.md" in text
    assert "evidence/external-input-request.md" in text
    assert "evidence/github-update-packet.md" in text
    assert "evidence/mvp-issue-packets/issue-10.md through issue-20.md" in text
    assert "python3 scripts/check_readiness.py --require-github" in text
    assert "Do not paste secrets" in text
    assert secret not in text
    assert str(packet.ROOT) not in text
    assert str(Path.home()) not in text


def test_external_input_request_packet_names_inputs_without_secret_values() -> None:
    secret = "external-input-secret-123456789"
    with with_env("FEISHU_APP_SECRET", secret):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp_name:
            evidence_root = Path(tmp_name) / "evidence"
            text = packet.build_external_input_request_packet(evidence_root)

    assert "# External Input Request Packet" in text
    assert "Required variable names:" in text
    assert "Missing variable names now:" in text
    assert "Required evidence files:" in text
    assert "Commands after values are configured:" in text
    assert "FEISHU_APP_ID" in text
    assert "FEISHU_APP_SECRET" in text
    assert "feishu-delivery/user-request.redacted.json" in text
    assert "model-provider/usage-log.json" in text
    assert "archive-storage/sync-result.json" in text
    assert "python3 scripts/spikes/feishu_delivery_spike.py --validate-evidence" in text
    assert "python3 scripts/spikes/model_provider_spike.py --validate-evidence" in text
    assert "python3 scripts/spikes/archive_storage_spike.py --validate-evidence" in text
    assert "Share variable names and setup instructions only." in text
    assert secret not in text
    assert str(packet.ROOT) not in text
    assert str(Path.home()) not in text


def test_action_packet_blocks_unlocks_on_partial_final_evidence_group() -> None:
    live_summary = {
        "environment": {
            "feishu": {"present": [], "missing": []},
            "model_provider": {"present": [], "missing": []},
            "archive_sync": {"present": [], "missing": []},
        },
        "evidence": {"present": [], "missing": []},
        "final_evidence_groups": {
            "readiness_manifest": {"status": "complete", "present": [], "missing": []},
            "feishu_delivery": {"status": "partial", "present": [], "missing": []},
            "model_provider": {"status": "complete", "present": [], "missing": []},
            "archive_storage": {"status": "complete", "present": [], "missing": []},
        },
        "evidence_validation": {"passed": [], "missing": [], "failures": []},
    }
    source_summary = {
        "counts": {"valid": 0, "invalid": 0, "missing": 0},
    }

    states = packet.prerequisite_states(live_summary, source_summary)
    statuses = packet.mvp_issue_statuses(live_summary, source_summary)
    feishu_issue = next(status for status in statuses if status["issue"] == "#17")

    assert states["feishu_delivery"]["status"] == "blocked"
    assert "final evidence group partial" in states["feishu_delivery"]["detail"]
    assert states["final_readiness_gate"]["status"] == "blocked"
    assert "1 incomplete final evidence group" in states["final_readiness_gate"]["detail"]
    assert feishu_issue["issue_specific_status"] == "blocked"
    assert "Feishu delivery spike: final evidence group partial" in feishu_issue["blocker_details"]


def test_action_packet_writes_markdown() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp_name:
        output = Path(tmp_name) / "evidence/readiness-action-packet.md"
        evidence_root = Path(tmp_name) / "evidence"
        external_input_output = evidence_root / packet.EXTERNAL_INPUT_REQUEST_RELATIVE
        github_update_output = evidence_root / packet.GITHUB_UPDATE_PACKET_RELATIVE

        packet.write_packet(output, evidence_root)
        packet.write_external_input_request_packet(external_input_output, evidence_root)
        packet.write_github_update_packet(github_update_output, evidence_root)

        assert output.exists()
        assert external_input_output.exists()
        assert github_update_output.exists()
        text = output.read_text(encoding="utf-8")
        external_input_text = external_input_output.read_text(encoding="utf-8")
        github_update_text = github_update_output.read_text(encoding="utf-8")
        assert "Blocking Workstreams" in text
        assert "Source owner decisions" in text
        assert "External Input Request Packet" in external_input_text
        assert "GitHub Update Packet" in github_update_text


def test_source_owner_packets_can_be_written_from_action_packet() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp_name:
        evidence_root = Path(tmp_name) / "evidence"

        written = packet.write_source_owner_packets(evidence_root)

        source_owner_dir = evidence_root / "source-owner-reviews"
        assert written == 25
        assert (source_owner_dir / "index.md").exists()
        assert (source_owner_dir / "worksheet.md").exists()
        assert (source_owner_dir / "batch-plan.md").exists()
        assert (source_owner_dir / "request-packet.md").exists()
        assert (source_owner_dir / "src-the-verge.decision.json").exists()
        assert (source_owner_dir / "src-the-verge.packet.md").exists()
        assert "Source Owner Decision Request Packet" in (source_owner_dir / "request-packet.md").read_text(encoding="utf-8")


def test_mvp_issue_packets_are_written_with_label_guardrails() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp_name:
        evidence_root = Path(tmp_name) / "evidence"
        output_dir = evidence_root / "mvp-issue-packets"

        written = packet.write_mvp_issue_packets(output_dir, evidence_root)

        files = sorted(output_dir.glob("issue-*.md"))
        assert written == 11
        assert len(files) == 11

        feishu_text = (output_dir / "issue-17.md").read_text(encoding="utf-8")
        console_text = (output_dir / "issue-18.md").read_text(encoding="utf-8")

        assert "MVP Issue Triage Packet: #17 Feishu delivery" in feishu_text
        assert "Feishu delivery spike:" in feishu_text
        assert "Issue-specific status: blocked" in feishu_text
        assert "docs/issues/mvp/08-feishu-delivery.md" in feishu_text
        assert "Do not paste secrets" in feishu_text

        assert "MVP Issue Triage Packet: #18 Operations Console" in console_text
        assert "Issue-specific status: ready for final triage" in console_text
        assert "Global readiness gate: blocked" in console_text
        assert "Label action: Keep `needs-triage` until final readiness and GitHub tracker gates pass." in console_text
        assert "Remaining Issue-Specific Inputs" in console_text
        assert "- None." in console_text


def main() -> int:
    test_action_packet_summarizes_blockers_without_secret_values()
    test_github_update_packet_names_label_guardrails_without_secret_values()
    test_external_input_request_packet_names_inputs_without_secret_values()
    test_action_packet_blocks_unlocks_on_partial_final_evidence_group()
    test_action_packet_writes_markdown()
    test_source_owner_packets_can_be_written_from_action_packet()
    test_mvp_issue_packets_are_written_with_label_guardrails()
    print("readiness action packet tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
