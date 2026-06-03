#!/usr/bin/env python3
"""Regression tests for source_owner_review_decision.py."""

from __future__ import annotations

import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

import source_owner_review_decision as review


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = [
    "fixtures/source-ingestion/source-owner-review-queue.json",
    "fixtures/source-ingestion/source-access-policy.json",
    "docs/source-eligibility-reviews.md",
    "docs/source-registry.md",
]


@contextmanager
def isolated_artifacts():
    old_values = {
        "ROOT": review.ROOT,
        "QUEUE_PATH": review.QUEUE_PATH,
        "POLICY_PATH": review.POLICY_PATH,
        "REVIEW_PATH": review.REVIEW_PATH,
        "REGISTRY_PATH": review.REGISTRY_PATH,
    }
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        for rel_path in ARTIFACTS:
            target = tmp / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel_path, target)

        review.ROOT = tmp
        review.QUEUE_PATH = tmp / "fixtures/source-ingestion/source-owner-review-queue.json"
        review.POLICY_PATH = tmp / "fixtures/source-ingestion/source-access-policy.json"
        review.REVIEW_PATH = tmp / "docs/source-eligibility-reviews.md"
        review.REGISTRY_PATH = tmp / "docs/source-registry.md"
        try:
            yield tmp
        finally:
            for name, value in old_values.items():
                setattr(review, name, value)


def decision_payload(decision: str) -> dict:
    production_enabled = decision == "eligible"
    return {
        "source_id": "src-the-verge",
        "reviewed_at": "2026-06-03",
        "reviewed_by": "Briefing Administrator",
        "decision": decision,
        "evidence_checked": [
            {
                "required_evidence": "Vox Media/The Verge terms or permission path",
                "url_or_note": "Owner note: permission path reviewed.",
                "checked_at": "2026-06-03",
            },
            {
                "required_evidence": "generated-summary permission",
                "url_or_note": "Owner note: generated-summary scope reviewed.",
                "checked_at": "2026-06-03",
            },
            {
                "required_evidence": "media reuse decision",
                "url_or_note": "Owner note: media remains blocked.",
                "checked_at": "2026-06-03",
            },
        ],
        "owner_question_answers": [
            {
                "question": "Can RSS metadata be used for internal generated summaries?",
                "answer": "Owner answer recorded for test.",
            },
            {
                "question": "Are source images allowed, or should this remain text-only?",
                "answer": "Keep text-only for test.",
            },
        ],
        "policy_after_decision": {
            "eligibility_state": decision,
            "connector_mode": "rss_metadata_only" if production_enabled else "rss_metadata_probe",
            "production_auto_ingestion": production_enabled,
            "full_text_storage": "not_stored",
            "summary_policy": "generated_summary_from_metadata_only" if production_enabled else "generated_summary_disallowed",
            "media_policy": "none_until_approved",
            "rate_policy": "conservative_default" if production_enabled else "no_production_fetch",
        },
        "implementation_guardrail": "Regression test guardrail.",
        "artifact_updates": {
            "review_matrix": {
                "terms_evidence": f"Owner decision reviewed 2026-06-03; test decision {decision}.",
                "summary_storage": "Generated summaries follow the owner decision.",
                "media_use": "No media reuse.",
                "rate_limit": "Conservative default for test." if production_enabled else "No production fetch.",
                "next_action": f"Apply test decision {decision}.",
            },
            "source_registry": {
                "eligibility_notes": f"Regression test applied decision {decision}.",
            },
        },
    }


def write_decision(tmp: Path, payload: dict) -> Path:
    path = tmp / "decision.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def source_policy(tmp: Path, source_id: str) -> dict:
    policy = json.loads((tmp / "fixtures/source-ingestion/source-access-policy.json").read_text(encoding="utf-8"))
    return next(source for source in policy["sources"] if source["source_id"] == source_id)


def queued_source_ids(tmp: Path) -> set[str]:
    queue = json.loads((tmp / "fixtures/source-ingestion/source-owner-review-queue.json").read_text(encoding="utf-8"))
    return {item["source_id"] for item in queue["items"]}


def test_draft_requires_owner_input() -> None:
    draft = review.draft_payload("src-the-verge")
    assert "artifact_updates" in draft
    assert review.contains_template_marker(draft)


def test_draft_all_writes_every_open_review_without_overwriting_existing() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"
        existing = evidence_dir / "src-the-verge.decision.json"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text('{"keep": true}\n', encoding="utf-8")

        review.write_all_drafts(evidence_dir)

        open_ids = review.open_source_ids()
        draft_ids = {
            path.name.removesuffix(".decision.json")
            for path in evidence_dir.glob("*.decision.json")
        }
        assert set(open_ids) == draft_ids
        assert existing.read_text(encoding="utf-8") == '{"keep": true}\n'

        generated = json.loads((evidence_dir / "src-techcrunch.decision.json").read_text(encoding="utf-8"))
        assert generated["source_id"] == "src-techcrunch"
        assert review.contains_template_marker(generated)


def test_blocked_decision_updates_artifacts_and_closes_queue() -> None:
    with isolated_artifacts() as tmp:
        decision_path = write_decision(tmp, decision_payload("blocked"))
        review.apply_decision(decision_path, dry_run=False)

        review_text = (tmp / "docs/source-eligibility-reviews.md").read_text(encoding="utf-8")
        registry_text = (tmp / "docs/source-registry.md").read_text(encoding="utf-8")
        policy = source_policy(tmp, "src-the-verge")

        assert "| src-the-verge | blocked |" in review_text
        assert "Regression test applied decision blocked." in registry_text
        assert policy["eligibility_state"] == "blocked"
        assert policy["production_auto_ingestion"] is False
        assert policy["requires_owner_review"] is False
        assert "src-the-verge" not in queued_source_ids(tmp)


def test_needs_review_decision_keeps_queue_open() -> None:
    with isolated_artifacts() as tmp:
        decision_path = write_decision(tmp, decision_payload("needs_review"))
        review.apply_decision(decision_path, dry_run=False)

        review_text = (tmp / "docs/source-eligibility-reviews.md").read_text(encoding="utf-8")
        policy = source_policy(tmp, "src-the-verge")

        assert "| src-the-verge | needs_review |" in review_text
        assert policy["eligibility_state"] == "needs_review"
        assert policy["production_auto_ingestion"] is False
        assert policy["requires_owner_review"] is True
        assert "src-the-verge" in queued_source_ids(tmp)


def main() -> int:
    test_draft_requires_owner_input()
    test_draft_all_writes_every_open_review_without_overwriting_existing()
    test_blocked_decision_updates_artifacts_and_closes_queue()
    test_needs_review_decision_keeps_queue_open()
    print("source owner review decision tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
