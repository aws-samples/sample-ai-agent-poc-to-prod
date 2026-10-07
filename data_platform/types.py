from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping

Row = dict[str, str]                      # one record; string-valued like csv.DictReader

@dataclass(frozen=True)
class SourceSpec:
    """Describes one catalogued source, domain-agnostically.
    `kind` selects the connector; `location` + `options` are connector-specific."""
    id: str                               # catalog id, e.g. "sessions"
    kind: str                             # connector type key, e.g. "csv"
    location: str                         # connector-specific locator, e.g. relative path
    grain: str = ""                       # natural key column name (metadata only)
    description: str = ""
    options: Mapping[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class SourceError:
    """Structured, non-raising error returned for unknown/invalid access."""
    error: str
    source_id: str | None = None
