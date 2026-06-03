#!/usr/bin/env python3
"""Regression tests for source_owner_review_decision.py."""

from __future__ import annotations

import json
import shutil
import tempfile
from contextlib import contextmanager
from contextlib import redirect_stdout
from io import StringIO
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


def decision_payload_for_source(source_id: str, decision: str) -> dict:
    production_enabled = decision == "eligible"
    queue_item = review.load_queue_items()[source_id]
    return {
        "source_id": source_id,
        "reviewed_at": "2026-06-03",
        "reviewed_by": "Briefing Administrator",
        "decision": decision,
        "evidence_checked": [
            {
                "required_evidence": evidence,
                "url_or_note": f"Owner note: reviewed {evidence}.",
                "checked_at": "2026-06-03",
            }
            for evidence in queue_item["evidence_required"]
        ],
        "owner_question_answers": [
            {
                "question": question,
                "answer": "Owner answer recorded for test.",
            }
            for question in queue_item["owner_questions"]
        ],
        "policy_after_decision": {
            "eligibility_state": decision,
            "connector_mode": "rss_metadata_only" if production_enabled else queue_item["default_connector_mode"],
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


def decision_payload(decision: str) -> dict:
    return decision_payload_for_source("src-the-verge", decision)


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


def artifact_snapshot(tmp: Path) -> dict[str, str]:
    return {rel_path: (tmp / rel_path).read_text(encoding="utf-8") for rel_path in ARTIFACTS}


def write_completed_open_decisions(evidence_dir: Path, decision: str) -> None:
    for source_id in review.open_source_ids():
        output = review.decision_path(evidence_dir, source_id)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(decision_payload_for_source(source_id, decision), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def assert_review_error(path: Path, expected: str) -> None:
    try:
        review.validated_payload(path)
    except review.ReviewError as error:
        assert expected in str(error)
        return
    raise AssertionError("expected source owner decision validation to fail")


def test_draft_requires_owner_input() -> None:
    draft = review.draft_payload("src-the-verge")
    assert "artifact_updates" in draft
    assert review.contains_template_marker(draft)


def test_draft_includes_current_artifact_context() -> None:
    draft = review.draft_payload("src-the-verge")
    context = draft["current_artifact_context"]

    assert context["review_matrix_row"]["Eligibility state"] == "needs_review"
    assert context["source_registry_row"]["Source"] == "The Verge"
    assert context["source_access_policy"]["source_id"] == "src-the-verge"
    assert context["owner_review_queue_item"]["source_id"] == "src-the-verge"


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


def test_packet_includes_review_context_and_commands() -> None:
    packet = review.review_packet("src-the-verge")

    assert "# Source Owner Review Packet: src-the-verge" in packet
    assert "This packet is context only. Complete the JSON decision file" in packet
    assert "The Verge" in packet
    assert "Vox Media/The Verge terms or permission path" in packet
    assert "Can RSS metadata be used for internal generated summaries?" in packet
    assert "python3 scripts/source_owner_review_decision.py --validate evidence/source-owner-reviews/src-the-verge.decision.json" in packet
    assert "python3 scripts/source_owner_review_decision.py --apply evidence/source-owner-reviews/src-the-verge.decision.json --dry-run" in packet


def test_packet_all_writes_every_open_packet() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"

        review.write_all_packets(evidence_dir)

        open_ids = review.open_source_ids()
        packet_ids = {
            path.name.removesuffix(".packet.md")
            for path in evidence_dir.glob("*.packet.md")
        }
        packet_text = (evidence_dir / "src-the-verge.packet.md").read_text(encoding="utf-8")

        assert set(open_ids) == packet_ids
        assert "The Verge" in packet_text
        assert "evidence/source-owner-reviews/src-the-verge.decision.json" in packet_text


def test_packet_index_groups_status_and_paths() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"
        review.write_all_drafts(evidence_dir)
        review.write_all_packets(evidence_dir)

        index = review.review_packet_index(evidence_dir)

        assert "# Source Owner Review Index" in index
        assert "- Open decisions: 25" in index
        assert "- Invalid decision files: 25" in index
        assert "### summary_permission" in index
        assert "src-the-verge.decision.json" in index
        assert "src-the-verge.packet.md" in index
        assert "| src-the-verge | The Verge | invalid | TEMPLATE_DECISION |" in index
        assert "python3 scripts/source_owner_review_decision.py --packet-index" in index


def test_packet_index_writes_index_file() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"

        review.write_packet_index(evidence_dir)

        index_path = evidence_dir / "index.md"
        assert index_path.exists()
        text = index_path.read_text(encoding="utf-8")
        assert "Source Owner Review Index" in text
        assert "Open Items By Decision Needed" in text


def test_review_worksheet_includes_decision_fields_and_prompts() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"
        review.write_all_drafts(evidence_dir)
        review.write_all_packets(evidence_dir)

        worksheet = review.review_worksheet(evidence_dir)

        assert "# Source Owner Review Worksheet" in worksheet
        assert "- Open decisions: 25" in worksheet
        assert "## Decision Fields To Complete" in worksheet
        assert "`policy_after_decision` with full text storage still `not_stored`" in worksheet
        assert "| src-the-verge | The Verge | invalid | summary_permission |" in worksheet
        assert "### src-the-verge - The Verge" in worksheet
        assert "Vox Media/The Verge terms or permission path" in worksheet
        assert "Can RSS metadata be used for internal generated summaries?" in worksheet
        assert "python3 scripts/source_owner_review_decision.py --worksheet" in worksheet


def test_review_worksheet_writes_worksheet_file() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"

        review.write_worksheet(evidence_dir)

        worksheet_path = evidence_dir / "worksheet.md"
        assert worksheet_path.exists()
        text = worksheet_path.read_text(encoding="utf-8")
        assert "Source Owner Review Worksheet" in text
        assert "Open Decision Checklist" in text


def test_batch_plan_groups_open_items_and_paths() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"
        review.write_all_drafts(evidence_dir)
        review.write_all_packets(evidence_dir)

        plan = review.review_batch_plan(evidence_dir)

        assert "# Source Owner Review Batch Plan" in plan
        assert "Batch 1 - Access Path Blockers" in plan
        assert "Batch 2 - RSS Feed Reuse Scope" in plan
        assert "Batch 3 - Generated Summary And Media Permission" in plan
        assert "Batch 4 - License Obligations" in plan
        assert "| Batch 1 - Access Path Blockers | 3 | 0 | 3 | 0 | automated_access_permission, manual_per_item_review |" in plan
        assert "| Batch 2 - RSS Feed Reuse Scope | 7 | 0 | 7 | 0 | feed_reuse_scope |" in plan
        assert "| Batch 3 - Generated Summary And Media Permission | 11 | 0 | 11 | 0 | summary_permission |" in plan
        assert "| Batch 4 - License Obligations | 4 | 0 | 4 | 0 | license_obligation |" in plan
        assert "| src-anthropic-news | Anthropic News | AI | official | automated_access_permission |" in plan
        assert "| src-manual-url | Manual URL Inbox | Technology Industry Progress | administrator | manual_per_item_review |" in plan
        assert "| src-techcrunch | TechCrunch | Technology Industry Progress | mainstream | feed_reuse_scope |" in plan
        assert "| src-the-verge | The Verge | Technology Industry Progress | mainstream | summary_permission |" in plan
        assert "| src-nvidia-blog | NVIDIA Blog | Hardware | official | license_obligation |" in plan
        assert "evidence/source-owner-reviews/src-the-verge.decision.json" in plan
        assert "evidence/source-owner-reviews/src-the-verge.packet.md" in plan
        assert "python3 scripts/source_owner_review_decision.py --batch-plan" in plan


def test_batch_plan_writes_batch_plan_file() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"

        review.write_batch_plan(evidence_dir)

        batch_plan_path = evidence_dir / "batch-plan.md"
        assert batch_plan_path.exists()
        text = batch_plan_path.read_text(encoding="utf-8")
        assert "Source Owner Review Batch Plan" in text
        assert "Batch Summary" in text


def test_refresh_context_all_updates_existing_drafts_without_overwriting_answers() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"
        review.write_all_drafts(evidence_dir)
        for path in evidence_dir.glob("*.decision.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload.pop("current_artifact_context")
            payload["reviewed_by"] = "Owner In Progress"
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        assert review.refresh_all_context(evidence_dir) == 0

        refreshed = json.loads((evidence_dir / "src-the-verge.decision.json").read_text(encoding="utf-8"))
        assert refreshed["reviewed_by"] == "Owner In Progress"
        assert refreshed["decision"] == "TEMPLATE_DECISION"
        assert refreshed["current_artifact_context"]["source_registry_row"]["Source"] == "The Verge"


def test_status_reports_template_drafts_as_invalid() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"
        review.write_all_drafts(evidence_dir)
        output = StringIO()

        with redirect_stdout(output):
            assert review.decision_status(evidence_dir) == 0

        text = output.getvalue()
        assert "src-the-verge\tinvalid\tTEMPLATE_DECISION" in text
        assert "Source owner decision status: 0 valid, 25 invalid, 0 missing, 25 open items" in text


def test_status_reports_completed_drafts_as_valid() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"
        write_completed_open_decisions(evidence_dir, "needs_review")
        output = StringIO()

        with redirect_stdout(output):
            assert review.decision_status(evidence_dir) == 0

        text = output.getvalue()
        assert "src-the-verge\tvalid\tneeds_review\tready to apply" in text
        assert "Source owner decision status: 25 valid, 0 invalid, 0 missing, 25 open items" in text


def test_validate_all_fails_for_template_drafts() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"
        review.write_all_drafts(evidence_dir)

        assert review.validate_all_decisions(evidence_dir) == 1


def test_validate_all_passes_completed_open_reviews() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"
        write_completed_open_decisions(evidence_dir, "needs_review")

        assert review.validate_all_decisions(evidence_dir) == 0


def test_decision_rejects_placeholder_evidence_note() -> None:
    with isolated_artifacts() as tmp:
        payload = decision_payload("needs_review")
        payload["evidence_checked"][0]["url_or_note"] = "TBD"
        path = write_decision(tmp, payload)

        assert_review_error(path, "each evidence item needs url_or_note must be a concrete review note")


def test_decision_rejects_placeholder_owner_answer() -> None:
    with isolated_artifacts() as tmp:
        payload = decision_payload("needs_review")
        payload["owner_question_answers"][0]["answer"] = "unknown"
        path = write_decision(tmp, payload)

        assert_review_error(path, "each owner question needs an answer must be a concrete review note")


def test_apply_all_rejects_template_drafts_without_writing() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"
        review.write_all_drafts(evidence_dir)
        before = artifact_snapshot(tmp)

        assert review.apply_all_decisions(evidence_dir, dry_run=False) == 1
        assert artifact_snapshot(tmp) == before


def test_apply_all_dry_run_validates_without_writing() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"
        write_completed_open_decisions(evidence_dir, "needs_review")
        before = artifact_snapshot(tmp)

        assert review.apply_all_decisions(evidence_dir, dry_run=True) == 0
        assert artifact_snapshot(tmp) == before


def test_apply_all_applies_completed_open_reviews() -> None:
    with isolated_artifacts() as tmp:
        evidence_dir = tmp / "evidence/source-owner-reviews"
        write_completed_open_decisions(evidence_dir, "blocked")

        assert review.apply_all_decisions(evidence_dir, dry_run=False) == 0

        review_text = (tmp / "docs/source-eligibility-reviews.md").read_text(encoding="utf-8")
        policy = source_policy(tmp, "src-the-verge")

        assert "| src-the-verge | blocked |" in review_text
        assert "| src-techcrunch | blocked |" in review_text
        assert policy["eligibility_state"] == "blocked"
        assert policy["production_auto_ingestion"] is False
        assert policy["requires_owner_review"] is False
        assert not queued_source_ids(tmp)


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
    test_draft_includes_current_artifact_context()
    test_draft_all_writes_every_open_review_without_overwriting_existing()
    test_packet_includes_review_context_and_commands()
    test_packet_all_writes_every_open_packet()
    test_packet_index_groups_status_and_paths()
    test_packet_index_writes_index_file()
    test_review_worksheet_includes_decision_fields_and_prompts()
    test_review_worksheet_writes_worksheet_file()
    test_batch_plan_groups_open_items_and_paths()
    test_batch_plan_writes_batch_plan_file()
    test_refresh_context_all_updates_existing_drafts_without_overwriting_answers()
    test_status_reports_template_drafts_as_invalid()
    test_status_reports_completed_drafts_as_valid()
    test_validate_all_fails_for_template_drafts()
    test_validate_all_passes_completed_open_reviews()
    test_decision_rejects_placeholder_evidence_note()
    test_decision_rejects_placeholder_owner_answer()
    test_apply_all_rejects_template_drafts_without_writing()
    test_apply_all_dry_run_validates_without_writing()
    test_apply_all_applies_completed_open_reviews()
    test_blocked_decision_updates_artifacts_and_closes_queue()
    test_needs_review_decision_keeps_queue_open()
    print("source owner review decision tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
