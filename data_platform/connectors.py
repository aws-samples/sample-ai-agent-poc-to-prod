from __future__ import annotations
from pathlib import Path
import csv
from typing import Protocol
from .types import SourceSpec, Row

class Connector(Protocol):
    """Reads all rows for a SourceSpec of a given kind. Pure read, no mutation."""
    def read(self, spec: SourceSpec, base_dir: Path) -> list[Row]: ...

class CsvConnector:
    """Connector for kind='csv': reads a CSV file at base_dir/location via DictReader."""
    def read(self, spec: SourceSpec, base_dir: Path) -> list[Row]:
        root = base_dir.resolve()
        path = (base_dir / spec.location).resolve()
        if root != path and root not in path.parents:   # path confinement (§3.2)
            raise ValueError(f"source location escapes data root: {spec.location}")
        with path.open(newline="") as f:
            return list(csv.DictReader(f))

# registry of connector kinds — extend by adding an entry, no platform edits
CONNECTORS: dict[str, "Connector"] = {"csv": CsvConnector()}

def register_connector(kind: str, connector: "Connector") -> None:
    """Register a new source-type backend (e.g. 'sqlite', 'http', 'parquet')."""
    CONNECTORS[kind] = connector
