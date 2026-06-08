"""Fixture-backed end-to-end MVP acceptance run."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping

from .archive_package import ArchivePackageResult, write_archive_package
from .briefing_generation import GeneratedBriefing, generate_briefing
from .contracts import CandidateItem, SourceMedia
from .feishu_delivery import (
    FeishuMessageRequest,
    FeishuRecipient,
    build_delivery_status_map,
    build_feishu_card,
    build_internal_app_message_request,
)
from .operations_console import (
    AdminAuth,
    ConsoleView,
    OperationsConsole,
    OperationsConsoleStore,
    hash_admin_password,
    seed_console_store,
)
from .ranking import RankingInput, RankingResult, rank_candidates
from .run import ConnectorResult, RunPreparation
from .source_connectors import SourceMetadataInput, run_source_connectors
from .source_policy import SourceAccessPolicy
from .source_registry import SourceRegistry


RUN_ID = "run_2026-06-08_e2e_acceptance"
SCHEDULED_FOR = "2026-06-08T00:00:00Z"
STARTED_AT = "2026-06-08T07:55:00Z"
DELIVERY_DEADLINE = "2026-06-08T08:00:00Z"
GENERATED_AT = "2026-06-08T08:00:00Z"
ARCHIVE_URL = "https://archive.example.invalid/2026-06-08/technology/"
FIXTURE_MODEL_USAGE = {
    "provider": "fixture",
    "model": "fixture-e2e-acceptance",
    "task_count": 2,
    "request_count": 2,
    "input_tokens": 1200,
    "output_tokens": 700,
    "latency_ms": 1200,
    "failure_count": 0,
    "notes": "Fixture-backed E2E acceptance does not call a live model provider.",
}


@dataclass(frozen=True)
class E2EAcceptanceResult:
    run: RunPreparation
    ranking: RankingResult
    briefing: GeneratedBriefing
    archive: ArchivePackageResult
    feishu_requests: tuple[FeishuMessageRequest, ...]
    delivery_status: Mapping[str, Mapping[str, object]]
    console_view: ConsoleView
    report: Mapping[str, object]

    @property
    def passed(self) -> bool:
        checklist = self.report.get("checklist", {})
        return isinstance(checklist, Mapping) and all(value is True for value in checklist.values())


def run_fixture_e2e_acceptance(
    *,
    repo_root: Path,
    archive_root: Path,
    sync_target: Path,
) -> E2EAcceptanceResult:
    registry = SourceRegistry.from_markdown_file(repo_root / "docs/source-registry.md")
    policy = SourceAccessPolicy.from_file(repo_root / "fixtures/source-ingestion/source-access-policy.json")
    connector_results = run_source_connectors(
        registry,
        policy,
        _source_inputs(repo_root),
        run_id=RUN_ID,
        discovered_at=STARTED_AT,
        delivery_deadline=DELIVERY_DEADLINE,
    )
    run = _prepare_run(policy, connector_results)
    ranking = _rank_for_acceptance(run.accepted_candidates)
    briefing = generate_briefing(ranking.selected, run_id=RUN_ID)
    card = build_feishu_card(briefing, archive_url=ARCHIVE_URL)
    recipients = _recipients()
    feishu_requests = tuple(build_internal_app_message_request(recipient, card) for recipient in recipients)
    delivery_status = build_delivery_status_map(
        {
            recipients[0]: {"code": 0, "data": {"message_id": "om_fixture_user_e2e"}},
            recipients[1]: {"code": 0, "data": {"message_id": "om_fixture_group_e2e"}},
        }
    )
    archive = write_archive_package(
        briefing,
        local_root=archive_root,
        sync_target=sync_target,
        generated_at=GENERATED_AT,
        domain_template="technology",
        excluded_candidates=ranking.archive_excluded_candidates(),
        connector_status=_connector_status_map(connector_results),
        delivery_status=delivery_status,
        model_usage_summary=FIXTURE_MODEL_USAGE,
    )
    console_view = _console_view(registry, policy, connector_results, briefing, delivery_status, archive)
    report = _redacted_report(
        registry,
        connector_results,
        run,
        ranking,
        briefing,
        archive,
        delivery_status,
        console_view,
    )
    return E2EAcceptanceResult(
        run=run,
        ranking=ranking,
        briefing=briefing,
        archive=archive,
        feishu_requests=feishu_requests,
        delivery_status=delivery_status,
        console_view=console_view,
        report=report,
    )


def write_redacted_report(report: Mapping[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _source_inputs(repo_root: Path) -> tuple[SourceMetadataInput, ...]:
    return (
        SourceMetadataInput(
            source_id="src-rust-blog",
            content_type="application/rss+xml",
            content=_read(repo_root, "fixtures/source-ingestion/recorded-public-feed.rss"),
            completed_at="2026-06-08T07:57:00Z",
        ),
        SourceMetadataInput(
            source_id="src-arxiv-cs-ai",
            content_type="application/atom+xml",
            content=_read(repo_root, "fixtures/source-ingestion/recorded-arxiv.atom"),
            completed_at="2026-06-08T07:57:30Z",
        ),
        SourceMetadataInput(
            source_id="src-manual-url",
            content_type="text/html",
            content=_read(repo_root, "fixtures/source-ingestion/recorded-manual-url.html"),
            fetched_url="https://www.apple.com/newsroom/2024/05/apple-introduces-m4-chip/",
            completed_at="2026-06-08T07:58:00Z",
        ),
        SourceMetadataInput(
            source_id="src-kubernetes-blog",
            content_type="application/rss+xml",
            content=_read(repo_root, "fixtures/source-ingestion/recorded-public-feed.rss"),
            completed_at="2026-06-08T08:00:01Z",
        ),
    )


def _prepare_run(policy: SourceAccessPolicy, connector_results: tuple[ConnectorResult, ...]) -> RunPreparation:
    from .run import AutomaticBriefingRun

    return AutomaticBriefingRun(policy).prepare(
        run_id=RUN_ID,
        domain_template="technology",
        scheduled_for=SCHEDULED_FOR,
        delivery_deadline=DELIVERY_DEADLINE,
        started_at=STARTED_AT,
        connector_results=connector_results,
    )


def _rank_for_acceptance(candidates: tuple[CandidateItem, ...]) -> RankingResult:
    by_source = {candidate.source_id: candidate for candidate in candidates}
    public_candidate = _with_fixture_media(by_source["src-rust-blog"])
    academic_candidate = by_source["src-arxiv-cs-ai"]
    return rank_candidates(
        (
            RankingInput(
                candidate=public_candidate,
                section="Software",
                subcategory="Programming languages",
                source_trust="official",
                event_impact=4,
                confidence_level="high",
                related_history=(
                    {
                        "previous_run_id": "run_2026-06-07_e2e_acceptance",
                        "summary": "Rust language and tooling updates appeared in the previous briefing context.",
                    },
                ),
            ),
            RankingInput(
                candidate=academic_candidate,
                section="Academic Progress",
                subcategory="AI papers",
                source_trust="academic",
                event_impact=4,
                confidence_level="low",
                confidence_notice="论文元数据来自单一来源，尚未经过独立复现。",
            ),
        ),
        subscribed_sections={"Software", "Academic Progress"},
        run_started_at=STARTED_AT,
        max_selected=2,
    )


def _with_fixture_media(candidate: CandidateItem) -> CandidateItem:
    media = SourceMedia.from_mapping(
        {
            "url": f"{candidate.source_url}#source-media",
            "kind": "favicon",
            "attribution": f"{candidate.source_name} metadata fixture",
            "eligibility_note": "Fixture media resolver path validates attribution without downloading media.",
        }
    )
    return replace(candidate, source_media=media)


def _recipients() -> tuple[FeishuRecipient, FeishuRecipient]:
    return (
        FeishuRecipient(
            recipient_key="feishu_user_demo",
            recipient_type="feishu_user",
            receive_id_type="open_id",
            receive_id="fixture_user_open_id",
        ),
        FeishuRecipient(
            recipient_key="feishu_group_demo",
            recipient_type="feishu_group",
            receive_id_type="chat_id",
            receive_id="fixture_group_chat_id",
        ),
    )


def _connector_status_map(results: tuple[ConnectorResult, ...]) -> dict[str, dict[str, object]]:
    status: dict[str, dict[str, object]] = {}
    for result in results:
        row: dict[str, object] = {
            "status": result.status,
            "item_count": len(result.candidates),
        }
        if result.warning:
            row["warning"] = result.warning
        status[result.source_id] = row
    return status


def _console_view(
    registry: SourceRegistry,
    policy: SourceAccessPolicy,
    connector_results: tuple[ConnectorResult, ...],
    briefing: GeneratedBriefing,
    delivery_status: Mapping[str, Mapping[str, object]],
    archive: ArchivePackageResult,
) -> ConsoleView:
    store = OperationsConsoleStore()
    store.initialize()
    seed_console_store(store, _console_seed(registry, policy, connector_results, briefing, delivery_status, archive))
    auth = AdminAuth(
        username="admin",
        password_hash=hash_admin_password("fixture-password", salt=b"e2e-acceptance-salt", iterations=1_000),
        session_secret="fixture-session-secret-for-e2e",
    )
    token = auth.login("admin", "fixture-password", now=1000)
    return OperationsConsole(store=store, auth=auth).dashboard(token, now=1001)


def _console_seed(
    registry: SourceRegistry,
    policy: SourceAccessPolicy,
    connector_results: tuple[ConnectorResult, ...],
    briefing: GeneratedBriefing,
    delivery_status: Mapping[str, Mapping[str, object]],
    archive: ArchivePackageResult,
) -> dict[str, tuple[dict[str, object], ...]]:
    connector_rows = []
    for result in connector_results:
        source = registry.entry_for(result.source_id)
        connector_rows.append(
            {
                "source_id": source.id,
                "name": source.name,
                "source_type": source.source_type,
                "eligibility_state": policy.row_for(source.id).eligibility_state,
                "connector_status": result.status,
                "last_checked_at": GENERATED_AT,
            }
        )

    return {
        "console_config": (
            {"key": "DELIVERY_DEADLINE_LOCAL_TIME", "value": "08:00", "is_secret": False},
            {"key": "DELIVERY_TIMEZONE", "value": "Asia/Shanghai", "is_secret": False},
            {"key": "MODEL_API_KEY", "value": "fixture-model-secret", "is_secret": True},
        ),
        "sources": tuple(connector_rows),
        "taxonomy": tuple(
            {
                "section": group.section,
                "subcategory": group.subcategory or "All",
            }
            for group in briefing.groups
        ),
        "recipients": (
            {
                "recipient_id": "feishu_user_demo",
                "recipient_type": "feishu_user",
                "label": "Fixture user",
                "enabled": 1,
            },
            {
                "recipient_id": "feishu_group_demo",
                "recipient_type": "feishu_group",
                "label": "Fixture group",
                "enabled": 1,
            },
        ),
        "subscriptions": (
            {"recipient_id": "feishu_user_demo", "section": "Software", "subcategory": "Programming languages"},
            {"recipient_id": "feishu_group_demo", "section": "Academic Progress", "subcategory": "AI papers"},
        ),
        "runs": (
            {
                "run_id": RUN_ID,
                "domain_template": "technology",
                "scheduled_for": SCHEDULED_FOR,
                "run_status": "completed",
                "archive_url": ARCHIVE_URL,
            },
        ),
        "selected_items": tuple(
            {
                "run_id": item.run_id,
                "item_id": item.id,
                "title_zh": item.title_zh,
                "section": item.section,
                "confidence_level": item.confidence_level,
                "selection_rationale": item.selection_rationale.summary,
            }
            for item in briefing.items
        ),
        "excluded_candidates": (),
        "delivery_status": tuple(
            {
                "run_id": RUN_ID,
                "recipient_id": recipient_key,
                "status": str(status["status"]),
                "retryable": 1 if status.get("retryable") else 0,
                "failure_reason": status.get("failure_reason"),
            }
            for recipient_key, status in delivery_status.items()
        ),
        "sync_status": (
            {
                "run_id": RUN_ID,
                "target_key": "remote_sync",
                "status": archive.metadata.sync_status["remote_sync"].status,
                "retryable": 1 if archive.metadata.sync_status["remote_sync"].retryable else 0,
                "failure_reason": archive.metadata.sync_status["remote_sync"].failure_reason,
            },
        ),
    }


def _redacted_report(
    registry: SourceRegistry,
    connector_results: tuple[ConnectorResult, ...],
    run: RunPreparation,
    ranking: RankingResult,
    briefing: GeneratedBriefing,
    archive: ArchivePackageResult,
    delivery_status: Mapping[str, Mapping[str, object]],
    console_view: ConsoleView,
) -> dict[str, object]:
    connector_status = _connector_status_map(connector_results)
    low_confidence_items = [item.id for item in briefing.items if item.confidence_notice is not None]
    source_media_items = [
        item.id for item in briefing.items if item.source_media is not None and item.media_attribution
    ]
    no_media_fallback_items = sorted(briefing.media_fallbacks)
    related_history_items = [item.id for item in briefing.items if item.related_history]
    delivery_statuses = {key: status["status"] for key, status in delivery_status.items()}
    source_types = sorted({registry.entry_for(result.source_id).source_type for result in connector_results})
    checklist = {
        "configured_each_first_version_source_type": source_types == ["academic_source", "manual_url", "public_feed"],
        "complete_run_to_feishu_delivery": set(delivery_statuses.values()) == {"sent"},
        "late_connector_did_not_block_deadline": connector_status["src-kubernetes-blog"]["status"] == "timeout"
        and set(delivery_statuses.values()) == {"sent"},
        "pushed_user_and_group": set(delivery_statuses) == {"feishu_group_demo", "feishu_user_demo"},
        "archive_created_for_same_run": archive.metadata.run_id == RUN_ID
        and archive.metadata.sync_status["local_archive"].status == "local_written",
        "deep_dive_detail_exists": all(
            (archive.local_package_path / detail.href).exists() for detail in briefing.deep_dive_details
        ),
        "low_confidence_notice_visible": bool(low_confidence_items),
        "source_media_attribution_visible": bool(source_media_items),
        "no_media_fallback_visible": bool(no_media_fallback_items),
        "related_history_visible": bool(related_history_items),
        "operations_console_status_visible": bool(console_view.runs)
        and {row["status"] for row in console_view.delivery_status} == {"sent"},
    }
    return {
        "run_id": RUN_ID,
        "passed": all(checklist.values()),
        "checklist": checklist,
        "configured_source_types": source_types,
        "connector_status": connector_status,
        "accepted_candidate_ids": [candidate.id for candidate in run.accepted_candidates],
        "selected_candidate_ids": [selected.candidate.id for selected in ranking.selected],
        "briefing_item_ids": [item.id for item in briefing.items],
        "low_confidence_item_ids": low_confidence_items,
        "source_media_item_ids": source_media_items,
        "no_media_fallback_item_ids": no_media_fallback_items,
        "related_history_item_ids": related_history_items,
        "delivery_status": delivery_statuses,
        "archive": {
            "metadata_file": archive.metadata.files["metadata_json"],
            "local_status": archive.metadata.sync_status["local_archive"].status,
            "remote_status": archive.metadata.sync_status["remote_sync"].status,
            "files_written": list(archive.files_written),
        },
        "operations_console": {
            "run_count": len(console_view.runs),
            "delivery_status_count": len(console_view.delivery_status),
            "sync_status_count": len(console_view.sync_status),
            "retry_action_count": len(console_view.retry_actions),
        },
        "model_usage_summary": dict(FIXTURE_MODEL_USAGE),
    }


def _read(repo_root: Path, relative_path: str) -> str:
    return (repo_root / relative_path).read_text(encoding="utf-8")
