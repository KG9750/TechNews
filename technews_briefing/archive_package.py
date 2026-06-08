"""Local-first Archive Package writer."""

from __future__ import annotations

import html
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping

from .briefing_generation import GeneratedBriefing
from .contracts import ArchiveMetadata, BriefingItem, OriginalSourceAnchor
from .ranking import ExcludedCandidate


class ArchivePackageError(ValueError):
    """Raised when an Archive Package cannot be built safely."""


@dataclass(frozen=True)
class ArchivePackageResult:
    local_package_path: Path
    remote_package_path: Path | None
    metadata: ArchiveMetadata
    files_written: tuple[str, ...]


def archive_package_path(local_root: Path, *, generated_at: str, domain_template: str) -> Path:
    return local_root / _date_from_timestamp(generated_at) / _safe_segment(domain_template, "domain_template")


def write_archive_package(
    briefing: GeneratedBriefing,
    *,
    local_root: Path,
    generated_at: str,
    domain_template: str = "technology",
    excluded_candidates: tuple[ExcludedCandidate | Mapping[str, object], ...] = (),
    connector_status: Mapping[str, Mapping[str, object]] | None = None,
    delivery_status: Mapping[str, Mapping[str, object]] | None = None,
    model_usage_summary: Mapping[str, object] | None = None,
    sync_target: Path | None = None,
    sync_attempted_at: str | None = None,
    warnings: tuple[str, ...] = (),
) -> ArchivePackageResult:
    package_path = archive_package_path(local_root, generated_at=generated_at, domain_template=domain_template)
    relative_package_path = f"{_date_from_timestamp(generated_at)}/{_safe_segment(domain_template, 'domain_template')}"

    if package_path.exists():
        shutil.rmtree(package_path)
    (package_path / "media").mkdir(parents=True)
    (package_path / "deep-dive").mkdir(parents=True)

    _write_text(package_path / "briefing.md", _render_markdown(briefing))
    _write_text(package_path / "briefing.html", _render_html(briefing))
    _write_text(package_path / "media/README.md", _render_media_readme(briefing))
    for detail in briefing.deep_dive_details:
        _write_text(package_path / detail.href, _render_deep_dive_html(detail.as_mapping()))

    base_metadata = _metadata_payload(
        briefing,
        generated_at=generated_at,
        domain_template=domain_template,
        excluded_candidates=excluded_candidates,
        connector_status=connector_status or {},
        delivery_status=delivery_status or {},
        model_usage_summary=model_usage_summary or _default_model_usage_summary(),
        relative_package_path=relative_package_path,
        sync_status={
            "local_archive": {
                "status": "local_written",
                "root": "ARCHIVE_LOCAL_ROOT",
                "package_path": relative_package_path,
            },
            "remote_sync": {
                "status": "not_started",
                "target": _sync_target_label(sync_target, relative_package_path),
                "retryable": True,
            },
        },
        warnings=warnings,
    )
    _write_json(package_path / "metadata.json", base_metadata)

    remote_package_path, remote_status, sync_warning = _sync_package(
        package_path,
        sync_target=sync_target,
        relative_package_path=relative_package_path,
        attempted_at=sync_attempted_at or generated_at,
    )
    final_warnings = tuple((*warnings, sync_warning)) if sync_warning else warnings
    final_metadata = dict(base_metadata)
    final_metadata["sync_status"] = {
        "local_archive": base_metadata["sync_status"]["local_archive"],
        "remote_sync": remote_status,
    }
    final_metadata["warnings"] = list(final_warnings)
    metadata = ArchiveMetadata.from_mapping(final_metadata)
    _write_json(package_path / "metadata.json", final_metadata)

    if remote_package_path is not None and remote_status["status"] == "synced":
        _write_json(remote_package_path / "metadata.json", final_metadata)

    return ArchivePackageResult(
        local_package_path=package_path,
        remote_package_path=remote_package_path,
        metadata=metadata,
        files_written=tuple(_tree_lines(package_path)),
    )


def _metadata_payload(
    briefing: GeneratedBriefing,
    *,
    generated_at: str,
    domain_template: str,
    excluded_candidates: tuple[ExcludedCandidate | Mapping[str, object], ...],
    connector_status: Mapping[str, Mapping[str, object]],
    delivery_status: Mapping[str, Mapping[str, object]],
    model_usage_summary: Mapping[str, object],
    relative_package_path: str,
    sync_status: Mapping[str, Mapping[str, object]],
    warnings: tuple[str, ...],
) -> dict[str, object]:
    return {
        "run_id": briefing.run_id,
        "domain_template": domain_template,
        "generated_at": generated_at,
        "files": {
            "briefing_html": "briefing.html",
            "briefing_md": "briefing.md",
            "metadata_json": "metadata.json",
            "media_dir": "media/",
            "deep_dive_dir": "deep-dive/",
        },
        "selected_items": [_selected_item_record(briefing, item) for item in briefing.items],
        "excluded_candidates": [_excluded_candidate_record(candidate) for candidate in excluded_candidates],
        "connector_status": dict(connector_status),
        "delivery_status": dict(delivery_status),
        "media_inventory": _media_inventory(briefing),
        "sync_status": dict(sync_status),
        "model_usage_summary": dict(model_usage_summary),
        "warnings": list(warnings),
        "package_path": relative_package_path,
    }


def _selected_item_record(briefing: GeneratedBriefing, item: BriefingItem) -> dict[str, object]:
    detail = briefing.deep_dive_for_item(item.id)
    record: dict[str, object] = {
        "briefing_item_id": item.id,
        "candidate_id": item.candidate_id,
        "section": item.section,
        "subcategory": item.subcategory,
        "title_zh": item.title_zh,
        "confidence_level": item.confidence_level,
        "selection_rationale": item.selection_rationale.summary,
        "original_source_anchor": _source_anchor_mapping(item.original_source_anchor),
        "deep_dive_href": detail.href,
        "media_attribution": item.media_attribution,
    }
    if item.confidence_notice is not None:
        record["confidence_notice"] = {
            "reason": item.confidence_notice.reason,
            "display_text_zh": item.confidence_notice.display_text_zh,
            "supporting_sources": [
                _source_anchor_mapping(source) for source in item.confidence_notice.supporting_sources
            ],
        }
    if detail.media_fallback is not None:
        record["media_fallback"] = detail.media_fallback.as_mapping()
    return record


def _excluded_candidate_record(candidate: ExcludedCandidate | Mapping[str, object]) -> Mapping[str, object]:
    if isinstance(candidate, ExcludedCandidate):
        return candidate.archive_record()
    return dict(candidate)


def _media_inventory(briefing: GeneratedBriefing) -> list[dict[str, object]]:
    inventory = []
    for item in briefing.items:
        if item.source_media is None:
            continue
        inventory.append(
            {
                "briefing_item_id": item.id,
                "candidate_id": item.candidate_id,
                "source_media_url": item.source_media.url,
                "stored_file": None,
                "attribution": item.source_media.attribution,
                "status": "metadata_only_not_downloaded",
                "eligibility_note": item.source_media.eligibility_note,
            }
        )
    return inventory


def _sync_package(
    package_path: Path,
    *,
    sync_target: Path | None,
    relative_package_path: str,
    attempted_at: str,
) -> tuple[Path | None, dict[str, object], str | None]:
    if sync_target is None:
        return (
            None,
            {
                "status": "failed",
                "target": "ARCHIVE_SYNC_TARGET_UNSET",
                "attempted_at": attempted_at,
                "failure_reason": "ARCHIVE_SYNC_TARGET is not configured.",
                "retryable": True,
                "retry_state": "pending_retry",
            },
            "Remote sync failed because no ARCHIVE_SYNC_TARGET is configured; local archive remains readable.",
        )

    remote_package_path = sync_target / relative_package_path
    try:
        if remote_package_path.exists():
            shutil.rmtree(remote_package_path)
        remote_package_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(package_path, remote_package_path)
    except OSError as error:
        return (
            remote_package_path,
            {
                "status": "failed",
                "target": f"ARCHIVE_SYNC_TARGET/{relative_package_path}",
                "attempted_at": attempted_at,
                "failure_reason": str(error),
                "retryable": True,
                "retry_state": "pending_retry",
            },
            "Remote sync failed; local archive remains readable and retryable.",
        )
    return (
        remote_package_path,
        {
            "status": "synced",
            "target": f"ARCHIVE_SYNC_TARGET/{relative_package_path}",
            "attempted_at": attempted_at,
            "retryable": False,
            "retry_state": "not_needed",
        },
        None,
    )


def _render_markdown(briefing: GeneratedBriefing) -> str:
    lines = [f"# TechNews Briefing - {briefing.run_id}", ""]
    for group in briefing.groups:
        lines.extend([f"## {group.section}", ""])
        if group.subcategory:
            lines.extend([f"### {group.subcategory}", ""])
        for item in group.items:
            detail = briefing.deep_dive_for_item(item.id)
            lines.extend([f"#### {item.title_zh}", ""])
            lines.extend(f"- {bullet}" for bullet in item.bullets_zh)
            if item.confidence_notice is not None:
                lines.append(f"- {item.confidence_notice.display_text_zh}")
            lines.append(
                f"- 来源：[{item.original_source_anchor.source_name}]({item.original_source_anchor.source_url})"
            )
            lines.append(f"- Deep-Dive：[{detail.href}]({detail.href})")
            if item.media_attribution is not None:
                lines.append(f"- {item.media_attribution['display_text_zh']}")
            elif detail.media_fallback is not None:
                lines.append(f"- {detail.media_fallback.display_text_zh}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_html(briefing: GeneratedBriefing) -> str:
    body = [f"<h1>TechNews Briefing - {html.escape(briefing.run_id)}</h1>"]
    for group in briefing.groups:
        body.append(f"<h2>{html.escape(group.section)}</h2>")
        if group.subcategory:
            body.append(f"<h3>{html.escape(group.subcategory)}</h3>")
        for item in group.items:
            detail = briefing.deep_dive_for_item(item.id)
            body.append(f'<article id="{html.escape(item.id)}">')
            body.append(f"<h4>{html.escape(item.title_zh)}</h4>")
            body.append("<ul>")
            for bullet in item.bullets_zh:
                body.append(f"<li>{html.escape(bullet)}</li>")
            if item.confidence_notice is not None:
                body.append(f"<li>{html.escape(item.confidence_notice.display_text_zh)}</li>")
            body.append(
                "<li>来源："
                f'<a href="{html.escape(item.original_source_anchor.source_url)}">'
                f"{html.escape(item.original_source_anchor.source_name)}</a></li>"
            )
            body.append(f'<li>Deep-Dive：<a href="{html.escape(detail.href)}">{html.escape(detail.href)}</a></li>')
            if item.media_attribution is not None:
                body.append(f"<li>{html.escape(str(item.media_attribution['display_text_zh']))}</li>")
            elif detail.media_fallback is not None:
                body.append(f"<li>{html.escape(detail.media_fallback.display_text_zh)}</li>")
            body.append("</ul></article>")
    return _html_page("TechNews Briefing", "\n".join(body))


def _render_deep_dive_html(detail: Mapping[str, object]) -> str:
    source_rows = []
    for source in detail["source_list"]:
        if not isinstance(source, Mapping):
            continue
        source_rows.append(
            "<li>"
            f'<a href="{html.escape(str(source["source_url"]))}">'
            f"{html.escape(str(source['source_name']))}</a>"
            f" - {html.escape(str(source['original_title']))}</li>"
        )
    content = [
        f"<h1>{html.escape(str(detail['title_zh']))}</h1>",
        f"<p>{html.escape(str(detail['summary_zh']))}</p>",
        "<h2>Sources</h2>",
        "<ul>",
        *source_rows,
        "</ul>",
        "<h2>Selection Rationale</h2>",
        f"<p>{html.escape(str(detail['selection_rationale'].get('summary', '')))}</p>",
    ]
    confidence_notice = detail.get("confidence_notice")
    if isinstance(confidence_notice, Mapping):
        content.extend(
            [
                "<h2>Confidence Notice</h2>",
                f"<p>{html.escape(str(confidence_notice['display_text_zh']))}</p>",
            ]
        )
    media_fallback = detail.get("media_fallback")
    if isinstance(media_fallback, Mapping):
        content.extend(["<h2>Media</h2>", f"<p>{html.escape(str(media_fallback['display_text_zh']))}</p>"])
    return _html_page(str(detail["title_zh"]), "\n".join(content))


def _render_media_readme(briefing: GeneratedBriefing) -> str:
    if not any(item.source_media is not None for item in briefing.items):
        return "No source media files are downloaded for this Archive Package.\n"
    return (
        "Source media is recorded as metadata only unless a later policy decision allows downloading.\n"
        "See metadata.json media_inventory for attribution and eligibility notes.\n"
    )


def _html_page(title: str, body: str) -> str:
    return (
        "<!doctype html>\n"
        '<html lang="zh-CN">\n'
        '<head><meta charset="utf-8"><title>'
        f"{html.escape(title)}</title></head>\n"
        f"<body>{body}</body>\n"
        "</html>\n"
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _tree_lines(path: Path) -> list[str]:
    lines = []
    for child in sorted(path.rglob("*")):
        relative = child.relative_to(path)
        suffix = "/" if child.is_dir() else ""
        lines.append(f"{relative}{suffix}")
    return lines


def _source_anchor_mapping(source: OriginalSourceAnchor) -> dict[str, str]:
    return {
        "source_name": source.source_name,
        "original_title": source.original_title,
        "source_url": source.source_url,
    }


def _default_model_usage_summary() -> dict[str, object]:
    return {
        "provider": "product",
        "model": "not_called",
        "task_count": 0,
        "request_count": 0,
        "failure_count": 0,
        "notes": "Archive package writer did not call a model provider.",
    }


def _sync_target_label(sync_target: Path | None, relative_package_path: str) -> str:
    if sync_target is None:
        return "ARCHIVE_SYNC_TARGET_UNSET"
    return f"ARCHIVE_SYNC_TARGET/{relative_package_path}"


def _date_from_timestamp(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError as error:
        raise ArchivePackageError("generated_at must be an ISO 8601 timestamp") from error


def _safe_segment(value: str, label: str) -> str:
    if not value or any(character in value for character in "/\\"):
        raise ArchivePackageError(f"{label} must be a single path segment")
    return value
