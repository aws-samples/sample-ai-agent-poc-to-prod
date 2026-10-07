"""Contract floor + version consistency checks (design sections 5A/6).

The four reference checks (the floor) re-pointed at enrich_sessions(platform),
plus the version source-of-truth guard (#10). All run with NO model and NO
network: they import only stdlib + project modules and build the platform via
build_platform(SemanticLayer(sem_dir).schema(), project_root) — the same wiring
orchestration/tools.py uses.
"""
from __future__ import annotations
import re
from pathlib import Path

from semantic import SemanticLayer
from data_platform import build_platform
from data_platform.types import SourceError
from orchestration.enrichment import enrich_sessions

_ROOT = Path(__file__).resolve().parent.parent
_SEM_DIR = _ROOT / "semantic"

# version-parse rule (design section 2.6): first whitespace-delimited token after
# the marker, so sources.md's trailing prose is ignored. Naive split is forbidden.
_VERSION_RE = re.compile(r"#\s*version:\s*(\S+)")
_MARKDOWN_FILES = ("sources.md", "field_map.md", "joins.md")


def _layer() -> SemanticLayer:
    return SemanticLayer(_SEM_DIR)


def _platform(layer: SemanticLayer):
    return build_platform(layer.schema(), _ROOT)


def test_layer_served() -> None:
    """#1 Layer served: served text carries the catalog + join semantics headers
    and the session_id key."""
    served = _layer().served_text()
    assert "Source Catalog" in served, "served text missing 'Source Catalog'"
    assert "Join Semantics" in served, "served text missing 'Join Semantics'"
    assert "session_id" in served, "served text missing 'session_id'"
    print("PASS #1 test_layer_served: semantic layer served (catalog + join semantics present)")


def test_sources_loadable() -> None:
    """#2 For every id in list_source_ids(), read_rows(id) returns a non-empty
    list (not a SourceError)."""
    platform = _platform(_layer())
    for sid in platform.list_source_ids():
        rows = platform.read_rows(sid)
        assert not isinstance(rows, SourceError), f"{sid} returned a SourceError: {rows}"
        assert isinstance(rows, list) and rows, f"{sid} returned no rows"
    print("PASS #2 test_sources_loadable: every catalogued source loads with rows")


def test_enrichment_joins() -> None:
    """#3 S06 enriches to track 'AI & Agents', room 'Workshop Room C', speaker
    'Sam Okoye', partial=False — joined on the documented keys."""
    rows = {r["session_id"]: r for r in enrich_sessions(_platform(_layer()))}
    s06 = rows["S06"]  # Production-Grade Agent Architectures
    assert s06["track_name"] == "AI & Agents", s06["track_name"]
    assert s06["room_name"] == "Workshop Room C", s06["room_name"]
    assert "Sam Okoye" in s06["speakers"], s06["speakers"]
    assert s06["partial"] is False, s06["partial"]
    print("PASS #3 test_enrichment_joins: talk enriched across tracks/rooms/speakers on documented keys")


def test_partial_flagged() -> None:
    """#4 S10 (room_id='Main', absent from rooms) is partial=True with a TBD room
    — not dropped, not invented."""
    rows = {r["session_id"]: r for r in enrich_sessions(_platform(_layer()))}
    s10 = rows["S10"]  # Panel in room 'Main', which is absent from rooms.csv
    assert s10["partial"] is True, s10["partial"]
    assert "TBD" in s10["room_name"], s10["room_name"]
    print("PASS #4 test_partial_flagged: missing room flagged as TBD (partial), not invented or dropped")


def test_version_consistent() -> None:
    """#10 schema.json['version'] equals the first token parsed from each markdown
    '# version:' line (trailing prose ignored). Keeps the single source of truth
    (schema.json) and the human-facing markdown comment from drifting."""
    layer = _layer()
    schema_version = str(layer.version())
    for name in _MARKDOWN_FILES:
        text = (_SEM_DIR / name).read_text(encoding="utf-8")
        match = _VERSION_RE.search(text)
        assert match, f"{name} has no '# version:' marker"
        token = match.group(1)
        assert token == schema_version, (
            f"{name} version '{token}' != schema.json version '{schema_version}'"
        )
    print(f"PASS #10 test_version_consistent: all markdown versions match schema.json ({schema_version})")


def run_all() -> None:
    """Run the five contract/version checks (floor #1-#4 + version #10)."""
    test_layer_served()
    test_sources_loadable()
    test_enrichment_joins()
    test_partial_flagged()
    test_version_consistent()


if __name__ == "__main__":
    run_all()
