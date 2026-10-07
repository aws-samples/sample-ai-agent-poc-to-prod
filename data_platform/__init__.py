"""Reusable, domain-agnostic data foundation: typed source access (list/get/read) driven by an external catalog. Knows nothing about conferences."""
from pathlib import Path
from .platform import DataPlatform
from .catalog import Catalog
from .types import SourceSpec, Row, SourceError
from .connectors import Connector, CsvConnector, register_connector

def build_platform(schema: list[dict], base_dir: Path) -> DataPlatform:
    """Build a DataPlatform from a machine-readable source list + a data root.
    This is the single integration point the orchestration layer calls."""
    return DataPlatform(Catalog.from_schema(schema), base_dir)
