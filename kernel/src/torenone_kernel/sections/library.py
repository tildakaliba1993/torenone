"""Section library — lookup + ordering for auto-sizing.

⚠️ No section data ships in this repository. The production library is built from the curated
SAISC section list supplied by the registered engineer (co-founder). Until that data exists,
any attempt to run a real design will fail loudly (there is nothing to size against) — which is
the correct, safe behaviour. Tests use a clearly-synthetic, non-design fixture only.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from importlib.resources import files
from pathlib import Path

from torenone_kernel.sections.properties import SectionProperties


class SectionLibrary:
    """An immutable, de-duplicated collection of sections, queryable by designation."""

    def __init__(self, sections: Iterable[SectionProperties]) -> None:
        by_name: dict[str, SectionProperties] = {}
        for section in sections:
            if section.designation in by_name:
                raise ValueError(f"duplicate section designation: {section.designation!r}")
            by_name[section.designation] = section
        self._by_name = by_name

    @classmethod
    def from_records(cls, records: Iterable[dict[str, object]]) -> SectionLibrary:
        return cls(SectionProperties(**record) for record in records)

    @classmethod
    def load_default(cls) -> SectionLibrary:
        """Load the packaged SAISC section dataset.

        ⚠️ PROVISIONAL data — parsed from the SAISC 'Database of Structural Steel Sections'
        and pending a registered engineer's spot-check sign-off (see the data file's `_meta`
        and PRD Phase 8). Use for development; not yet cleared for production design output.
        """
        raw = (
            files("torenone_kernel.sections")
            .joinpath("data/saisc_sections.json")
            .read_text(encoding="utf-8")
        )
        return cls.from_records(json.loads(raw)["sections"])

    @classmethod
    def load_json(cls, path: str | Path) -> SectionLibrary:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("section data file must contain a JSON array of section records")
        return cls.from_records(data)

    def get(self, designation: str) -> SectionProperties:
        try:
            return self._by_name[designation]
        except KeyError:
            raise KeyError(f"unknown section: {designation!r}") from None

    def __contains__(self, designation: object) -> bool:
        return designation in self._by_name

    def __len__(self) -> int:
        return len(self._by_name)

    def designations(self) -> list[str]:
        return list(self._by_name)

    def by_increasing_mass(self) -> list[SectionProperties]:
        """Sections ordered lightest-first — the search order for auto-sizing (1.11)."""
        return sorted(self._by_name.values(), key=lambda s: s.mass_per_metre_kg_m)
