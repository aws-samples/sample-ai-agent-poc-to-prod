"""Modular Strands tools composing the semantic layer over the data platform.

get_semantic_layer and query_source are SDK-optional: the @tool decorator falls
back to a no-op so this module imports and runs with strands uninstalled
(INV-9). Each tool body wraps its work in observability.span (a legal downward
dependency on the leaf; a true no-op when disabled).
"""
from __future__ import annotations
from pathlib import Path
from semantic import SemanticLayer
from data_platform import build_platform
from data_platform.types import SourceError
from observability import span            # leaf dependency (downward); no-op when disabled
from .guardrails import validate_source_id

try:
    from strands import tool
except Exception:
    def tool(fn=None, **_):              # keep importable/testable without strands
        return (lambda f: f) if fn is None else fn

_LAYER = SemanticLayer(Path(__file__).parent.parent / "semantic")   # cached (FR-7.2)
_PLATFORM = build_platform(_LAYER.schema(), Path(__file__).parent.parent)


@tool
def get_semantic_layer() -> str:
    """Return the governed semantic layer (catalog + field map + join semantics)
    so the agent can plan a correct multi-source lookup at runtime."""
    with span("tool.get_semantic_layer"):          # no-op when observability disabled
        return _LAYER.served_text()


@tool
def query_source(source_id: str) -> list[dict]:
    """Return rows for one source_id catalogued in the semantic layer. Unknown
    ids return a structured error. Consult get_semantic_layer first."""
    with span("tool.query_source", source_id=source_id):   # emits one timed JSON span when enabled
        err = validate_source_id(source_id, _PLATFORM.list_source_ids())
        if err:
            return [err]
        rows = _PLATFORM.read_rows(source_id)
        return [{"error": rows.error}] if isinstance(rows, SourceError) else rows
