"""Python data models for the minimal briefing contracts.

The contracts in docs/schemas/minimal-contracts.md are the product Interface.
These models keep fixture checks and future product code crossing the same seam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping


class ContractError(ValueError):
    """Raised when a payload violates a briefing contract."""


SOURCE_TYPES = {"public_feed", "academic_source", "manual_url", "deferred_connector"}
ELIGIBILITY_STATES = {"eligible", "needs_review", "deferred", "blocked"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
CONNECTOR_STATUSES = {"completed", "partial", "timeout", "failed", "skipped"}
DELIVERY_STATUSES = {"pending", "sent", "failed", "skipped"}
SYNC_STATUSES = {"not_started", "local_written", "synced", "failed"}
MODEL_TASK_STATUSES = {"pending", "completed", "failed", "skipped"}
FAILED_STATUS = "failed"
SOURCE_MEDIA_KINDS = {
    "feed_image",
    "open_graph_image",
    "official_image",
    "paper_asset",
    "favicon",
}
STATUS_COMMON_KEYS = {"status", "failure_reason", "retryable"}
DISALLOWED_FULL_BODY_KEYS = {
    "article_body",
    "body",
    "body_text",
    "complete_article_text",
    "content",
    "full_text",
    "html",
    "text",
    "transcript",
}


def _require_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ContractError(f"{key} must be an object")
    return value


def _optional_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ContractError(f"{key} must be an object when present")
    return value


def _require_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{key} must be a non-empty string")
    return value


def _optional_str(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{key} must be a non-empty string when present")
    return value


def _require_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ContractError(f"{key} must be a list")
    return value


def _optional_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ContractError(f"{key} must be a list when present")
    return value


def _require_value(value: str, allowed: set[str], label: str) -> str:
    if value not in allowed:
        raise ContractError(f"{label} must be one of {sorted(allowed)}")
    return value


def _require_utc_timestamp(payload: Mapping[str, Any], key: str) -> str:
    value = _require_str(payload, key)
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{key} must be an ISO 8601 timestamp") from exc
    return value


def _optional_utc_timestamp(payload: Mapping[str, Any], key: str) -> str | None:
    value = _optional_str(payload, key)
    if value is None:
        return None
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{key} must be an ISO 8601 timestamp when present") from exc
    return value


def _nested_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        keys = {str(key) for key in value}
        for nested in value.values():
            keys.update(_nested_keys(nested))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(_nested_keys(item))
        return keys
    return set()


def _reject_full_body_metadata(raw_metadata: Mapping[str, Any]) -> None:
    disallowed = sorted(_nested_keys(raw_metadata) & DISALLOWED_FULL_BODY_KEYS)
    if disallowed:
        raise ContractError(f"raw_metadata contains full-body keys: {', '.join(disallowed)}")


@dataclass(frozen=True)
class OriginalSourceAnchor:
    source_name: str
    original_title: str
    source_url: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "OriginalSourceAnchor":
        return cls(
            source_name=_require_str(payload, "source_name"),
            original_title=_require_str(payload, "original_title"),
            source_url=_require_str(payload, "source_url"),
        )


@dataclass(frozen=True)
class SourceMedia:
    url: str
    kind: str
    attribution: str
    eligibility_note: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "SourceMedia":
        kind = _require_value(_require_str(payload, "kind"), SOURCE_MEDIA_KINDS, "source_media.kind")
        return cls(
            url=_require_str(payload, "url"),
            kind=kind,
            attribution=_require_str(payload, "attribution"),
            eligibility_note=_require_str(payload, "eligibility_note"),
        )


@dataclass(frozen=True)
class SelectionRationale:
    summary: str
    signals: tuple[str, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "SelectionRationale":
        signals = _require_list(payload, "signals")
        if not all(isinstance(signal, str) and signal.strip() for signal in signals):
            raise ContractError("selection_rationale.signals must contain strings")
        return cls(
            summary=_require_str(payload, "summary"),
            signals=tuple(signals),
        )


@dataclass(frozen=True)
class ConfidenceNotice:
    reason: str
    display_text_zh: str
    supporting_sources: tuple[OriginalSourceAnchor, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ConfidenceNotice":
        sources = _require_list(payload, "supporting_sources")
        return cls(
            reason=_require_str(payload, "reason"),
            display_text_zh=_require_str(payload, "display_text_zh"),
            supporting_sources=tuple(OriginalSourceAnchor.from_mapping(source) for source in sources),
        )


@dataclass(frozen=True)
class ModelUsage:
    provider: str
    model: str
    task_type: str
    request_count: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    failure_reason: str | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ModelUsage":
        request_count = payload.get("request_count")
        if not isinstance(request_count, int) or request_count < 0:
            raise ContractError("model_usage.request_count must be a non-negative integer")
        return cls(
            provider=_require_str(payload, "provider"),
            model=_require_str(payload, "model"),
            task_type=_require_str(payload, "task_type"),
            request_count=request_count,
            input_tokens=_optional_int(payload, "input_tokens"),
            output_tokens=_optional_int(payload, "output_tokens"),
            latency_ms=_optional_int(payload, "latency_ms"),
            failure_reason=_optional_str(payload, "failure_reason"),
        )


def _optional_int(payload: Mapping[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or value < 0:
        raise ContractError(f"{key} must be a non-negative integer when present")
    return value


def _optional_bool(payload: Mapping[str, Any], key: str) -> bool | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ContractError(f"{key} must be a boolean when present")
    return value


@dataclass(frozen=True)
class StatusRecord:
    status: str
    failure_reason: str | None = None
    retryable: bool | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any], allowed: set[str], label: str) -> "StatusRecord":
        status = _require_value(_require_str(payload, "status"), allowed, f"{label}.status")
        failure_reason = _optional_str(payload, "failure_reason")
        retryable = _optional_bool(payload, "retryable")
        if status == FAILED_STATUS and failure_reason is None:
            raise ContractError(f"{label}.failure_reason is required when status is failed")
        metadata = {str(key): value for key, value in payload.items() if key not in STATUS_COMMON_KEYS}
        return cls(status=status, failure_reason=failure_reason, retryable=retryable, metadata=metadata)


@dataclass(frozen=True)
class ModelUsageSummary:
    provider: str
    model: str
    task_count: int
    request_count: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    failure_count: int = 0
    notes: str | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ModelUsageSummary":
        failure_count = payload.get("failure_count", 0)
        if not isinstance(failure_count, int) or failure_count < 0:
            raise ContractError("model_usage_summary.failure_count must be a non-negative integer")
        return cls(
            provider=_require_str(payload, "provider"),
            model=_require_str(payload, "model"),
            task_count=_require_non_negative_int(payload, "task_count"),
            request_count=_require_non_negative_int(payload, "request_count"),
            input_tokens=_optional_int(payload, "input_tokens"),
            output_tokens=_optional_int(payload, "output_tokens"),
            latency_ms=_optional_int(payload, "latency_ms"),
            failure_count=failure_count,
            notes=_optional_str(payload, "notes"),
        )


def _require_non_negative_int(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value < 0:
        raise ContractError(f"{key} must be a non-negative integer")
    return value


def _status_mapping(payload: Mapping[str, Any], key: str, allowed: set[str], label: str) -> Mapping[str, StatusRecord]:
    values = _require_mapping(payload, key)
    records: dict[str, StatusRecord] = {}
    for record_key, record in values.items():
        if not isinstance(record_key, str) or not record_key.strip():
            raise ContractError(f"{label} keys must be non-empty strings")
        if not isinstance(record, Mapping):
            raise ContractError(f"{label}.{record_key} must be an object")
        records[record_key] = StatusRecord.from_mapping(record, allowed, f"{label}.{record_key}")
    return records


@dataclass(frozen=True)
class CandidateItem:
    id: str
    run_id: str
    source_id: str
    source_type: str
    source_name: str
    original_title: str
    source_url: str
    original_source_anchor: OriginalSourceAnchor
    dedupe_key: str
    discovered_at: str
    eligibility_state: str
    event_key: str | None = None
    published_at: str | None = None
    language: str | None = None
    section_hints: tuple[str, ...] = ()
    source_media: SourceMedia | None = None
    eligibility_notes: str | None = None
    raw_metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "CandidateItem":
        source_type = _require_value(_require_str(payload, "source_type"), SOURCE_TYPES, "source_type")
        eligibility_state = _require_value(
            _require_str(payload, "eligibility_state"),
            ELIGIBILITY_STATES,
            "eligibility_state",
        )
        raw_metadata = _optional_mapping(payload, "raw_metadata") or {}
        _reject_full_body_metadata(raw_metadata)
        source_media = _optional_mapping(payload, "source_media")
        section_hints = _optional_list(payload, "section_hints")
        if not all(isinstance(section, str) and section.strip() for section in section_hints):
            raise ContractError("section_hints must contain strings")
        return cls(
            id=_require_str(payload, "id"),
            run_id=_require_str(payload, "run_id"),
            source_id=_require_str(payload, "source_id"),
            source_type=source_type,
            source_name=_require_str(payload, "source_name"),
            original_title=_require_str(payload, "original_title"),
            source_url=_require_str(payload, "source_url"),
            original_source_anchor=OriginalSourceAnchor.from_mapping(
                _require_mapping(payload, "original_source_anchor")
            ),
            dedupe_key=_require_str(payload, "dedupe_key"),
            discovered_at=_require_utc_timestamp(payload, "discovered_at"),
            eligibility_state=eligibility_state,
            event_key=_optional_str(payload, "event_key"),
            published_at=_optional_utc_timestamp(payload, "published_at"),
            language=_optional_str(payload, "language"),
            section_hints=tuple(section_hints),
            source_media=SourceMedia.from_mapping(source_media) if source_media else None,
            eligibility_notes=_optional_str(payload, "eligibility_notes"),
            raw_metadata=raw_metadata,
        )


@dataclass(frozen=True)
class BriefingItem:
    id: str
    run_id: str
    candidate_id: str
    section: str
    title_zh: str
    bullets_zh: tuple[str, ...]
    original_source_anchor: OriginalSourceAnchor
    selection_rationale: SelectionRationale
    confidence_level: str
    subcategory: str | None = None
    source_media: SourceMedia | None = None
    confidence_notice: ConfidenceNotice | None = None
    media_attribution: Mapping[str, Any] | None = None
    related_history: tuple[Mapping[str, Any], ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "BriefingItem":
        bullets = _require_list(payload, "bullets_zh")
        if not 3 <= len(bullets) <= 4 or not all(isinstance(bullet, str) and bullet.strip() for bullet in bullets):
            raise ContractError("bullets_zh must contain three or four strings")
        confidence_level = _require_value(
            _require_str(payload, "confidence_level"),
            CONFIDENCE_LEVELS,
            "confidence_level",
        )
        notice_payload = _optional_mapping(payload, "confidence_notice")
        confidence_notice = ConfidenceNotice.from_mapping(notice_payload) if notice_payload else None
        if confidence_level != "high" and confidence_notice is None:
            raise ContractError("confidence_notice is required when confidence_level is not high")
        source_media = _optional_mapping(payload, "source_media")
        media_attribution = _optional_mapping(payload, "media_attribution")
        if source_media and media_attribution is None:
            raise ContractError("media_attribution is required when source_media is displayed")
        related_history = _optional_list(payload, "related_history")
        if not all(isinstance(item, Mapping) for item in related_history):
            raise ContractError("related_history must contain objects")
        return cls(
            id=_require_str(payload, "id"),
            run_id=_require_str(payload, "run_id"),
            candidate_id=_require_str(payload, "candidate_id"),
            section=_require_str(payload, "section"),
            subcategory=_optional_str(payload, "subcategory"),
            title_zh=_require_str(payload, "title_zh"),
            bullets_zh=tuple(bullets),
            original_source_anchor=OriginalSourceAnchor.from_mapping(
                _require_mapping(payload, "original_source_anchor")
            ),
            selection_rationale=SelectionRationale.from_mapping(_require_mapping(payload, "selection_rationale")),
            confidence_level=confidence_level,
            source_media=SourceMedia.from_mapping(source_media) if source_media else None,
            confidence_notice=confidence_notice,
            media_attribution=media_attribution,
            related_history=tuple(related_history),
        )


@dataclass(frozen=True)
class ArchiveMetadata:
    run_id: str
    domain_template: str
    generated_at: str
    files: Mapping[str, Any]
    selected_items: tuple[Mapping[str, Any], ...]
    excluded_candidates: tuple[Mapping[str, Any], ...]
    connector_status: Mapping[str, StatusRecord]
    delivery_status: Mapping[str, StatusRecord]
    media_inventory: tuple[Mapping[str, Any], ...]
    sync_status: Mapping[str, StatusRecord]
    model_usage_summary: ModelUsageSummary
    warnings: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ArchiveMetadata":
        warnings = _optional_list(payload, "warnings")
        if not all(isinstance(warning, str) and warning.strip() for warning in warnings):
            raise ContractError("warnings must contain strings")
        return cls(
            run_id=_require_str(payload, "run_id"),
            domain_template=_require_str(payload, "domain_template"),
            generated_at=_require_utc_timestamp(payload, "generated_at"),
            files=_require_mapping(payload, "files"),
            selected_items=tuple(_require_list(payload, "selected_items")),
            excluded_candidates=tuple(_require_list(payload, "excluded_candidates")),
            connector_status=_status_mapping(payload, "connector_status", CONNECTOR_STATUSES, "connector_status"),
            delivery_status=_status_mapping(payload, "delivery_status", DELIVERY_STATUSES, "delivery_status"),
            media_inventory=tuple(_require_list(payload, "media_inventory")),
            sync_status=_status_mapping(payload, "sync_status", SYNC_STATUSES, "sync_status"),
            model_usage_summary=ModelUsageSummary.from_mapping(_require_mapping(payload, "model_usage_summary")),
            warnings=tuple(warnings),
        )


@dataclass(frozen=True)
class BriefingRun:
    run_id: str
    domain_template: str
    scheduled_for: str
    delivery_deadline: str
    started_at: str
    connector_status: Mapping[str, StatusRecord]
    model_task_status: Mapping[str, StatusRecord]
    archive_status: Mapping[str, StatusRecord]
    feishu_delivery_status: Mapping[str, StatusRecord]
    completed_at: str | None = None
    run_warnings: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "BriefingRun":
        warnings = _optional_list(payload, "run_warnings")
        if not all(isinstance(warning, str) and warning.strip() for warning in warnings):
            raise ContractError("run_warnings must contain strings")
        return cls(
            run_id=_require_str(payload, "run_id"),
            domain_template=_require_str(payload, "domain_template"),
            scheduled_for=_require_utc_timestamp(payload, "scheduled_for"),
            delivery_deadline=_require_utc_timestamp(payload, "delivery_deadline"),
            started_at=_require_utc_timestamp(payload, "started_at"),
            completed_at=_optional_utc_timestamp(payload, "completed_at"),
            connector_status=_status_mapping(payload, "connector_status", CONNECTOR_STATUSES, "connector_status"),
            model_task_status=_status_mapping(payload, "model_task_status", MODEL_TASK_STATUSES, "model_task_status"),
            archive_status=_status_mapping(payload, "archive_status", SYNC_STATUSES, "archive_status"),
            feishu_delivery_status=_status_mapping(
                payload,
                "feishu_delivery_status",
                DELIVERY_STATUSES,
                "feishu_delivery_status",
            ),
            run_warnings=tuple(warnings),
        )
