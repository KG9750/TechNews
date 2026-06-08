"""Metadata-only source connector normalization."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from xml.etree import ElementTree

from .contracts import CandidateItem
from .run import ConnectorResult
from .source_policy import SourceAccessPolicy, SourcePolicyRow
from .source_registry import SourceRegistry, SourceRegistryEntry


class SourceConnectorError(ValueError):
    """Raised when metadata cannot be normalized into a CandidateItem."""


@dataclass(frozen=True)
class SourceMetadataInput:
    source_id: str
    content: str | None = None
    content_type: str = "text/plain"
    fetched_url: str | None = None
    completed_at: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class ParsedMetadataItem:
    source_name: str
    title: str
    url: str
    published_at: str | None
    raw_metadata: dict[str, object]


def normalize_source_input(
    source: SourceRegistryEntry,
    policy_row: SourcePolicyRow,
    source_input: SourceMetadataInput,
    *,
    run_id: str,
    discovered_at: str,
) -> CandidateItem:
    if source_input.source_id != source.id:
        raise SourceConnectorError(f"metadata input source_id does not match registry source: {source_input.source_id}")
    if policy_row.source_id != source.id or policy_row.source_type != source.source_type:
        raise SourceConnectorError(f"source policy row does not match registry source: {source.id}")
    if source_input.error:
        raise SourceConnectorError(source_input.error)
    if not source_input.content:
        raise SourceConnectorError(f"{source.id} metadata input is empty")

    if source.source_type == "public_feed":
        parsed = _parse_feed_metadata(source, source_input)
    elif source.source_type == "academic_source":
        parsed = _parse_academic_metadata(source, source_input)
    elif source.source_type == "manual_url":
        parsed = _parse_manual_url_metadata(source, source_input)
    else:
        raise SourceConnectorError(f"{source.source_type} is not implemented by first-version connectors")

    return CandidateItem.from_mapping(
        {
            "id": _candidate_id(source.id, parsed.url),
            "run_id": run_id,
            "source_id": source.id,
            "source_type": source.source_type,
            "source_name": parsed.source_name,
            "original_title": parsed.title,
            "source_url": parsed.url,
            "original_source_anchor": {
                "source_name": parsed.source_name,
                "original_title": parsed.title,
                "source_url": parsed.url,
            },
            "dedupe_key": f"{source.id}|{parsed.url}",
            "published_at": parsed.published_at,
            "discovered_at": discovered_at,
            "language": "en",
            "section_hints": list(source.section_hints()),
            "eligibility_state": policy_row.eligibility_state,
            "eligibility_notes": source.eligibility_notes,
            "raw_metadata": parsed.raw_metadata,
        }
    )


def run_source_connectors(
    registry: SourceRegistry,
    source_policy: SourceAccessPolicy,
    source_inputs: tuple[SourceMetadataInput, ...],
    *,
    run_id: str,
    discovered_at: str,
    delivery_deadline: str,
) -> tuple[ConnectorResult, ...]:
    results: list[ConnectorResult] = []
    for source_input in source_inputs:
        try:
            source = registry.require_first_version_connector(source_input.source_id)
            policy_row = source_policy.row_for(source.id)
            if not policy_row.production_auto_ingestion:
                results.append(
                    ConnectorResult(
                        source_id=source.id,
                        status="skipped",
                        warning=_policy_skip_warning(policy_row),
                    )
                )
                continue
            if _finished_after_deadline(source_input, delivery_deadline):
                results.append(
                    ConnectorResult(
                        source_id=source.id,
                        status="timeout",
                        warning="connector finished after delivery deadline",
                    )
                )
                continue
            candidate = normalize_source_input(
                source,
                policy_row,
                source_input,
                run_id=run_id,
                discovered_at=discovered_at,
            )
            results.append(ConnectorResult(source_id=source.id, status="completed", candidates=(candidate,)))
        except Exception as error:
            results.append(
                ConnectorResult(
                    source_id=source_input.source_id,
                    status="failed",
                    warning=f"metadata normalization failed: {error}",
                )
            )
    return tuple(results)


def _parse_feed_metadata(source: SourceRegistryEntry, source_input: SourceMetadataInput) -> ParsedMetadataItem:
    root = _xml_root(source_input.content or "")
    if _local_name(root.tag) == "feed":
        return _parse_atom_entry(source, source_input, root)

    channel = _first_child(root, "channel")
    item = _first_child(channel or root, "item")
    if item is None:
        raise SourceConnectorError(f"{source.id} feed metadata has no item")

    title = _required_text(_child_text(item, "title"), f"{source.id} item title")
    url = _required_text(_child_text(item, "link"), f"{source.id} item link")
    feed_title = _child_text(channel or root, "title")
    categories = [_text(child) for child in _children(item, "category") if _text(child)]
    description = _child_text(item, "description")
    raw_metadata: dict[str, object] = {
        "content_type": source_input.content_type,
        "feed_title": feed_title or source.name,
    }
    if categories:
        raw_metadata["categories"] = categories
    if description:
        raw_metadata["description_excerpt"] = _excerpt(description)
    return ParsedMetadataItem(
        source_name=source.name,
        title=title,
        url=url,
        published_at=_parse_optional_timestamp(_child_text(item, "pubDate")),
        raw_metadata=raw_metadata,
    )


def _parse_academic_metadata(source: SourceRegistryEntry, source_input: SourceMetadataInput) -> ParsedMetadataItem:
    return _parse_atom_entry(source, source_input, _xml_root(source_input.content or ""))


def _parse_atom_entry(
    source: SourceRegistryEntry,
    source_input: SourceMetadataInput,
    root: ElementTree.Element,
) -> ParsedMetadataItem:
    entry = root if _local_name(root.tag) == "entry" else _first_child(root, "entry")
    if entry is None:
        raise SourceConnectorError(f"{source.id} Atom metadata has no entry")

    title = _required_text(_child_text(entry, "title"), f"{source.id} entry title")
    url = _atom_url(entry) or _child_text(entry, "id")
    url = _required_text(url, f"{source.id} entry URL")
    authors = [_child_text(author, "name") for author in _children(entry, "author")]
    categories = [category.attrib.get("term") or _text(category) for category in _children(entry, "category")]
    raw_metadata: dict[str, object] = {
        "content_type": source_input.content_type,
        "feed_title": _child_text(root, "title") or source.name,
    }
    if authors:
        raw_metadata["authors"] = [author for author in authors if author]
    if categories:
        raw_metadata["categories"] = [category for category in categories if category]
    summary = _child_text(entry, "summary")
    if summary:
        raw_metadata["summary_excerpt"] = _excerpt(summary)
    return ParsedMetadataItem(
        source_name=source.name,
        title=title,
        url=url,
        published_at=_parse_optional_timestamp(_child_text(entry, "published") or _child_text(entry, "updated")),
        raw_metadata=raw_metadata,
    )


def _parse_manual_url_metadata(source: SourceRegistryEntry, source_input: SourceMetadataInput) -> ParsedMetadataItem:
    parser = _PageMetadataParser()
    parser.feed(source_input.content or "")
    title = parser.meta.get("og:title") or parser.title
    title = _required_text(title, f"{source.id} page title")
    url = parser.canonical_url or parser.meta.get("og:url") or source_input.fetched_url
    url = _required_text(url, f"{source.id} page URL")
    source_name = parser.meta.get("og:site_name") or source.name
    description = parser.meta.get("description") or parser.meta.get("og:description")
    raw_metadata: dict[str, object] = {
        "content_type": source_input.content_type,
        "site_name": source_name,
    }
    if description:
        raw_metadata["description_excerpt"] = _excerpt(description)
    if parser.canonical_url:
        raw_metadata["canonical_url"] = parser.canonical_url
    if parser.meta.get("og:image"):
        raw_metadata["open_graph_image_url"] = parser.meta["og:image"]
    return ParsedMetadataItem(
        source_name=source_name,
        title=title,
        url=url,
        published_at=_parse_optional_timestamp(parser.meta.get("article:published_time")),
        raw_metadata=raw_metadata,
    )


class _PageMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.canonical_url: str | None = None
        self.title = ""
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value for key, value in attrs if value}
        if tag == "title":
            self._in_title = True
            return
        if tag == "meta":
            key = attributes.get("property") or attributes.get("name")
            content = attributes.get("content")
            if key and content:
                self.meta[key.lower()] = content.strip()
            return
        if tag == "link" and attributes.get("href"):
            rel = attributes.get("rel", "").lower().split()
            if "canonical" in rel:
                self.canonical_url = attributes["href"].strip()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            self.title = " ".join(part.strip() for part in self._title_parts if part.strip())


def _policy_skip_warning(policy_row: SourcePolicyRow) -> str:
    if policy_row.requires_per_item_review or policy_row.connector_mode.startswith("manual_url"):
        return "manual-only by Source Access Policy"
    if policy_row.connector_mode.endswith("_probe"):
        return "probe-only by Source Access Policy"
    return "production auto-ingestion disabled by Source Access Policy"


def _finished_after_deadline(source_input: SourceMetadataInput, delivery_deadline: str) -> bool:
    if not source_input.completed_at:
        return False
    return _parse_datetime(source_input.completed_at) > _parse_datetime(delivery_deadline)


def _xml_root(content: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise SourceConnectorError("invalid XML metadata") from exc


def _children(element: ElementTree.Element | None, name: str) -> list[ElementTree.Element]:
    if element is None:
        return []
    return [child for child in list(element) if _local_name(child.tag) == name]


def _first_child(element: ElementTree.Element | None, name: str) -> ElementTree.Element | None:
    children = _children(element, name)
    return children[0] if children else None


def _child_text(element: ElementTree.Element | None, name: str) -> str | None:
    child = _first_child(element, name)
    return _text(child) if child is not None else None


def _text(element: ElementTree.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    text = re.sub(r"\s+", " ", element.text).strip()
    return text or None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _atom_url(entry: ElementTree.Element) -> str | None:
    for link in _children(entry, "link"):
        rel = link.attrib.get("rel", "alternate")
        href = link.attrib.get("href")
        if href and rel == "alternate":
            return href
    return None


def _required_text(value: str | None, label: str) -> str:
    if not value:
        raise SourceConnectorError(f"{label} is required")
    return value


def _excerpt(value: str, limit: int = 280) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _parse_optional_timestamp(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        parsed = _parse_datetime(value)
    return _format_utc(parsed)


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SourceConnectorError(f"invalid timestamp: {value}") from exc


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _candidate_id(source_id: str, url: str) -> str:
    digest = hashlib.sha1(f"{source_id}|{url}".encode("utf-8")).hexdigest()[:12]
    safe_source = re.sub(r"[^a-z0-9]+", "_", source_id.lower()).strip("_")
    return f"cand_{safe_source}_{digest}"
