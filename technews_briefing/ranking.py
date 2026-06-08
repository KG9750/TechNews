"""Editorial ranking and Selection Rationale primitives."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

from .contracts import CONFIDENCE_LEVELS, CandidateItem, OriginalSourceAnchor


SOURCE_TRUST_WEIGHTS = {
    "official": 6.0,
    "academic": 5.5,
    "mainstream": 4.0,
    "specialist": 3.5,
    "administrator": 2.5,
    "community": 1.0,
}
CONFIDENCE_WEIGHTS = {
    "high": 2.0,
    "medium": -0.5,
    "low": -3.0,
}


class RankingError(ValueError):
    """Raised when ranking inputs are incomplete or inconsistent."""


@dataclass(frozen=True)
class RankingInput:
    candidate: CandidateItem
    section: str
    subcategory: str | None
    source_trust: str
    event_impact: int
    confidence_level: str
    confidence_notice: str | None = None
    original_material_available: bool = True
    related_history: tuple[Mapping[str, object], ...] = ()

    def __post_init__(self) -> None:
        if not self.section.strip():
            raise RankingError("section must be a non-empty string")
        if self.source_trust not in SOURCE_TRUST_WEIGHTS:
            raise RankingError(f"source_trust must be one of {sorted(SOURCE_TRUST_WEIGHTS)}")
        if not 1 <= self.event_impact <= 5:
            raise RankingError("event_impact must be between 1 and 5")
        if self.confidence_level not in CONFIDENCE_LEVELS:
            raise RankingError(f"confidence_level must be one of {sorted(CONFIDENCE_LEVELS)}")
        if self.confidence_level != "high" and not self.confidence_notice:
            raise RankingError("confidence_notice is required for medium and low confidence ranking inputs")


@dataclass(frozen=True)
class SelectionRationaleRecord:
    summary: str
    signals: tuple[str, ...]

    def as_mapping(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "signals": list(self.signals),
        }


@dataclass(frozen=True)
class SelectedCandidate:
    candidate: CandidateItem
    rank: int
    score: float
    section: str
    subcategory: str | None
    confidence_level: str
    confidence_notice: str | None
    selection_rationale: SelectionRationaleRecord
    corroborating_sources: tuple[OriginalSourceAnchor, ...] = ()
    related_history: tuple[Mapping[str, object], ...] = ()

    def archive_record(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate.id,
            "section": self.section,
            "subcategory": self.subcategory,
            "confidence_level": self.confidence_level,
            "selection_rationale": self.selection_rationale.summary,
            "original_source_anchor": _source_anchor_mapping(self.candidate.original_source_anchor),
            "corroborating_sources": [_source_anchor_mapping(source) for source in self.corroborating_sources],
            "related_history": list(self.related_history),
        }


@dataclass(frozen=True)
class ExcludedCandidate:
    candidate: CandidateItem
    score: float
    reason: str
    selection_rationale: SelectionRationaleRecord
    duplicate_of: str | None = None

    def archive_record(self) -> dict[str, object]:
        record: dict[str, object] = {
            "candidate_id": self.candidate.id,
            "reason": self.reason,
            "selection_rationale": self.selection_rationale.summary,
            "original_source_anchor": _source_anchor_mapping(self.candidate.original_source_anchor),
        }
        if self.duplicate_of:
            record["duplicate_of"] = self.duplicate_of
        return record


@dataclass(frozen=True)
class RankingResult:
    selected: tuple[SelectedCandidate, ...]
    excluded: tuple[ExcludedCandidate, ...]

    def archive_excluded_candidates(self) -> tuple[dict[str, object], ...]:
        return tuple(candidate.archive_record() for candidate in self.excluded)


def rank_candidates(
    candidates: tuple[RankingInput, ...],
    *,
    subscribed_sections: set[str],
    run_started_at: str,
    max_selected: int = 8,
) -> RankingResult:
    if max_selected < 1:
        raise RankingError("max_selected must be at least 1")
    if not subscribed_sections:
        raise RankingError("subscribed_sections must not be empty")

    run_time = _parse_datetime(run_started_at)
    grouped = _group_by_event(candidates)
    representatives: list[tuple[RankingInput, float, tuple[RankingInput, ...]]] = []
    duplicate_exclusions: list[ExcludedCandidate] = []

    for group in grouped.values():
        scored = sorted(
            ((item, _score(item, subscribed_sections, run_time, corroboration_count=len(group) - 1)) for item in group),
            key=lambda item_score: (item_score[1], item_score[0].candidate.published_at or ""),
            reverse=True,
        )
        representative, score = scored[0]
        duplicates = tuple(item for item, _ in scored[1:])
        representatives.append((representative, score, duplicates))
        for duplicate in duplicates:
            duplicate_exclusions.append(
                ExcludedCandidate(
                    candidate=duplicate.candidate,
                    score=_score(duplicate, subscribed_sections, run_time, corroboration_count=len(group) - 1),
                    reason="duplicate_coverage",
                    duplicate_of=representative.candidate.id,
                    selection_rationale=SelectionRationaleRecord(
                        summary="Duplicate or corroborating coverage; merged into the higher-ranked source item.",
                        signals=(
                            f"duplicate_of:{representative.candidate.id}",
                            f"event_key:{_event_key(duplicate)}",
                            "archive:preserve_as_corroborating_source",
                        ),
                    ),
                )
            )

    representatives.sort(key=lambda item: item[1], reverse=True)
    selected: list[SelectedCandidate] = []
    excluded: list[ExcludedCandidate] = list(duplicate_exclusions)

    for index, (item, score, duplicates) in enumerate(representatives):
        if index < max_selected:
            selected.append(
                SelectedCandidate(
                    candidate=item.candidate,
                    rank=index + 1,
                    score=score,
                    section=item.section,
                    subcategory=item.subcategory,
                    confidence_level=item.confidence_level,
                    confidence_notice=item.confidence_notice,
                    selection_rationale=_selected_rationale(
                        item,
                        score,
                        rank=index + 1,
                        subscribed=item.section in subscribed_sections,
                        corroboration_count=len(duplicates),
                        run_time=run_time,
                    ),
                    corroborating_sources=tuple(duplicate.candidate.original_source_anchor for duplicate in duplicates),
                    related_history=item.related_history,
                )
            )
        else:
            excluded.append(
                ExcludedCandidate(
                    candidate=item.candidate,
                    score=score,
                    reason="below_selection_limit",
                    selection_rationale=_excluded_rationale(item, score, max_selected),
                )
            )

    excluded.sort(key=lambda item: (item.reason != "duplicate_coverage", -item.score))
    return RankingResult(selected=tuple(selected), excluded=tuple(excluded))


def _score(
    item: RankingInput,
    subscribed_sections: set[str],
    run_time: datetime,
    *,
    corroboration_count: int,
) -> float:
    score = item.event_impact * 10.0
    score += SOURCE_TRUST_WEIGHTS[item.source_trust]
    score += CONFIDENCE_WEIGHTS[item.confidence_level]
    score += 4.0 if item.section in subscribed_sections else -4.0
    score += _timeliness_score(item.candidate.published_at, run_time)
    if item.original_material_available:
        score += 2.0
    if item.candidate.source_media is not None:
        score += 0.5
    if item.related_history:
        score += 1.0
    if corroboration_count:
        score += min(corroboration_count, 3) * 1.5
    return score


def _selected_rationale(
    item: RankingInput,
    score: float,
    *,
    rank: int,
    subscribed: bool,
    corroboration_count: int,
    run_time: datetime,
) -> SelectionRationaleRecord:
    signals = [
        f"rank:{rank}",
        f"score:{score:.1f}",
        f"section:{item.section}",
        f"subcategory:{item.subcategory or 'none'}",
        f"source_trust:{item.source_trust}",
        f"event_impact:{item.event_impact}",
        f"confidence:{item.confidence_level}",
        f"timeliness:{_timeliness_label(item.candidate.published_at, run_time)}",
        "subscribed_section" if subscribed else "outside_subscribed_sections",
    ]
    if item.original_material_available:
        signals.append("original_material_available")
    if item.candidate.source_media is not None:
        signals.append("source_media_available")
    if corroboration_count:
        signals.append(f"corroborating_sources:{corroboration_count}")
    if item.related_history:
        signals.append(f"related_history:{len(item.related_history)}")

    summary = (
        f"Selected for {item.section} because impact={item.event_impact}, "
        f"trust={item.source_trust}, confidence={item.confidence_level}, and score={score:.1f}."
    )
    return SelectionRationaleRecord(summary=summary, signals=tuple(signals))


def _excluded_rationale(item: RankingInput, score: float, max_selected: int) -> SelectionRationaleRecord:
    return SelectionRationaleRecord(
        summary=f"Excluded because score={score:.1f} fell below the top {max_selected} selected candidates.",
        signals=(
            f"score:{score:.1f}",
            f"section:{item.section}",
            f"event_impact:{item.event_impact}",
            f"confidence:{item.confidence_level}",
            "archive:preserve_exclusion_reason",
        ),
    )


def _group_by_event(candidates: tuple[RankingInput, ...]) -> dict[str, list[RankingInput]]:
    groups: dict[str, list[RankingInput]] = {}
    for item in candidates:
        groups.setdefault(_event_key(item), []).append(item)
    return groups


def _event_key(item: RankingInput) -> str:
    if item.candidate.event_key:
        return item.candidate.event_key
    if item.candidate.dedupe_key:
        return f"dedupe:{item.candidate.dedupe_key}"
    return "title:" + re.sub(r"[^a-z0-9]+", "-", item.candidate.original_title.lower()).strip("-")


def _timeliness_score(published_at: str | None, run_time: datetime) -> float:
    label = _timeliness_label(published_at, run_time)
    if label == "recent":
        return 2.0
    if label == "current_week":
        return 1.0
    if label == "missing_published_at":
        return -1.0
    return 0.0


def _timeliness_label(published_at: str | None, run_time: datetime) -> str:
    if not published_at:
        return "missing_published_at"
    age_seconds = (run_time - _parse_datetime(published_at)).total_seconds()
    if age_seconds < 0:
        return "future_timestamp"
    age_days = age_seconds / 86400
    if age_days <= 2:
        return "recent"
    if age_days <= 7:
        return "current_week"
    return "older"


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _source_anchor_mapping(anchor: OriginalSourceAnchor) -> dict[str, str]:
    return {
        "source_name": anchor.source_name,
        "original_title": anchor.original_title,
        "source_url": anchor.source_url,
    }
