"""First-version source registry loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .contracts import SOURCE_TYPES
from .source_policy import SourceAccessPolicy


FIRST_VERSION_SOURCE_TYPES = {"public_feed", "academic_source", "manual_url"}
MVP_STATES = {"first-version", "deferred"}


class SourceRegistryError(ValueError):
    """Raised when a source registry entry is missing or unsafe to run."""


@dataclass(frozen=True)
class SourceRegistryEntry:
    id: str
    name: str
    source_type: str
    url_or_feed: str
    primary_section: str
    secondary_sections: tuple[str, ...]
    trust_tier: str
    media_availability: str
    mvp_state: str
    eligibility_notes: str

    @classmethod
    def from_mapping(cls, payload: dict[str, str]) -> "SourceRegistryEntry":
        source_type = _required_value(payload, "Type", SOURCE_TYPES)
        mvp_state = _required_value(payload, "MVP state", MVP_STATES)
        secondary_sections = tuple(
            part.strip() for part in _required_str(payload, "Secondary sections").split(",") if part.strip()
        )
        return cls(
            id=_required_str(payload, "ID"),
            name=_required_str(payload, "Source"),
            source_type=source_type,
            url_or_feed=_required_str(payload, "URL or feed"),
            primary_section=_required_str(payload, "Primary section"),
            secondary_sections=secondary_sections,
            trust_tier=_required_str(payload, "Trust tier"),
            media_availability=_required_str(payload, "Media"),
            mvp_state=mvp_state,
            eligibility_notes=_required_str(payload, "Eligibility notes"),
        )

    def is_first_version(self) -> bool:
        return self.mvp_state == "first-version"

    def is_deferred(self) -> bool:
        return self.mvp_state == "deferred"

    def supports_first_version_connector(self) -> bool:
        return self.is_first_version() and self.source_type in FIRST_VERSION_SOURCE_TYPES

    def section_hints(self) -> tuple[str, ...]:
        return (self.primary_section, *self.secondary_sections)


class SourceRegistry:
    """Application-facing view of seed sources and first-version connector eligibility."""

    def __init__(self, entries: tuple[SourceRegistryEntry, ...]) -> None:
        ids = [entry.id for entry in entries]
        duplicates = sorted({source_id for source_id in ids if ids.count(source_id) > 1})
        if duplicates:
            raise SourceRegistryError("duplicate source IDs: " + ", ".join(duplicates))
        self._entries = entries
        self._by_id = {entry.id: entry for entry in entries}

    @classmethod
    def from_markdown_file(cls, path: Path | str) -> "SourceRegistry":
        rows = _read_registry_rows(Path(path))
        if not rows:
            raise SourceRegistryError("source registry must include source rows")
        return cls(tuple(SourceRegistryEntry.from_mapping(row) for row in rows))

    def entries(self) -> tuple[SourceRegistryEntry, ...]:
        return self._entries

    def entry_for(self, source_id: str) -> SourceRegistryEntry:
        try:
            return self._by_id[source_id]
        except KeyError as exc:
            raise SourceRegistryError(f"source_id is not in Source Registry: {source_id}") from exc

    def first_version_sources(self) -> tuple[SourceRegistryEntry, ...]:
        return tuple(entry for entry in self._entries if entry.is_first_version())

    def deferred_sources(self) -> tuple[SourceRegistryEntry, ...]:
        return tuple(entry for entry in self._entries if entry.is_deferred())

    def first_version_connectors(self) -> tuple[SourceRegistryEntry, ...]:
        return tuple(entry for entry in self._entries if entry.supports_first_version_connector())

    def first_version_source_types(self) -> set[str]:
        return {entry.source_type for entry in self.first_version_sources()}

    def require_first_version_connector(self, source_id: str) -> SourceRegistryEntry:
        entry = self.entry_for(source_id)
        if not entry.is_first_version():
            raise SourceRegistryError(f"{source_id} is not a first-version source")
        if entry.source_type not in FIRST_VERSION_SOURCE_TYPES:
            raise SourceRegistryError(f"{source_id} source_type is not supported for first-version connectors")
        return entry

    def production_enabled_connectors(self, source_policy: SourceAccessPolicy) -> tuple[SourceRegistryEntry, ...]:
        return tuple(
            self.require_first_version_connector(row.source_id) for row in source_policy.production_enabled_sources()
        )

    def require_production_enabled_connector(
        self,
        source_id: str,
        source_policy: SourceAccessPolicy,
    ) -> SourceRegistryEntry:
        entry = self.require_first_version_connector(source_id)
        enabled_ids = {row.source_id for row in source_policy.production_enabled_sources()}
        if source_id not in enabled_ids:
            raise SourceRegistryError(f"{source_id} is not enabled for production auto-ingestion")
        return entry


def _read_registry_rows(path: Path) -> list[dict[str, str]]:
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        columns = _split_markdown_row(line)
        if not columns:
            continue
        if columns[0] == "ID":
            header = columns
            continue
        if not header or columns[0].startswith("---"):
            continue
        if columns[0].startswith("src-"):
            if len(columns) != len(header):
                raise SourceRegistryError(f"{columns[0]} has wrong column count")
            rows.append(dict(zip(header, columns)))
    return rows


def _split_markdown_row(line: str) -> list[str] | None:
    if not line.startswith("|"):
        return None
    return [part.strip() for part in line.strip().strip("|").split("|")]


def _required_str(payload: dict[str, str], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SourceRegistryError(f"{key} must be a non-empty string")
    return value


def _required_value(payload: dict[str, str], key: str, allowed: set[str]) -> str:
    value = _required_str(payload, key)
    if value not in allowed:
        raise SourceRegistryError(f"{key} must be one of {sorted(allowed)}")
    return value
