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
    assert "Open source owner decisions: 25" in text
    assert "Missing source owner decisions: 25" in text
    assert "python3 scripts/check_readiness.py --require-live --require-evidence" in text
    assert "source-owner-reviews/index.md" in text
    assert "MODEL_API_KEY" in text
    assert secret not in text
    assert str(packet.ROOT) not in text
    assert str(Path.home()) not in text


def test_action_packet_writes_markdown() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp_name:
        output = Path(tmp_name) / "evidence/readiness-action-packet.md"
        evidence_root = Path(tmp_name) / "evidence"

        packet.write_packet(output, evidence_root)

        assert output.exists()
        text = output.read_text(encoding="utf-8")
        assert "Blocking Workstreams" in text
        assert "Source owner decisions" in text


def main() -> int:
    test_action_packet_summarizes_blockers_without_secret_values()
    test_action_packet_writes_markdown()
    print("readiness action packet tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
