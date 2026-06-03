#!/usr/bin/env python3
"""Regression tests for live evidence helper scripts."""

from __future__ import annotations

import importlib.util
import json
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


preflight = load_module("live_readiness_preflight", ROOT / "scripts/spikes/live_readiness_preflight.py")
manifest = load_module("readiness_manifest", ROOT / "scripts/spikes/readiness_manifest.py")
readiness = load_module("check_readiness", ROOT / "scripts/check_readiness.py")


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


def test_preflight_redacts_workspace_and_env_values() -> None:
    secret = "test-secret-value-123456789"
    with with_env("MODEL_API_KEY", secret):
        text = preflight.redact_text(f"{preflight.ROOT} {Path.home()} {secret}")
        assert str(preflight.ROOT) not in text
        assert str(Path.home()) not in text
        assert secret not in text
        assert "REDACTED_WORKSPACE" in text
        assert "REDACTED_ENV_VALUE" in text

        with tempfile.TemporaryDirectory() as tmp_name:
            summary = preflight.build_summary(Path(tmp_name), run_helpers=False)
        encoded = json.dumps(summary, ensure_ascii=False)
        assert secret not in encoded
        assert "MODEL_API_KEY" in encoded


def test_preflight_dry_runs_write_to_temp_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp_name:
        evidence_root = Path(tmp_name)
        results = preflight.run_dry_runs(evidence_root, run_helpers=True)
        assert len(results) == 4
        assert all(result["returncode"] == 0 for result in results)
        assert (evidence_root / "feishu-delivery/dry-run-request-shape.redacted.json").exists()
        assert (evidence_root / "model-provider/dry-run-summary.json").exists()
        assert (evidence_root / "archive-storage/dry-run-sync-result.json").exists()
        assert (evidence_root / "readiness-manifest.dry-run.json").exists()


def test_preflight_packet_lists_status_without_secret_values() -> None:
    secret = "packet-secret-value-123456789"
    with with_env("MODEL_API_KEY", secret):
        with tempfile.TemporaryDirectory() as tmp_name:
            evidence_root = Path(tmp_name)
            summary_path = evidence_root / "summary.json"
            packet_path = evidence_root / "packet.md"
            summary = preflight.build_summary(evidence_root, run_helpers=False)
            packet = preflight.build_markdown_packet(summary, evidence_root, summary_path, packet_path)
            preflight.write_markdown(packet_path, packet)

            assert packet_path.exists()

    assert "# Live Readiness Execution Packet" in packet
    assert "MODEL_API_KEY" in packet
    assert "readiness-manifest.json" in packet
    assert "python3 scripts/check_readiness.py --require-live --require-evidence" in packet
    assert secret not in packet
    assert str(preflight.ROOT) not in packet
    assert str(Path.home()) not in packet


def test_readiness_manifest_dry_run_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp_name:
        evidence_root = Path(tmp_name)
        payload = manifest.build_manifest(
            evidence_root,
            reviewed_by="Briefing Administrator",
            redaction_notes="Dry-run regression test.",
            dry_run=True,
        )
    assert payload["repository"] == "KG9750/TechNews"
    assert payload["spikes"]["feishu_delivery"]["status"] == "missing"
    assert payload["spikes"]["model_provider"]["provider"] == "not_available_dry_run"
    assert payload["spikes"]["archive_storage"]["run_id"] == "not_available_dry_run"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def model_output(profile: str, fixture_id: str, run_id: str, confidence_level: str) -> dict:
    fixture = readiness.golden_sample_by_id()[fixture_id]
    anchor = fixture["raw_source_metadata"]
    classification = fixture.get("expected_classification", {})
    return {
        "input_fixture_id": fixture_id,
        "briefing_item": {
            "id": f"brief_{profile}",
            "run_id": run_id,
            "candidate_id": f"candidate_{profile}",
            "section": classification.get("section", "AI"),
            "subcategory": classification.get("subcategory", "Regression Test"),
            "title_zh": f"{profile} synthetic title",
            "bullets_zh": [
                "Synthetic bullet one.",
                "Synthetic bullet two.",
                "Synthetic bullet three.",
            ],
            "original_source_anchor": {
                "source_name": anchor["source_name"],
                "original_title": anchor["original_title"],
                "source_url": anchor["source_url"],
            },
            "selection_rationale": {
                "summary": "Synthetic redacted rationale.",
                "signals": ["source_trust", "event_impact"],
            },
            "confidence_level": confidence_level,
            "confidence_notice": "Synthetic confidence notice." if confidence_level in {"medium", "low"} else None,
            "media_attribution": None,
            "related_history": [],
        },
        "model_usage": {
            "provider": "synthetic-live-provider",
            "model": "synthetic-live-model",
            "task_type": "briefing_item_generation",
            "request_count": 1,
            "latency_ms": 100,
            "failure_reason": None,
        },
    }


def write_synthetic_live_evidence(evidence_root: Path) -> None:
    model_run_id = "run_synthetic_model_provider"
    archive_run_id = "run_synthetic_archive_storage"
    provider = "synthetic-live-provider"
    model = "synthetic-live-model"

    write_json(
        evidence_root / "feishu-delivery/user-response.redacted.json",
        {"code": 0, "msg": "success", "data": {"message_id": "REDACTED_MESSAGE_ID_USER"}},
    )
    write_json(
        evidence_root / "feishu-delivery/group-response.redacted.json",
        {"code": 0, "msg": "success", "data": {"message_id": "REDACTED_MESSAGE_ID_GROUP"}},
    )
    (evidence_root / "feishu-delivery").mkdir(parents=True, exist_ok=True)
    (evidence_root / "feishu-delivery/rendered-message.md").write_text(
        "Source: Synthetic Source\n置信提示: Synthetic confidence notice.\n",
        encoding="utf-8",
    )

    profiles = {
        "high-confidence-news": ("sample-001-openai-gpt-4o", "high"),
        "low-confidence-news": ("sample-020-single-source-leak", "low"),
        "academic-paper": ("sample-018-rt-2", "medium"),
    }
    for profile, (fixture_id, confidence_level) in profiles.items():
        output = model_output(profile, fixture_id, model_run_id, confidence_level)
        write_json(evidence_root / f"model-provider/outputs/{profile}.json", output)
    write_json(
        evidence_root / "model-provider/usage-log.json",
        {
            "run_id": model_run_id,
            "status": "completed",
            "provider": provider,
            "model": model,
            "tasks": [
                {
                    "task_type": "briefing_item_generation",
                    "input_fixture_id": fixture_id,
                    "output_fixture": f"outputs/{profile}.json",
                    "request_count": 1,
                    "latency_ms": 100,
                    "failure_reason": None,
                }
                for profile, (fixture_id, _) in profiles.items()
            ],
        },
    )

    write_json(
        evidence_root / "archive-storage/sync-result.json",
        {
            "run_id": archive_run_id,
            "local_archive": {
                "status": "written",
                "package_path": "REDACTED_LOCAL_ARCHIVE_ROOT/2026-06-01/technology",
                "file_count": 4,
            },
            "remote_sync": {
                "status": "synced",
                "target": "REDACTED_SYNC_TARGET/2026-06-01/technology",
                "file_count": 4,
                "retryable": False,
            },
        },
    )
    (evidence_root / "archive-storage").mkdir(parents=True, exist_ok=True)
    (evidence_root / "archive-storage/local-tree.txt").write_text("briefing.md\nmetadata.json\n", encoding="utf-8")
    (evidence_root / "archive-storage/remote-tree.txt").write_text("briefing.md\nmetadata.json\n", encoding="utf-8")

    write_json(
        evidence_root / "readiness-manifest.json",
        {
            "readiness_evidence_id": "readiness_synthetic_redacted",
            "generated_at": "2026-06-03T00:00:00Z",
            "repository": "KG9750/TechNews",
            "commit": "synthetic-redacted-commit",
            "reviewed_by": "Briefing Administrator",
            "redaction_review": {
                "reviewed_at": "2026-06-03T00:00:00Z",
                "notes": "Synthetic redacted positive evidence for validator regression testing.",
            },
            "spikes": {
                "feishu_delivery": {
                    "status": "passed",
                    "evidence_files": [
                        "feishu-delivery/user-response.redacted.json",
                        "feishu-delivery/group-response.redacted.json",
                        "feishu-delivery/rendered-message.md",
                    ],
                    "requirements": [
                        "one_user_delivery",
                        "one_group_delivery",
                        "source_line_present",
                        "confidence_notice_present",
                    ],
                },
                "model_provider": {
                    "status": "passed",
                    "run_id": model_run_id,
                    "provider": provider,
                    "model": model,
                    "evidence_files": [
                        "model-provider/outputs/high-confidence-news.json",
                        "model-provider/outputs/low-confidence-news.json",
                        "model-provider/outputs/academic-paper.json",
                        "model-provider/usage-log.json",
                    ],
                },
                "archive_storage": {
                    "status": "passed",
                    "run_id": archive_run_id,
                    "evidence_files": [
                        "archive-storage/sync-result.json",
                        "archive-storage/local-tree.txt",
                        "archive-storage/remote-tree.txt",
                    ],
                },
            },
        },
    )


def test_synthetic_live_evidence_package_passes_gate() -> None:
    with tempfile.TemporaryDirectory() as tmp_name:
        evidence_root = Path(tmp_name)
        write_synthetic_live_evidence(evidence_root)
        passed, missing, failures = readiness.check_live_evidence(evidence_root)
    assert not missing
    assert not failures
    assert "Live evidence manifest: declared files and spike run metadata are consistent" in passed
    assert "Feishu live evidence: user and group delivery responses present" in passed
    assert "Archive live evidence: local write and remote sync success present" in passed
    assert "Model live evidence: three live outputs and usage log valid" in passed


def test_live_evidence_rejects_raw_environment_values() -> None:
    secret = "live-secret-value-123456789"
    with with_env("FEISHU_APP_SECRET", secret):
        with tempfile.TemporaryDirectory() as tmp_name:
            path = Path(tmp_name) / "evidence.json"
            path.write_text(f'{{"redacted": "{secret}"}}\n', encoding="utf-8")
            failures: list[str] = []
            readiness.check_no_sensitive_live_evidence(path, failures, "Synthetic evidence")
    assert any("contains raw environment value FEISHU_APP_SECRET" in failure for failure in failures)


def main() -> int:
    test_preflight_redacts_workspace_and_env_values()
    test_preflight_dry_runs_write_to_temp_evidence()
    test_preflight_packet_lists_status_without_secret_values()
    test_readiness_manifest_dry_run_shape()
    test_synthetic_live_evidence_package_passes_gate()
    test_live_evidence_rejects_raw_environment_values()
    print("live evidence helper tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
