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


def main() -> int:
    test_preflight_redacts_workspace_and_env_values()
    test_preflight_dry_runs_write_to_temp_evidence()
    test_readiness_manifest_dry_run_shape()
    print("live evidence helper tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
