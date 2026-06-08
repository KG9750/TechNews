#!/usr/bin/env python3
"""Regression tests for foundational product modules."""

from __future__ import annotations

import json
import sys
from tempfile import TemporaryDirectory
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from technews_briefing.contracts import (  # noqa: E402
    ArchiveMetadata,
    BriefingItem,
    CandidateItem,
    ContractError,
)
from technews_briefing.archive_package import (  # noqa: E402
    ArchivePackageError,
    archive_package_path,
    write_archive_package,
)
from technews_briefing.briefing_generation import generate_briefing  # noqa: E402
from technews_briefing.ranking import RankingInput, rank_candidates  # noqa: E402
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
GOLDEN_EVENT_KEYS = {
    "sample-002-apple-intelligence": "event-apple-intelligence-2024-06",
    "sample-021-duplicate-apple-ai-coverage": "event-apple-intelligence-2024-06",
}
GOLDEN_TRUST_BY_SOURCE_TYPE = {
    "academic_source": "academic",
    "manual_url": "administrator",
    "public_feed": "official",
}
GOLDEN_EVENT_IMPACT = {
    "sample-001-openai-gpt-4o": 5,
    "sample-002-apple-intelligence": 5,
    "sample-010-github-copilot-workspace": 4,
    "sample-011-kubernetes-130": 2,
    "sample-016-attention-is-all-you-need": 4,
    "sample-020-single-source-leak": 5,
    "sample-021-duplicate-apple-ai-coverage": 4,
}
ARCHIVE_TEST_CONNECTOR_STATUS = {
    "src-openai-news": {"status": "completed", "item_count": 1},
    "src-manual-url": {"status": "completed", "item_count": 1},
}
ARCHIVE_TEST_DELIVERY_STATUS = {
    "feishu_group_demo": {"status": "skipped", "reason": "product module test does not call Feishu"},
}
ARCHIVE_TEST_MODEL_USAGE_SUMMARY = {
    "provider": "fixture",
    "model": "not_called",
    "task_count": 0,
    "request_count": 0,
    "failure_count": 0,
    "notes": "Product module test uses deterministic fixtures.",
}


def load_json(path: str):
    with (ROOT / path).open(encoding="utf-8") as handle:
        return json.load(handle)


def load_json_from_path(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def golden_sample(fixture_id: str) -> dict[str, object]:
    for item in load_json("fixtures/golden-samples/items.json"):
        if item["fixture_id"] == fixture_id:
            return item
    raise AssertionError(f"missing golden sample: {fixture_id}")


def ranking_input_from_golden(
    fixture_id: str,
    *,
    related_history: tuple[dict[str, object], ...] = (),
) -> RankingInput:
    item = golden_sample(fixture_id)
    metadata = item["raw_source_metadata"]
    expected_candidate = item["expected_candidate_item"]
    expected_classification = item["expected_classification"]
    expected_selection = item["expected_selection"]
    source_url = metadata["source_url"]
    source_media = None
    if "source_media" in item["scenario_tags"]:
        source_media = {
            "url": f"{source_url}#source-media",
            "kind": "open_graph_image",
            "attribution": metadata["source_name"],
            "eligibility_note": "Golden sample metadata-only source media fixture.",
        }

    candidate = CandidateItem.from_mapping(
        {
            "id": f"cand_{fixture_id.replace('-', '_')}",
            "run_id": "run_2026-06-01_golden_ranking",
            "source_id": f"src_{fixture_id.replace('-', '_')}",
            "source_type": expected_candidate["source_type"],
            "source_name": metadata["source_name"],
            "original_title": metadata["original_title"],
            "source_url": source_url,
            "original_source_anchor": {
                "source_name": metadata["source_name"],
                "original_title": metadata["original_title"],
                "source_url": source_url,
            },
            "dedupe_key": f"{metadata['source_name']}|{source_url}",
            "event_key": GOLDEN_EVENT_KEYS.get(fixture_id),
            "published_at": metadata["published_at"],
            "discovered_at": "2024-07-25T08:00:00Z",
            "language": "en",
            "section_hints": [expected_classification["section"]],
            "source_media": source_media,
            "eligibility_state": expected_candidate["eligibility_state"],
            "eligibility_notes": "Golden sample ranking fixture.",
            "raw_metadata": {
                "fixture_id": fixture_id,
                "scenario_tags": item["scenario_tags"],
            },
        }
    )
    return RankingInput(
        candidate=candidate,
        section=expected_classification["section"],
        subcategory=expected_classification.get("subcategory"),
        source_trust=GOLDEN_TRUST_BY_SOURCE_TYPE[expected_candidate["source_type"]],
        event_impact=GOLDEN_EVENT_IMPACT[fixture_id],
        confidence_level=expected_selection["confidence_level"],
        confidence_notice=expected_selection.get("confidence_notice"),
        original_material_available=True,
        related_history=related_history,
    )


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


def test_ranker_selects_and_excludes_golden_samples_with_structured_rationales() -> None:
    result = rank_candidates(
        (
            ranking_input_from_golden("sample-001-openai-gpt-4o"),
            ranking_input_from_golden("sample-002-apple-intelligence"),
            ranking_input_from_golden("sample-010-github-copilot-workspace"),
            ranking_input_from_golden("sample-011-kubernetes-130"),
            ranking_input_from_golden("sample-016-attention-is-all-you-need"),
            ranking_input_from_golden("sample-020-single-source-leak"),
            ranking_input_from_golden("sample-021-duplicate-apple-ai-coverage"),
        ),
        subscribed_sections={"AI", "Software", "Academic Progress", "Hardware"},
        run_started_at="2024-07-25T08:00:00Z",
        max_selected=5,
    )
    selected_ids = {item.candidate.raw_metadata["fixture_id"] for item in result.selected}
    excluded_ids = {item.candidate.raw_metadata["fixture_id"] for item in result.excluded}
    selected_by_id = {item.candidate.raw_metadata["fixture_id"]: item for item in result.selected}
    excluded_by_id = {item.candidate.raw_metadata["fixture_id"]: item for item in result.excluded}

    assert "sample-001-openai-gpt-4o" in selected_ids
    assert "sample-010-github-copilot-workspace" in selected_ids
    assert "sample-016-attention-is-all-you-need" in selected_ids
    assert "sample-020-single-source-leak" in selected_ids
    assert "sample-011-kubernetes-130" in excluded_ids
    assert "sample-021-duplicate-apple-ai-coverage" in excluded_ids
    assert selected_by_id["sample-001-openai-gpt-4o"].candidate.source_media is not None
    assert selected_by_id["sample-016-attention-is-all-you-need"].candidate.source_type == "academic_source"
    assert excluded_by_id["sample-011-kubernetes-130"].candidate.source_media is None

    for selected in result.selected:
        rationale = selected.selection_rationale.as_mapping()
        assert rationale["summary"]
        assert selected.candidate.original_source_anchor.source_url
        assert any(signal.startswith("score:") for signal in rationale["signals"])
        assert any(signal.startswith("confidence:") for signal in rationale["signals"])

    archive_exclusions = result.archive_excluded_candidates()
    assert all(record["candidate_id"] and record["selection_rationale"] for record in archive_exclusions)


def test_ranker_merges_duplicate_apple_intelligence_coverage() -> None:
    result = rank_candidates(
        (
            ranking_input_from_golden("sample-002-apple-intelligence"),
            ranking_input_from_golden("sample-021-duplicate-apple-ai-coverage"),
        ),
        subscribed_sections={"AI", "Technology Industry Progress"},
        run_started_at="2024-07-25T08:00:00Z",
        max_selected=3,
    )

    assert len(result.selected) == 1
    selected = result.selected[0]
    assert selected.candidate.raw_metadata["fixture_id"] == "sample-002-apple-intelligence"
    assert len(selected.corroborating_sources) == 1
    assert selected.corroborating_sources[0].source_name == "TechCrunch"

    duplicate = result.excluded[0]
    assert duplicate.reason == "duplicate_coverage"
    assert duplicate.duplicate_of == selected.candidate.id
    assert duplicate.archive_record()["duplicate_of"] == selected.candidate.id


def test_ranker_preserves_low_confidence_notice_and_related_history_hooks() -> None:
    result = rank_candidates(
        (
            ranking_input_from_golden(
                "sample-020-single-source-leak",
                related_history=(
                    {
                        "archive_date": "2024-07-24",
                        "candidate_id": "cand_previous_ai_hardware_rumor",
                        "relationship": "follow_up",
                    },
                ),
            ),
        ),
        subscribed_sections={"Hardware"},
        run_started_at="2024-07-25T08:00:00Z",
        max_selected=1,
    )

    selected = result.selected[0]
    assert selected.confidence_level == "low"
    assert selected.confidence_notice
    assert selected.related_history[0]["relationship"] == "follow_up"
    assert "confidence:low" in selected.selection_rationale.signals
    assert "related_history:1" in selected.selection_rationale.signals


def test_briefing_generator_creates_contract_items_and_section_groups() -> None:
    result = rank_candidates(
        (
            ranking_input_from_golden("sample-001-openai-gpt-4o"),
            ranking_input_from_golden("sample-010-github-copilot-workspace"),
            ranking_input_from_golden("sample-020-single-source-leak"),
        ),
        subscribed_sections={"AI", "Software", "Hardware"},
        run_started_at="2024-07-25T08:00:00Z",
        max_selected=3,
    )

    briefing = generate_briefing(result.selected)
    items_by_candidate_id = {item.candidate_id: item for item in briefing.items}
    openai = items_by_candidate_id["cand_sample_001_openai_gpt_4o"]
    low_confidence = items_by_candidate_id["cand_sample_020_single_source_leak"]

    assert len(briefing.items) == 3
    assert {group.section for group in briefing.groups} == {"AI", "Software", "Hardware"}
    assert openai.source_media is not None
    assert openai.media_attribution is not None
    assert openai.media_attribution["source_url"] == openai.source_media.url
    assert openai.id not in briefing.media_fallbacks
    assert openai.original_source_anchor.source_url == "https://openai.com/index/hello-gpt-4o/"
    assert 3 <= len(openai.bullets_zh) <= 4

    assert low_confidence.confidence_level == "low"
    assert low_confidence.confidence_notice is not None
    assert low_confidence.confidence_notice.display_text_zh.startswith("置信提示：")
    assert low_confidence.confidence_notice.supporting_sources[0].source_url == (
        "https://example.invalid/manual-low-confidence-fixture"
    )
    assert low_confidence.source_media is None
    assert "不使用 AI 生成新闻图" in briefing.media_fallbacks[low_confidence.id].display_text_zh


def test_briefing_generator_preserves_deep_dive_detail_links_and_sources() -> None:
    result = rank_candidates(
        (
            ranking_input_from_golden("sample-002-apple-intelligence"),
            ranking_input_from_golden("sample-021-duplicate-apple-ai-coverage"),
        ),
        subscribed_sections={"AI", "Technology Industry Progress"},
        run_started_at="2024-07-25T08:00:00Z",
        max_selected=3,
    )

    briefing = generate_briefing(result.selected, deep_dive_base_path="archive/deep-dive")
    item = briefing.items[0]
    detail = briefing.deep_dive_for_item(item.id)

    assert item.candidate_id == "cand_sample_002_apple_intelligence"
    assert detail.href == f"archive/deep-dive/{item.id}.html"
    assert detail.briefing_item_id == item.id
    assert [source.source_name for source in detail.source_list] == ["Apple Newsroom", "TechCrunch"]
    assert detail.selection_rationale["summary"]
    assert detail.candidate_metadata["candidate_id"] == item.candidate_id
    assert detail.media_attribution is not None
    assert detail.media_fallback is None


def test_briefing_generator_uses_structured_no_media_fallback_for_academic_items() -> None:
    result = rank_candidates(
        (ranking_input_from_golden("sample-016-attention-is-all-you-need"),),
        subscribed_sections={"Academic Progress"},
        run_started_at="2024-07-25T08:00:00Z",
        max_selected=1,
    )

    briefing = generate_briefing(result.selected)
    item = briefing.items[0]
    detail = briefing.deep_dive_for_item(item.id)

    assert item.section == "Academic Progress"
    assert item.source_media is None
    assert item.media_attribution is None
    assert item.confidence_notice is None
    assert item.id in briefing.media_fallbacks
    assert detail.media_fallback is not None
    assert detail.media_fallback.reason == "no_source_media"
    assert detail.source_list[0].source_url == "https://arxiv.org/abs/1706.03762"
    assert "AI 聊天" in detail.summary_zh


def archive_test_briefing():
    result = rank_candidates(
        (
            ranking_input_from_golden("sample-001-openai-gpt-4o"),
            ranking_input_from_golden("sample-020-single-source-leak"),
            ranking_input_from_golden("sample-011-kubernetes-130"),
        ),
        subscribed_sections={"AI", "Hardware", "Software"},
        run_started_at="2024-07-25T08:00:00Z",
        max_selected=2,
    )
    return generate_briefing(result.selected), result.excluded


def test_archive_package_path_uses_date_domain_segments() -> None:
    path = archive_package_path(
        Path("archives"),
        generated_at="2026-06-01T07:30:00Z",
        domain_template="technology",
    )

    assert path == Path("archives/2026-06-01/technology")
    assert_raises(
        ArchivePackageError,
        lambda: archive_package_path(
            Path("archives"),
            generated_at="2026-06-01T07:30:00Z",
            domain_template="../technology",
        ),
        "single path segment",
    )


def test_archive_package_writes_local_files_and_failed_sync_metadata() -> None:
    briefing, excluded = archive_test_briefing()
    with TemporaryDirectory() as tmpdir:
        result = write_archive_package(
            briefing,
            local_root=Path(tmpdir) / "archives",
            generated_at="2026-06-01T07:30:00Z",
            excluded_candidates=excluded,
            connector_status=ARCHIVE_TEST_CONNECTOR_STATUS,
            delivery_status=ARCHIVE_TEST_DELIVERY_STATUS,
            model_usage_summary=ARCHIVE_TEST_MODEL_USAGE_SUMMARY,
        )

        assert (result.local_package_path / "briefing.html").exists()
        assert (result.local_package_path / "briefing.md").exists()
        assert (result.local_package_path / "metadata.json").exists()
        assert (result.local_package_path / "media/README.md").exists()
        assert (result.local_package_path / f"deep-dive/{briefing.items[0].id}.html").exists()
        assert result.metadata.sync_status["local_archive"].status == "local_written"
        assert result.metadata.sync_status["remote_sync"].status == "failed"
        assert result.metadata.sync_status["remote_sync"].retryable is True
        assert result.metadata.excluded_candidates
        assert "Remote sync failed" in result.metadata.warnings[-1]

        metadata = ArchiveMetadata.from_mapping(load_json_from_path(result.local_package_path / "metadata.json"))
        selected = metadata.selected_items[0]
        assert selected["deep_dive_href"].startswith("deep-dive/")
        assert selected["original_source_anchor"]["source_url"]
        assert "briefing.md" in result.files_written


def test_archive_package_syncs_to_configured_target() -> None:
    briefing, excluded = archive_test_briefing()
    with TemporaryDirectory() as tmpdir:
        local_root = Path(tmpdir) / "archives"
        sync_target = Path(tmpdir) / "synced"
        result = write_archive_package(
            briefing,
            local_root=local_root,
            sync_target=sync_target,
            generated_at="2026-06-01T07:30:00Z",
            excluded_candidates=excluded,
            connector_status=ARCHIVE_TEST_CONNECTOR_STATUS,
            delivery_status=ARCHIVE_TEST_DELIVERY_STATUS,
            model_usage_summary=ARCHIVE_TEST_MODEL_USAGE_SUMMARY,
        )

        assert result.remote_package_path == sync_target / "2026-06-01/technology"
        assert result.metadata.sync_status["remote_sync"].status == "synced"
        assert result.metadata.sync_status["remote_sync"].retryable is False
        assert (result.remote_package_path / "briefing.html").exists()
        remote_metadata = ArchiveMetadata.from_mapping(
            load_json_from_path(result.remote_package_path / "metadata.json")
        )
        assert remote_metadata.sync_status["remote_sync"].status == "synced"


def test_archive_package_keeps_local_output_when_sync_target_is_unavailable() -> None:
    briefing, excluded = archive_test_briefing()
    with TemporaryDirectory() as tmpdir:
        sync_target = Path(tmpdir) / "sync-target-file"
        sync_target.write_text("not a directory", encoding="utf-8")
        result = write_archive_package(
            briefing,
            local_root=Path(tmpdir) / "archives",
            sync_target=sync_target,
            generated_at="2026-06-01T07:30:00Z",
            excluded_candidates=excluded,
            connector_status=ARCHIVE_TEST_CONNECTOR_STATUS,
            delivery_status=ARCHIVE_TEST_DELIVERY_STATUS,
            model_usage_summary=ARCHIVE_TEST_MODEL_USAGE_SUMMARY,
        )

        assert result.metadata.sync_status["remote_sync"].status == "failed"
        assert result.metadata.sync_status["remote_sync"].failure_reason
        assert result.metadata.sync_status["remote_sync"].metadata["retry_state"] == "pending_retry"
        assert (result.local_package_path / "briefing.html").exists()
        assert (result.local_package_path / "metadata.json").exists()


def test_archive_storage_fixture_contains_complete_package_shape() -> None:
    package = ROOT / "fixtures/archive-storage/local-archive/2026-06-01/technology"
    assert (package / "briefing.html").exists()
    assert (package / "briefing.md").exists()
    assert (package / "metadata.json").exists()
    assert (package / "media/README.md").exists()
    metadata = ArchiveMetadata.from_mapping(load_json_from_path(package / "metadata.json"))
    assert metadata.sync_status["local_archive"].status == "local_written"
    assert metadata.sync_status["remote_sync"].status == "failed"


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
        test_ranker_selects_and_excludes_golden_samples_with_structured_rationales,
        test_ranker_merges_duplicate_apple_intelligence_coverage,
        test_ranker_preserves_low_confidence_notice_and_related_history_hooks,
        test_briefing_generator_creates_contract_items_and_section_groups,
        test_briefing_generator_preserves_deep_dive_detail_links_and_sources,
        test_briefing_generator_uses_structured_no_media_fallback_for_academic_items,
        test_archive_package_path_uses_date_domain_segments,
        test_archive_package_writes_local_files_and_failed_sync_metadata,
        test_archive_package_syncs_to_configured_target,
        test_archive_package_keeps_local_output_when_sync_target_is_unavailable,
        test_archive_storage_fixture_contains_complete_package_shape,
        test_automatic_briefing_run_filters_candidates_through_policy,
        test_product_modules_do_not_import_spike_runners,
    ]
    for test in tests:
        test()
    print("product module tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
