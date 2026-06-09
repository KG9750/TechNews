"""Briefing item and Deep-Dive Detail generation primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .contracts import BriefingItem, OriginalSourceAnchor, SourceMedia
from .ranking import SelectedCandidate


class BriefingGenerationError(ValueError):
    """Raised when selected candidates cannot produce briefing output."""


@dataclass(frozen=True)
class MediaFallback:
    briefing_item_id: str
    reason: str
    display_text_zh: str

    def as_mapping(self) -> dict[str, str]:
        return {
            "briefing_item_id": self.briefing_item_id,
            "reason": self.reason,
            "display_text_zh": self.display_text_zh,
        }


@dataclass(frozen=True)
class DeepDiveDetail:
    id: str
    briefing_item_id: str
    href: str
    title_zh: str
    summary_zh: str
    source_list: tuple[OriginalSourceAnchor, ...]
    selection_rationale: Mapping[str, object]
    confidence_notice: Mapping[str, object] | None
    related_history: tuple[Mapping[str, object], ...]
    candidate_metadata: Mapping[str, object]
    media_attribution: Mapping[str, object] | None = None
    media_fallback: MediaFallback | None = None

    def as_mapping(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "briefing_item_id": self.briefing_item_id,
            "href": self.href,
            "title_zh": self.title_zh,
            "summary_zh": self.summary_zh,
            "source_list": [_source_anchor_mapping(source) for source in self.source_list],
            "selection_rationale": dict(self.selection_rationale),
            "confidence_notice": self.confidence_notice,
            "related_history": list(self.related_history),
            "candidate_metadata": dict(self.candidate_metadata),
        }
        if self.media_attribution is not None:
            payload["media_attribution"] = dict(self.media_attribution)
        if self.media_fallback is not None:
            payload["media_fallback"] = self.media_fallback.as_mapping()
        return payload


@dataclass(frozen=True)
class BriefingGroup:
    section: str
    subcategory: str | None
    items: tuple[BriefingItem, ...]

    def as_mapping(self) -> dict[str, object]:
        return {
            "section": self.section,
            "subcategory": self.subcategory,
            "item_ids": [item.id for item in self.items],
        }


@dataclass(frozen=True)
class GeneratedBriefing:
    run_id: str
    items: tuple[BriefingItem, ...]
    groups: tuple[BriefingGroup, ...]
    deep_dive_details: tuple[DeepDiveDetail, ...]
    media_fallbacks: Mapping[str, MediaFallback]

    def deep_dive_for_item(self, briefing_item_id: str) -> DeepDiveDetail:
        for detail in self.deep_dive_details:
            if detail.briefing_item_id == briefing_item_id:
                return detail
        raise BriefingGenerationError(f"missing Deep-Dive Detail for {briefing_item_id}")


def generate_briefing(
    selected_candidates: tuple[SelectedCandidate, ...],
    *,
    run_id: str | None = None,
    deep_dive_base_path: str = "deep-dive",
) -> GeneratedBriefing:
    if not selected_candidates:
        raise BriefingGenerationError("selected_candidates must not be empty")

    resolved_run_id = run_id or selected_candidates[0].candidate.run_id
    items: list[BriefingItem] = []
    details: list[DeepDiveDetail] = []
    media_fallbacks: dict[str, MediaFallback] = {}

    for selected in selected_candidates:
        if selected.candidate.run_id != resolved_run_id:
            raise BriefingGenerationError("all selected candidates must share the briefing run_id")

        briefing_item = _briefing_item_from_selected(selected, run_id=resolved_run_id)
        fallback = _media_fallback(briefing_item) if briefing_item.source_media is None else None
        items.append(briefing_item)
        if fallback is not None:
            media_fallbacks[briefing_item.id] = fallback
        details.append(
            _deep_dive_detail_from_selected(
                selected,
                briefing_item=briefing_item,
                deep_dive_base_path=deep_dive_base_path,
                media_fallback=fallback,
            )
        )

    return GeneratedBriefing(
        run_id=resolved_run_id,
        items=tuple(items),
        groups=_group_items(tuple(items)),
        deep_dive_details=tuple(details),
        media_fallbacks=media_fallbacks,
    )


def _briefing_item_from_selected(selected: SelectedCandidate, *, run_id: str) -> BriefingItem:
    candidate = selected.candidate
    media_attribution = _media_attribution(candidate.source_media) if candidate.source_media else None
    notice = _confidence_notice(selected)
    return BriefingItem.from_mapping(
        {
            "id": f"brief_{_stable_suffix(candidate.id)}",
            "run_id": run_id,
            "candidate_id": candidate.id,
            "section": selected.section,
            "subcategory": selected.subcategory,
            "title_zh": _title_zh(selected),
            "bullets_zh": _bullets_zh(selected),
            "original_source_anchor": _source_anchor_mapping(candidate.original_source_anchor),
            "selection_rationale": selected.selection_rationale.as_mapping(),
            "confidence_level": selected.confidence_level,
            "source_media": _source_media_mapping(candidate.source_media) if candidate.source_media else None,
            "confidence_notice": notice,
            "media_attribution": media_attribution,
            "related_history": list(selected.related_history),
        }
    )


def _deep_dive_detail_from_selected(
    selected: SelectedCandidate,
    *,
    briefing_item: BriefingItem,
    deep_dive_base_path: str,
    media_fallback: MediaFallback | None,
) -> DeepDiveDetail:
    candidate = selected.candidate
    source_list = (candidate.original_source_anchor, *selected.corroborating_sources)
    return DeepDiveDetail(
        id=f"deep_{_stable_suffix(briefing_item.id)}",
        briefing_item_id=briefing_item.id,
        href=f"{deep_dive_base_path.rstrip('/')}/{briefing_item.id}.html",
        title_zh=briefing_item.title_zh,
        summary_zh=_summary_zh(selected),
        source_list=source_list,
        selection_rationale=selected.selection_rationale.as_mapping(),
        confidence_notice=_confidence_notice(selected),
        related_history=selected.related_history,
        candidate_metadata={
            "candidate_id": candidate.id,
            "source_id": candidate.source_id,
            "source_type": candidate.source_type,
            "published_at": candidate.published_at,
            "discovered_at": candidate.discovered_at,
            "section": selected.section,
            "subcategory": selected.subcategory,
            "confidence_level": selected.confidence_level,
        },
        media_attribution=briefing_item.media_attribution,
        media_fallback=media_fallback,
    )


def _title_zh(selected: SelectedCandidate) -> str:
    candidate = selected.candidate
    title = _compact(candidate.original_title, max_chars=80)
    if candidate.source_type == "academic_source":
        return f"论文：{title}"
    if selected.confidence_level == "low":
        return f"待核实：{title}"
    return f"{candidate.source_name}：{title}"


def _bullets_zh(selected: SelectedCandidate) -> list[str]:
    candidate = selected.candidate
    subcategory = selected.subcategory or "未细分子类"
    summary_label = "论文摘要" if candidate.source_type == "academic_source" else "摘要"
    bullets = [
        f"{summary_label}：{_summary_zh(selected)}",
        f"发布时间：{_published_label(candidate.published_at)}。",
        f"栏目：{selected.section}/{subcategory}；来源：{candidate.source_name}。",
    ]
    if selected.confidence_level != "high":
        bullets.append("置信度未达高档，请结合来源链接核验。")
    elif selected.corroborating_sources:
        bullets.append(f"另有 {len(selected.corroborating_sources)} 个相关来源保存在详情页。")
    elif selected.related_history:
        bullets.append(f"相关历史：{len(selected.related_history)} 条。")
    return bullets


def _summary_zh(selected: SelectedCandidate) -> str:
    candidate = selected.candidate
    raw = dict(candidate.raw_metadata)
    for key in ("description_excerpt", "summary_excerpt"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return _compact(value, max_chars=220)
    return _compact(candidate.original_title, max_chars=160)


def _published_label(value: str | None) -> str:
    if not value:
        return "来源未提供"
    return value.replace("T", " ").removesuffix("Z") + " UTC"


def _confidence_notice(selected: SelectedCandidate) -> dict[str, object] | None:
    if selected.confidence_level == "high":
        return None
    if not selected.confidence_notice:
        raise BriefingGenerationError("confidence_notice is required for medium and low confidence items")

    source_summary = selected.candidate.original_source_anchor.source_name
    display_text = selected.confidence_notice.strip()
    if not display_text.startswith("置信提示："):
        display_text = f"置信提示：{display_text}"
    if "当前依据" not in display_text:
        display_text = f"{display_text}；当前依据为 {source_summary} 原始来源。"

    supporting_sources = (selected.candidate.original_source_anchor, *selected.corroborating_sources)
    return {
        "reason": selected.confidence_notice,
        "display_text_zh": display_text,
        "supporting_sources": [_source_anchor_mapping(source) for source in supporting_sources],
    }


def _media_attribution(source_media: SourceMedia | None) -> dict[str, object] | None:
    if source_media is None:
        return None
    return {
        "display_text_zh": f"图片来源：{source_media.attribution} / {source_media.kind}",
        "source_url": source_media.url,
        "kind": source_media.kind,
        "eligibility_note": source_media.eligibility_note,
    }


def _media_fallback(briefing_item: BriefingItem) -> MediaFallback:
    return MediaFallback(
        briefing_item_id=briefing_item.id,
        reason="no_source_media",
        display_text_zh="未展示配图：当前来源未提供可复用 Source Media，MVP 不使用 AI 生成新闻图。",
    )


def _group_items(items: tuple[BriefingItem, ...]) -> tuple[BriefingGroup, ...]:
    grouped: dict[tuple[str, str | None], list[BriefingItem]] = {}
    for item in items:
        grouped.setdefault((item.section, item.subcategory), []).append(item)
    return tuple(
        BriefingGroup(section=section, subcategory=subcategory, items=tuple(group_items))
        for (section, subcategory), group_items in grouped.items()
    )


def _source_anchor_mapping(source: OriginalSourceAnchor) -> dict[str, str]:
    return {
        "source_name": source.source_name,
        "original_title": source.original_title,
        "source_url": source.source_url,
    }


def _source_media_mapping(source_media: SourceMedia) -> dict[str, str]:
    return {
        "url": source_media.url,
        "kind": source_media.kind,
        "attribution": source_media.attribution,
        "eligibility_note": source_media.eligibility_note,
    }


def _stable_suffix(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _compact(value: str, *, max_chars: int) -> str:
    stripped = " ".join(value.split())
    if len(stripped) <= max_chars:
        return stripped
    return stripped[: max_chars - 1].rstrip() + "…"
