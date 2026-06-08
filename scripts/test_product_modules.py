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
from technews_briefing.source_connectors import (  # noqa: E402
    SourceMetadataInput,
    normalize_source_input,
    run_source_connectors,
)
from technews_briefing.source_policy import SourceAccessPolicy  # noqa: E402
from technews_briefing.source_registry import (  # noqa: E402
    FIRST_VERSION_SOURCE_TYPES,
    SourceRegistry,
    SourceRegistryError,
)
from technews_briefing.taxonomy import TechnologyDomainTemplate  # noqa: E402


EXPECTED_TECHNOLOGY_TEMPLATE = {
    "AI": (
        "Foundation models",
        "Multimodal AI",
        "AI agents",
        "AI infrastructure",
        "Evaluation and safety",
        "AI applications",
        "Open-source AI",
    ),
    "Software": (
        "Developer tools",
        "Programming languages",
        "Cloud and DevOps",
        "Security",
        "Databases and data systems",
        "Open-source projects",
        "SaaS platforms",
    ),
    "Hardware": (
        "Semiconductors",
        "AI accelerators",
        "Data center hardware",
        "Consumer devices",
        "Manufacturing and supply chain",
        "Networking and connectivity",
        "Energy and cooling",
    ),
    "Embodied Intelligence": (
        "Robot body",
        "Data collection",
        "Model training",
        "Recent papers",
        "Financing",
        "Deployment and pilots",
        "Simulation and evaluation",
    ),
    "Academic Progress": (
        "AI papers",
        "Robotics papers",
        "Systems papers",
        "Hardware research",
        "Datasets and benchmarks",
        "Research institutions",
        "Reproducibility and evaluation",
    ),
    "Technology Industry Progress": (
        "Funding and investment",
        "M&A and partnerships",
        "Regulation and policy",
        "Antitrust and litigation",
        "Earnings and market signals",
        "Talent and organization",
        "Platform strategy",
    ),
}
REQUIRED_EMBODIED_SUBCATEGORIES = {
    "Robot body",
    "Data collection",
    "Model training",
    "Recent papers",
    "Financing",
}


def load_json(path: str):
    with (ROOT / path).open(encoding="utf-8") as handle:
        return json.load(handle)


def load_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


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


def test_technology_taxonomy_loads_configured_mvp_template() -> None:
    template = TechnologyDomainTemplate.from_markdown_file(ROOT / "docs/taxonomy/technology-domain-template.md")
    loaded = {section.name: section.subcategories for section in template.sections}
    assert loaded == EXPECTED_TECHNOLOGY_TEMPLATE

    template.require_mvp_coverage(
        required_sections=set(EXPECTED_TECHNOLOGY_TEMPLATE),
        required_embodied_subcategories=REQUIRED_EMBODIED_SUBCATEGORIES,
    )
    assert template.name == "technology"
    assert len(template.section_names()) == 6


def test_source_registry_loads_seed_sources_and_supported_first_version_types() -> None:
    registry = SourceRegistry.from_markdown_file(ROOT / "docs/source-registry.md")
    assert len(registry.entries()) >= 30
    assert len(registry.first_version_sources()) >= 30
    assert registry.deferred_sources()
    assert registry.first_version_source_types() == FIRST_VERSION_SOURCE_TYPES

    arxiv = registry.entry_for("src-arxiv-cs-ai")
    assert arxiv.source_type == "academic_source"
    assert arxiv.primary_section == "Academic Progress"
    assert arxiv.section_hints() == ("Academic Progress", "AI")
    assert arxiv.trust_tier == "academic"
    assert arxiv.media_availability == "paper metadata"
    assert arxiv.eligibility_notes

    manual = registry.require_first_version_connector("src-manual-url")
    assert manual.source_type == "manual_url"


def test_deferred_sources_stay_visible_but_cannot_run_as_first_version_connectors() -> None:
    registry = SourceRegistry.from_markdown_file(ROOT / "docs/source-registry.md")
    deferred_ids = {entry.id for entry in registry.deferred_sources()}
    connector_ids = {entry.id for entry in registry.first_version_connectors()}

    assert {"src-hackaday", "src-x", "src-linkedin", "src-facebook"} <= deferred_ids
    assert "src-x" not in connector_ids
    assert registry.entry_for("src-x").source_type == "deferred_connector"
    assert_raises(
        SourceRegistryError,
        lambda: registry.require_first_version_connector("src-x"),
        "not a first-version source",
    )


def test_source_registry_and_access_policy_share_first_version_source_ids() -> None:
    registry = SourceRegistry.from_markdown_file(ROOT / "docs/source-registry.md")
    policy = SourceAccessPolicy.from_file(ROOT / "fixtures/source-ingestion/source-access-policy.json")

    assert {entry.id for entry in registry.first_version_sources()} == {
        row.source_id for row in policy.production_enabled_sources()
    } | {row.source_id for row in policy.rows_by_eligibility("deferred")}


def test_source_registry_requires_policy_for_production_enabled_connectors() -> None:
    registry = SourceRegistry.from_markdown_file(ROOT / "docs/source-registry.md")
    policy = SourceAccessPolicy.from_file(ROOT / "fixtures/source-ingestion/source-access-policy.json")
    production_connector_ids = {entry.id for entry in registry.production_enabled_connectors(policy)}

    assert production_connector_ids == {
        "src-rust-blog",
        "src-kubernetes-blog",
        "src-arxiv-cs-ai",
        "src-arxiv-cs-lg",
        "src-arxiv-cs-ro",
        "src-arxiv-cs-cv",
        "src-arxiv-cs-cl",
    }
    assert "src-the-verge" in {entry.id for entry in registry.first_version_sources()}
    assert_raises(
        SourceRegistryError,
        lambda: registry.require_production_enabled_connector("src-the-verge", policy),
        "not enabled for production auto-ingestion",
    )


def test_source_connectors_normalize_each_first_version_source_type() -> None:
    registry = SourceRegistry.from_markdown_file(ROOT / "docs/source-registry.md")
    policy = SourceAccessPolicy.from_file(ROOT / "fixtures/source-ingestion/source-access-policy.json")
    run_id = "run_2026-06-01_source_connector_test"
    discovered_at = "2026-06-01T06:02:34Z"

    public_feed = normalize_source_input(
        registry.entry_for("src-rust-blog"),
        policy.row_for("src-rust-blog"),
        SourceMetadataInput(
            source_id="src-rust-blog",
            content_type="application/rss+xml",
            content=load_text("fixtures/source-ingestion/recorded-public-feed.rss"),
        ),
        run_id=run_id,
        discovered_at=discovered_at,
    )
    academic = normalize_source_input(
        registry.entry_for("src-arxiv-cs-ai"),
        policy.row_for("src-arxiv-cs-ai"),
        SourceMetadataInput(
            source_id="src-arxiv-cs-ai",
            content_type="application/atom+xml",
            content=load_text("fixtures/source-ingestion/recorded-arxiv.atom"),
        ),
        run_id=run_id,
        discovered_at=discovered_at,
    )
    manual = normalize_source_input(
        registry.entry_for("src-manual-url"),
        policy.row_for("src-manual-url"),
        SourceMetadataInput(
            source_id="src-manual-url",
            content_type="text/html",
            content=load_text("fixtures/source-ingestion/recorded-manual-url.html"),
            fetched_url="https://www.apple.com/newsroom/2024/05/apple-introduces-m4-chip/",
        ),
        run_id=run_id,
        discovered_at=discovered_at,
    )

    assert {public_feed.source_type, academic.source_type, manual.source_type} == {
        "public_feed",
        "academic_source",
        "manual_url",
    }
    assert public_feed.original_source_anchor.source_name == "Rust Blog"
    assert academic.original_source_anchor.source_url == "http://arxiv.org/abs/2605.31603v1"
    assert manual.original_source_anchor.source_name == "Apple Newsroom"
    assert manual.raw_metadata["open_graph_image_url"].startswith("https://www.apple.com/newsroom/")
    assert public_feed.raw_metadata["description_excerpt"]
    assert academic.raw_metadata["summary_excerpt"]


def test_source_connectors_record_failures_and_policy_skips_without_aborting_run() -> None:
    registry = SourceRegistry.from_markdown_file(ROOT / "docs/source-registry.md")
    policy = SourceAccessPolicy.from_file(ROOT / "fixtures/source-ingestion/source-access-policy.json")
    results = run_source_connectors(
        registry,
        policy,
        (
            SourceMetadataInput(
                source_id="src-rust-blog",
                content_type="application/rss+xml",
                content=load_text("fixtures/source-ingestion/recorded-public-feed.rss"),
                completed_at="2026-06-01T06:03:00Z",
            ),
            SourceMetadataInput(
                source_id="src-arxiv-cs-ai",
                content_type="application/atom+xml",
                error="fixture upstream 503",
                completed_at="2026-06-01T06:03:01Z",
            ),
            SourceMetadataInput(
                source_id="src-the-verge",
                content_type="application/rss+xml",
                content=load_text("fixtures/source-ingestion/recorded-public-feed.rss"),
                completed_at="2026-06-01T06:03:02Z",
            ),
            SourceMetadataInput(
                source_id="src-manual-url",
                content_type="text/html",
                content=load_text("fixtures/source-ingestion/recorded-manual-url.html"),
                completed_at="2026-06-01T06:03:03Z",
            ),
        ),
        run_id="run_2026-06-01_source_connector_policy_test",
        discovered_at="2026-06-01T06:02:34Z",
        delivery_deadline="2026-06-01T07:00:00Z",
    )
    by_source = {result.source_id: result for result in results}

    assert by_source["src-rust-blog"].status == "completed"
    assert by_source["src-arxiv-cs-ai"].status == "failed"
    assert by_source["src-the-verge"].status == "skipped"
    assert "probe-only" in by_source["src-the-verge"].warning
    assert by_source["src-manual-url"].status == "skipped"
    assert "manual-only" in by_source["src-manual-url"].warning

    prepared = AutomaticBriefingRun(policy).prepare(
        run_id="run_2026-06-01_source_connector_policy_test",
        domain_template="technology",
        scheduled_for="2026-06-01T06:00:00Z",
        delivery_deadline="2026-06-01T07:00:00Z",
        started_at="2026-06-01T06:01:00Z",
        connector_results=results,
    )
    assert [candidate.source_id for candidate in prepared.accepted_candidates] == ["src-rust-blog"]
    assert prepared.run.connector_status["src-arxiv-cs-ai"].status == "failed"
    assert prepared.run.connector_status["src-the-verge"].status == "skipped"


def test_source_connector_late_results_are_cut_off_at_delivery_deadline() -> None:
    registry = SourceRegistry.from_markdown_file(ROOT / "docs/source-registry.md")
    policy = SourceAccessPolicy.from_file(ROOT / "fixtures/source-ingestion/source-access-policy.json")
    results = run_source_connectors(
        registry,
        policy,
        (
            SourceMetadataInput(
                source_id="src-arxiv-cs-ai",
                content_type="application/atom+xml",
                content=load_text("fixtures/source-ingestion/recorded-arxiv.atom"),
                completed_at="2026-06-01T07:00:01Z",
            ),
        ),
        run_id="run_2026-06-01_source_connector_timeout_test",
        discovered_at="2026-06-01T06:02:34Z",
        delivery_deadline="2026-06-01T07:00:00Z",
    )

    assert results[0].source_id == "src-arxiv-cs-ai"
    assert results[0].status == "timeout"
    assert not results[0].candidates
    assert "delivery deadline" in results[0].warning


def test_source_connector_output_matches_recorded_candidate_fixture_anchor() -> None:
    registry = SourceRegistry.from_markdown_file(ROOT / "docs/source-registry.md")
    policy = SourceAccessPolicy.from_file(ROOT / "fixtures/source-ingestion/source-access-policy.json")
    expected = load_json("fixtures/source-ingestion/candidate-items.json")[1]
    generated = normalize_source_input(
        registry.entry_for("src-arxiv-cs-ai"),
        policy.row_for("src-arxiv-cs-ai"),
        SourceMetadataInput(
            source_id="src-arxiv-cs-ai",
            content_type="application/atom+xml",
            content=load_text("fixtures/source-ingestion/recorded-arxiv.atom"),
        ),
        run_id=expected["run_id"],
        discovered_at=expected["discovered_at"],
    )

    assert generated.original_title == expected["original_title"]
    assert generated.source_url == expected["source_url"]
    assert generated.original_source_anchor.source_name == expected["original_source_anchor"]["source_name"]
    assert generated.raw_metadata["authors"][:2] == expected["raw_metadata"]["authors"][:2]
    assert generated.raw_metadata["summary_excerpt"] == expected["raw_metadata"]["summary_excerpt"]


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
        test_technology_taxonomy_loads_configured_mvp_template,
        test_source_registry_loads_seed_sources_and_supported_first_version_types,
        test_deferred_sources_stay_visible_but_cannot_run_as_first_version_connectors,
        test_source_registry_and_access_policy_share_first_version_source_ids,
        test_source_registry_requires_policy_for_production_enabled_connectors,
        test_source_connectors_normalize_each_first_version_source_type,
        test_source_connectors_record_failures_and_policy_skips_without_aborting_run,
        test_source_connector_late_results_are_cut_off_at_delivery_deadline,
        test_source_connector_output_matches_recorded_candidate_fixture_anchor,
        test_automatic_briefing_run_filters_candidates_through_policy,
        test_product_modules_do_not_import_spike_runners,
    ]
    for test in tests:
        test()
    print("product module tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
