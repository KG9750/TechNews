"""Technology domain taxonomy loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class TaxonomyError(ValueError):
    """Raised when a taxonomy seed file is missing required configuration."""


@dataclass(frozen=True)
class TaxonomySection:
    name: str
    subcategories: tuple[str, ...]


@dataclass(frozen=True)
class TechnologyDomainTemplate:
    name: str
    sections: tuple[TaxonomySection, ...]

    @classmethod
    def from_markdown_file(cls, path: Path | str, name: str = "technology") -> "TechnologyDomainTemplate":
        rows = _read_sections(Path(path))
        if not rows:
            raise TaxonomyError("technology domain template must include sections")
        return cls(
            name=name,
            sections=tuple(TaxonomySection(section, tuple(subcategories)) for section, subcategories in rows),
        )

    def section_names(self) -> tuple[str, ...]:
        return tuple(section.name for section in self.sections)

    def section(self, name: str) -> TaxonomySection:
        for section in self.sections:
            if section.name == name:
                return section
        raise TaxonomyError(f"unknown taxonomy section: {name}")

    def subcategories_for(self, section_name: str) -> tuple[str, ...]:
        return self.section(section_name).subcategories

    def require_mvp_coverage(
        self,
        *,
        required_sections: set[str],
        required_embodied_subcategories: set[str],
        minimum_subcategories: int = 3,
    ) -> None:
        missing_sections = sorted(required_sections - set(self.section_names()))
        if missing_sections:
            raise TaxonomyError("taxonomy missing MVP sections: " + ", ".join(missing_sections))

        for section in self.sections:
            if section.name in required_sections and len(section.subcategories) < minimum_subcategories:
                raise TaxonomyError(f"{section.name} must have at least {minimum_subcategories} subcategories")

        embodied = set(self.subcategories_for("Embodied Intelligence"))
        missing_embodied = sorted(required_embodied_subcategories - embodied)
        if missing_embodied:
            raise TaxonomyError("Embodied Intelligence missing subcategories: " + ", ".join(missing_embodied))


def _read_sections(path: Path) -> list[tuple[str, list[str]]]:
    rows: list[tuple[str, list[str]]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        columns = _split_markdown_row(line)
        if not columns or len(columns) != 2:
            continue
        section, subcategories = columns
        if section in {"Section", "---"} or set(section) == {"-"}:
            continue
        parsed_subcategories = [part.strip() for part in subcategories.split(";") if part.strip()]
        if parsed_subcategories:
            rows.append((section, parsed_subcategories))
    return rows


def _split_markdown_row(line: str) -> list[str] | None:
    if not line.startswith("|"):
        return None
    return [part.strip() for part in line.strip().strip("|").split("|")]
