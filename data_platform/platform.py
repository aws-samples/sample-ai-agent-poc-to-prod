from __future__ import annotations
from pathlib import Path
from .catalog import Catalog
from .connectors import CONNECTORS
from .types import SourceSpec, Row, SourceError

class DataPlatform:
    """Domain-agnostic access to catalogued sources. Reusable by any app that
    supplies a catalog + connectors. No conference vocabulary appears here."""
    def __init__(self, catalog: Catalog, base_dir: Path):
        self._catalog = catalog
        self._base_dir = base_dir

    def list_sources(self) -> list[SourceSpec]:
        """All catalogued source specs."""
        return [self._catalog.get(i) for i in self._catalog.ids()]

    def list_source_ids(self) -> list[str]:
        """Catalogued source ids. Used by the tool-boundary id validator (§3.2).
        Domain-agnostic: returns catalog keys, never conference vocabulary."""
        return self._catalog.ids()

    def get_source(self, source_id: str) -> SourceSpec | SourceError:
        """One source's metadata, or a structured error for unknown ids."""
        spec = self._catalog.get(source_id)
        return spec if spec else SourceError(f"unknown source_id '{source_id}'", source_id)

    def read_rows(self, source_id: str) -> list[Row] | SourceError:
        """Rows for one catalogued source, or a structured error. Validates the id
        against the catalog and never reads outside the data root (§3.2)."""
        spec = self._catalog.get(source_id)
        if spec is None:
            return SourceError(f"unknown source_id '{source_id}'", source_id)
        connector = CONNECTORS.get(spec.kind)
        if connector is None:
            return SourceError(f"no connector for kind '{spec.kind}'", source_id)
        try:
            return connector.read(spec, self._base_dir)
        except Exception as e:                      # includes path-escape ValueError
            return SourceError(f"read failed for '{source_id}': {e}", source_id)
