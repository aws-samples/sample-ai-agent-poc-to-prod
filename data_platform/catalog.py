from __future__ import annotations
from typing import Iterable
from .types import SourceSpec

class Catalog:
    """Holds SourceSpecs built from an external source list (the semantic layer's).
    Domain-agnostic: never names conference concepts."""
    def __init__(self, specs: Iterable[SourceSpec]):
        self._specs: dict[str, SourceSpec] = {s.id: s for s in specs}

    @classmethod
    def from_schema(cls, schema: list[dict]) -> "Catalog":
        """Build from the machine-readable source list entries:
        {"id","kind","location","grain","description","options"}."""
        return cls(SourceSpec(
            id=d["id"], kind=d.get("kind", "csv"), location=d["location"],
            grain=d.get("grain", ""), description=d.get("description", ""),
            options=d.get("options", {}),
        ) for d in schema)

    def ids(self) -> list[str]: return list(self._specs)
    def get(self, source_id: str) -> SourceSpec | None: return self._specs.get(source_id)
    def __contains__(self, source_id: str) -> bool: return source_id in self._specs
