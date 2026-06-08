"""Source Access Policy enforcement for Source Connectors."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .contracts import CandidateItem, ContractError, ELIGIBILITY_STATES, SOURCE_TYPES


class SourcePolicyError(ValueError):
    """Raised when Source Access Policy blocks a Candidate Item."""


@dataclass(frozen=True)
class SourcePolicyRow:
    source_id: str
    source_type: str
    eligibility_state: str
    connector_mode: str
    production_auto_ingestion: bool
    requires_owner_review: bool
    requires_per_item_review: bool
    full_text_storage: str
    summary_policy: str
    media_policy: str
    rate_policy: str

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "SourcePolicyRow":
        source_type = _required_value(payload, "source_type", SOURCE_TYPES)
        eligibility_state = _required_value(payload, "eligibility_state", ELIGIBILITY_STATES)
        return cls(
            source_id=_required_str(payload, "source_id"),
            source_type=source_type,
            eligibility_state=eligibility_state,
            connector_mode=_required_str(payload, "connector_mode"),
            production_auto_ingestion=_required_bool(payload, "production_auto_ingestion"),
            requires_owner_review=_required_bool(payload, "requires_owner_review"),
            requires_per_item_review=_required_bool(payload, "requires_per_item_review"),
            full_text_storage=_required_str(payload, "full_text_storage"),
            summary_policy=_required_str(payload, "summary_policy"),
            media_policy=_required_str(payload, "media_policy"),
            rate_policy=_required_str(payload, "rate_policy"),
        )


@dataclass(frozen=True)
class PolicyDecision:
    source_id: str
    allowed: bool
    reason: str
    eligibility_state: str
    connector_mode: str


class SourceAccessPolicy:
    """Central Interface for production auto-ingestion decisions."""

    def __init__(self, rows: Mapping[str, SourcePolicyRow]) -> None:
        self._rows = dict(rows)

    @classmethod
    def from_file(cls, path: Path | str) -> "SourceAccessPolicy":
        with Path(path).open(encoding="utf-8") as handle:
            payload = json.load(handle)
        rows = payload.get("sources")
        if not isinstance(rows, list):
            raise SourcePolicyError("source-access policy must contain a sources list")
        parsed = [SourcePolicyRow.from_mapping(row) for row in rows]
        return cls({row.source_id: row for row in parsed})

    def row_for(self, source_id: str) -> SourcePolicyRow:
        try:
            return self._rows[source_id]
        except KeyError as exc:
            raise SourcePolicyError(f"source_id is not in Source Access Policy: {source_id}") from exc

    def production_enabled_sources(self) -> tuple[SourcePolicyRow, ...]:
        return tuple(row for row in self._rows.values() if row.production_auto_ingestion)

    def rows_by_eligibility(self, eligibility_state: str) -> tuple[SourcePolicyRow, ...]:
        if eligibility_state not in ELIGIBILITY_STATES:
            raise SourcePolicyError(f"unknown eligibility_state: {eligibility_state}")
        return tuple(row for row in self._rows.values() if row.eligibility_state == eligibility_state)

    def evaluate_candidate(self, candidate: CandidateItem) -> PolicyDecision:
        row = self.row_for(candidate.source_id)
        if candidate.source_type != row.source_type:
            return PolicyDecision(
                source_id=candidate.source_id,
                allowed=False,
                reason=f"candidate source_type {candidate.source_type} does not match policy {row.source_type}",
                eligibility_state=row.eligibility_state,
                connector_mode=row.connector_mode,
            )
        if candidate.eligibility_state != row.eligibility_state:
            return PolicyDecision(
                source_id=candidate.source_id,
                allowed=False,
                reason=(
                    f"candidate eligibility_state {candidate.eligibility_state} "
                    f"does not match policy {row.eligibility_state}"
                ),
                eligibility_state=row.eligibility_state,
                connector_mode=row.connector_mode,
            )
        if row.eligibility_state != "eligible":
            return PolicyDecision(
                source_id=candidate.source_id,
                allowed=False,
                reason=f"source remains {row.eligibility_state}; production auto-ingestion is disabled",
                eligibility_state=row.eligibility_state,
                connector_mode=row.connector_mode,
            )
        if not row.production_auto_ingestion:
            return PolicyDecision(
                source_id=candidate.source_id,
                allowed=False,
                reason="production auto-ingestion is disabled by Source Access Policy",
                eligibility_state=row.eligibility_state,
                connector_mode=row.connector_mode,
            )
        if row.requires_owner_review or row.requires_per_item_review:
            return PolicyDecision(
                source_id=candidate.source_id,
                allowed=False,
                reason="source still requires owner or per-item review",
                eligibility_state=row.eligibility_state,
                connector_mode=row.connector_mode,
            )
        return PolicyDecision(
            source_id=candidate.source_id,
            allowed=True,
            reason="source is eligible for production auto-ingestion",
            eligibility_state=row.eligibility_state,
            connector_mode=row.connector_mode,
        )

    def require_candidate_allowed(self, candidate: CandidateItem) -> None:
        decision = self.evaluate_candidate(candidate)
        if not decision.allowed:
            raise SourcePolicyError(decision.reason)


def _required_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{key} must be a non-empty string")
    return value


def _required_bool(payload: Mapping[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ContractError(f"{key} must be a boolean")
    return value


def _required_value(payload: Mapping[str, Any], key: str, allowed: set[str]) -> str:
    value = _required_str(payload, key)
    if value not in allowed:
        raise ContractError(f"{key} must be one of {sorted(allowed)}")
    return value
