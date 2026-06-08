#!/usr/bin/env python3
"""Validate JSON and markdown fixture files used by contracts and readiness checks."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "fixtures"
REQUIRED_MARKDOWN_FIXTURES = [
    "fixtures/archive-storage/README.md",
    "fixtures/archive-storage/local-archive/2026-06-01/technology/briefing.md",
    "fixtures/archive-storage/local-archive/2026-06-01/technology/media/README.md",
    "fixtures/feishu-delivery/README.md",
    "fixtures/feishu-delivery/rendered-message.md",
    "fixtures/golden-samples/README.md",
    "fixtures/model-provider/prompt-contract.md",
]


class FixtureValidationError(ValueError):
    """Raised when a fixture file is missing or malformed."""


def fixture_files(pattern: str) -> list[Path]:
    return sorted(FIXTURE_ROOT.glob(pattern))


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def validate_json_file(path: Path) -> None:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FixtureValidationError(f"{relative(path)} is not valid JSON: {exc}") from exc


def validate_markdown_file(path: Path) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise FixtureValidationError(f"{relative(path)} is not UTF-8 markdown") from exc
    if "\x00" in text:
        raise FixtureValidationError(f"{relative(path)} contains NUL bytes")
    if not text.strip():
        raise FixtureValidationError(f"{relative(path)} must not be empty")


def main() -> int:
    if not FIXTURE_ROOT.exists():
        raise FixtureValidationError("fixtures directory is missing")

    json_files = fixture_files("**/*.json")
    markdown_files = fixture_files("**/*.md")
    if not json_files:
        raise FixtureValidationError("fixtures must include JSON examples")
    if not markdown_files:
        raise FixtureValidationError("fixtures must include markdown-backed examples")

    for fixture in REQUIRED_MARKDOWN_FIXTURES:
        path = ROOT / fixture
        if not path.exists():
            raise FixtureValidationError(f"missing required markdown fixture: {fixture}")

    for path in json_files:
        validate_json_file(path)
    for path in markdown_files:
        validate_markdown_file(path)

    print(f"fixture validation passed: {len(json_files)} JSON files, {len(markdown_files)} markdown files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
