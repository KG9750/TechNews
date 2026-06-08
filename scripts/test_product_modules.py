#!/usr/bin/env python3
"""Regression tests for foundational product modules."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from technews_briefing.contracts import (  # noqa: E402
    ArchiveMetadata,
    BriefingItem,
    CandidateItem,
    ContractError,
)
from technews_briefing.run import AutomaticBriefingRun, ConnectorResult  # noqa: E402
from technews_briefing.source_policy import SourceAccessPolicy  # noqa: E402


def load_json(path: str):
    with (ROOT / path).open(encoding="utf-8") as handle:
        return json.load(handle)


def assert_raises(expected_error: type[Exception], fn, expected_text: str) -> None:
    try:
        fn()
    except expected_error as error:
        assert expected_text in str(error), str(error)
        return
    raise AssertionError(f"expected {expected_error.__name__}: {expected_text}")


def test_contract_models_accept_existing_fixtures() -> None:
    candidates = [
        CandidateItem.from_mapping(item) for item in load_json("fixtures/source-ingestion/candidate-items.json")
    ]
    assert len(candidates) == 3
    assert candidates[1].source_id == "src-arxiv-cs-ai"

    model_output = load_json("fixtures/model-provider/outputs/high-confidence-news.json")
    briefing_item = BriefingItem.from_mapping(model_output["briefing_item"])
    assert briefing_item.confidence_level == "high"
    assert len(briefing_item.bullets_zh) == 3

    archive = ArchiveMetadata.from_mapping(
        load_json("fixtures/archive-storage/local-archive/2026-06-01/technology/metadata.json")
    )
    assert archive.run_id == "run_2026-06-01_archive_storage_spike"
    assert archive.delivery_status["feishu_user_demo"].status == "skipped"
    assert archive.sync_status["remote_sync"].status == "failed"
    assert archive.sync_status["remote_sync"].failure_reason
    assert archive.model_usage_summary.request_count == 0


def test_contract_models_reject_full_body_metadata() -> None:
    payload = dict(load_json("fixtures/source-ingestion/candidate-items.json")[0])
    payload["raw_metadata"] = {"full_text": "do not store complete source bodies"}
    assert_raises(ContractError, lambda: CandidateItem.from_mapping(payload), "full-body keys")


def test_confidence_notice_required_for_non_high_briefing_items() -> None:
    payload = dict(load_json("fixtures/model-provider/outputs/high-confidence-news.json")["briefing_item"])
    payload["confidence_level"] = "low"
    payload["confidence_notice"] = None
    assert_raises(ContractError, lambda: BriefingItem.from_mapping(payload), "confidence_notice is required")


def test_low_confidence_fixture_maps_to_confidence_notice_shape() -> None:
    payload = dict(load_json("fixtures/model-provider/outputs/low-confidence-news.json")["briefing_item"])
    notice_text = payload["confidence_notice"]
    payload["confidence_notice"] = {
        "reason": "single_source_low_confidence",
        "display_text_zh": notice_text,
        "supporting_sources": [payload["original_source_anchor"]],
    }
    briefing_item = BriefingItem.from_mapping(payload)
    assert briefing_item.confidence_level == "low"
    assert briefing_item.confidence_notice is not None


def test_source_media_requires_media_attribution_when_displayed() -> None:
    payload = dict(load_json("fixtures/model-provider/outputs/high-confidence-news.json")["briefing_item"])
    payload["source_media"] = {
        "url": "https://example.invalid/image.jpg",
        "kind": "open_graph_image",
        "attribution": "Example Source",
        "eligibility_note": "Fixture-only media metadata.",
    }
    payload["media_attribution"] = None
    assert_raises(ContractError, lambda: BriefingItem.from_mapping(payload), "media_attribution is required")


def test_status_records_represent_delivery_and_sync_failures() -> None:
    run = AutomaticBriefingRun(
        SourceAccessPolicy.from_file(ROOT / "fixtures/source-ingestion/source-access-policy.json")
    )
    prepared = run.prepare(
        run_id="run_2026-06-01_failure_status",
        domain_template="technology",
        scheduled_for="2026-06-01T00:00:00Z",
        delivery_deadline="2026-06-01T01:00:00Z",
        started_at="2026-06-01T00:05:00Z",
        connector_results=(),
        model_task_status={"ranking": {"status": "failed", "failure_reason": "fixture model failure"}},
        archive_status={
            "remote_sync": {"status": "failed", "failure_reason": "fixture sync failure", "retryable": True}
        },
        feishu_delivery_status={"user": {"status": "failed", "failure_reason": "fixture delivery failure"}},
    )
    assert prepared.run.model_task_status["ranking"].failure_reason == "fixture model failure"
    assert prepared.run.archive_status["remote_sync"].retryable is True
    assert prepared.run.feishu_delivery_status["user"].status == "failed"


def test_failed_status_requires_failure_reason() -> None:
    payload = load_json("fixtures/archive-storage/local-archive/2026-06-01/technology/metadata.json")
    payload["sync_status"]["remote_sync"] = {"status": "failed"}
    assert_raises(ContractError, lambda: ArchiveMetadata.from_mapping(payload), "failure_reason is required")


def test_source_access_policy_centralizes_ingestion_decisions() -> None:
    policy = SourceAccessPolicy.from_file(ROOT / "fixtures/source-ingestion/source-access-policy.json")
    assert len(policy.production_enabled_sources()) == 7
    assert len(policy.rows_by_eligibility("deferred")) == 25

    candidates = [
        CandidateItem.from_mapping(item) for item in load_json("fixtures/source-ingestion/candidate-items.json")
    ]
    github, arxiv, manual = candidates
    assert not policy.evaluate_candidate(github).allowed
    assert policy.evaluate_candidate(arxiv).allowed
    assert not policy.evaluate_candidate(manual).allowed


def test_automatic_briefing_run_filters_candidates_through_policy() -> None:
    policy = SourceAccessPolicy.from_file(ROOT / "fixtures/source-ingestion/source-access-policy.json")
    candidates = [
        CandidateItem.from_mapping(item) for item in load_json("fixtures/source-ingestion/candidate-items.json")
    ]
    run = AutomaticBriefingRun(policy).prepare(
        run_id="run_2026-06-01_test",
        domain_template="technology",
        scheduled_for="2026-06-01T00:00:00Z",
        delivery_deadline="2026-06-01T01:00:00Z",
        started_at="2026-06-01T00:05:00Z",
        connector_results=(
            ConnectorResult(source_id="src-github-blog", status="completed", candidates=(candidates[0],)),
            ConnectorResult(source_id="src-arxiv-cs-ai", status="completed", candidates=(candidates[1],)),
            ConnectorResult(
                source_id="src-manual-url",
                status="partial",
                candidates=(candidates[2],),
                warning="manual URL requires per-item review",
            ),
        ),
    )

    assert [candidate.id for candidate in run.accepted_candidates] == ["cand_arxiv_2605_31603v1"]
    assert {candidate.source_id for candidate in run.excluded_candidates} == {"src-github-blog", "src-manual-url"}
    assert run.run.connector_status["src-manual-url"].status == "partial"
    assert run.run.run_warnings


def test_product_modules_do_not_import_spike_runners() -> None:
    for path in (ROOT / "technews_briefing").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "scripts/spikes" not in text
        assert "feishu_delivery_spike" not in text
        assert "model_provider_spike" not in text
        assert "archive_storage_spike" not in text


def main() -> int:
    tests = [
        test_contract_models_accept_existing_fixtures,
        test_contract_models_reject_full_body_metadata,
        test_confidence_notice_required_for_non_high_briefing_items,
        test_low_confidence_fixture_maps_to_confidence_notice_shape,
        test_source_media_requires_media_attribution_when_displayed,
        test_status_records_represent_delivery_and_sync_failures,
        test_failed_status_requires_failure_reason,
        test_source_access_policy_centralizes_ingestion_decisions,
        test_automatic_briefing_run_filters_candidates_through_policy,
        test_product_modules_do_not_import_spike_runners,
    ]
    for test in tests:
        test()
    print("product module tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
