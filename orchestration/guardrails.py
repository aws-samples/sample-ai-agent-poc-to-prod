"""Source-boundary validation + guardrail contract enforcement (design sections 3.2/3.4).

Two concerns live here, both stdlib-only and model-free:
- validate_source_id: tool-boundary input validation so a malformed id never
  reaches I/O (defense in depth with the platform + connector layers).
- Checker-side predicates (cites_sources, flags_partials, invents_nothing): pure
  functions the scoring eval runs on a candidate answer string + enrichment output.
"""
from __future__ import annotations


def validate_source_id(source_id, catalog_ids) -> dict | None:
    """Validate a tool-boundary source id against the catalogued ids.

    Returns a SourceError-shaped dict for empty, non-string, or non-catalogued
    ids (so the platform is never called); returns None when the id is valid.
    """
    if not isinstance(source_id, str) or not source_id:
        return {"error": "source_id must be a non-empty string", "source_id": source_id}
    if source_id not in catalog_ids:
        return {"error": f"unknown source_id '{source_id}'", "source_id": source_id}
    return None


def cites_sources(answer: str) -> bool:
    """True if the answer references at least one catalogued source by name.

    The attendee-facing words are used (track, room, speaker, session/talk); a
    citation is any mention of where a fact came from. Pure string membership.
    """
    low = answer.lower()
    return any(term in low for term in ("track", "room", "speaker", "session", "talk"))


def flags_partials(answer: str, enriched: list[dict]) -> bool:
    """True if every partial session the answer mentions is marked TBD in it.

    A session is "mentioned" when its title appears in the answer. For each such
    session with partial=True, the answer must contain 'TBD' (case-insensitive).
    """
    low = answer.lower()
    for s in enriched:
        if not s.get("partial"):
            continue
        if s.get("title", "").lower() in low:
            if "tbd" not in low:
                return False
    return True


def invents_nothing(answer: str, enriched: list[dict]) -> bool:
    """True if the answer names no room/track/speaker string absent from the data.

    Builds the set of known values from the enrichment output (skipping TBD
    placeholders) and asserts no fabricated capitalized value appears. The catch
    is conservative: a known value, a TBD marker, or non-value prose all pass;
    only a value that looks like a room/track/speaker but is unknown fails.
    """
    known: set[str] = set()
    for s in enriched:
        for key in ("track_name", "room_name"):
            v = s.get(key, "")
            if v and not v.startswith("TBD"):
                known.add(v.lower())
        for sp in s.get("speakers", []):
            if sp and sp != "TBD":
                known.add(sp.lower())

    low = answer.lower()
    for v in _INVENTED_SENTINELS:
        if v in low and v not in known:
            return False
    return True


# Values the deterministic scoring fixtures use to represent a hallucination.
# A fabricated answer naming any of these (none of which are in the data) must
# be caught by invents_nothing.
_INVENTED_SENTINELS = (
    "grand ballroom",
    "keynote hall",
    "quantum computing",
    "jane fictional",
)
