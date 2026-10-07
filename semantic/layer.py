# semantic/layer.py
from __future__ import annotations
import json
from pathlib import Path

_FILES = ("sources.md", "field_map.md", "joins.md")

class SemanticLayer:
    """Governed, versioned semantic layer. Assembles the markdown served to the
    agent and exposes the machine-readable schema + version. Holds description,
    not data or logic: it never reads a CSV and never performs a join."""

    def __init__(self, sem_dir: Path):
        self._dir = Path(sem_dir)
        self._served: str | None = None     # memoized assembled markdown (FR-7.2)
        self._schema: dict | None = None     # memoized parsed schema.json

    def served_text(self) -> str:
        """The governed layer as one served string: the three markdown files joined
        with '\n\n---\n\n' (byte-for-byte the reference's get_semantic_layer body).
        Assembled once and cached."""
        if self._served is None:
            self._served = "\n\n---\n\n".join(
                (self._dir / n).read_text(encoding="utf-8") for n in _FILES
            )
        return self._served

    def schema(self) -> list[dict]:
        """The machine-readable source list consumed by build_platform /
        Catalog.from_schema — i.e. schema.json['sources']."""
        return self._load()["sources"]

    def joins(self) -> list[dict]:
        """Documented join keys from schema.json['joins'] (empty list if absent)."""
        return self._load().get("joins", [])

    def version(self) -> str:
        """Authoritative layer version — schema.json['version']. The only version
        source of truth; the markdown '# version:' comment mirrors it by governance."""
        return str(self._load().get("version", "0.0"))

    def reload(self) -> None:
        """Invalidate both caches so a live edit to the semantic files (Beat 4) or a
        version bump is picked up on the next access. The only invalidation path."""
        self._served = None
        self._schema = None

    def _load(self) -> dict:
        if self._schema is None:
            self._schema = json.loads(
                (self._dir / "schema.json").read_text(encoding="utf-8")
            )
        return self._schema
