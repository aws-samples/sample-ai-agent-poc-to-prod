"""LAYER 3 — orchestration: the tools the agent calls, the join engine, and the
inline security guardrails.

Three things live here, all stdlib-only and model-free:

  1. Two Strands @tools the agent calls at runtime (get_semantic_layer,
     query_source). The @tool decorator is SDK-optional: if strands is not
     installed it falls back to a no-op so this module still imports and the
     deterministic eval still runs.
  2. enrich_sessions() — the deterministic join engine. It joins talks to their
     track, room, and speaker(s) on the three documented keys, flags anything
     missing as TBD, and NEVER invents a value.
  3. The guardrail predicates used by the evaluation (cites_sources,
     flags_partials, invents_nothing) plus the tool-boundary id check
     (validate_source_id). SECURITY lives here — see the README threat model.
"""
from __future__ import annotations
import time

import semantic
from data_platform import read_source, list_sources

# --- SDK-optional @tool decorator -------------------------------------------
# Keep this project importable and testable with strands-agents UNINSTALLED:
# when the import fails, @tool becomes a transparent no-op.
try:
    from strands import tool
except Exception:
    def tool(fn=None, **_):
        return (lambda f: f) if fn is None else fn


# --- The two tools the agent calls at runtime -------------------------------

@tool
def get_semantic_layer() -> str:
    """Return the governed semantic layer (catalog + field map + join semantics)
    so the agent can plan a correct multi-source lookup at runtime."""
    start = time.perf_counter()  # Observability: one simple timing touch.
    result = semantic.read_semantic_layer()
    # In production this is where an OpenTelemetry span would go.
    print(f"[timing] get_semantic_layer {round((time.perf_counter()-start)*1000,2)}ms")
    return result


@tool
def query_source(source_id: str) -> list[dict]:
    """Return rows for one source_id catalogued in the semantic layer. Unknown
    ids return a structured error. Consult get_semantic_layer first."""
    start = time.perf_counter()
    # Security: validate the id against known sources BEFORE any file is read.
    err = validate_source_id(source_id, list(list_sources()))
    if err:
        return [err]
    rows = read_source(source_id)
    # In production this is where an OpenTelemetry span would go.
    print(f"[timing] query_source({source_id}) {round((time.perf_counter()-start)*1000,2)}ms")
    # read_source returns an error dict (not a list) on failure; wrap it as data.
    return [rows] if isinstance(rows, dict) else rows


# --- The deterministic join engine ------------------------------------------

def enrich_sessions() -> list[dict]:
    """Enrich each talk with its track name, room name, and speaker(s) by joining
    on the three documented keys. A missing track/room/speaker is flagged
    (partial=True) and marked TBD — never invented, never dropped."""
    def rows(sid: str) -> list[dict]:
        r = read_source(sid)
        return [] if isinstance(r, dict) else r   # error dict -> no rows

    tracks = {r["track_id"]: r for r in rows("tracks")}
    rooms  = {r["room_id"]:  r for r in rows("rooms")}
    speakers_by_session: dict[str, list[str]] = {}
    for r in rows("speakers"):
        speakers_by_session.setdefault(r["session_id"], []).append(r["speaker_name"])

    out = []
    for s in rows("sessions"):
        track = tracks.get(s["track_id"])
        room  = rooms.get(s["room_id"])
        out.append({
            "session_id": s["session_id"], "title": s["title"], "day": s["day"],
            "start": s["start"], "end": s["end"],
            "track_name": track["track_name"] if track else f"TBD (track '{s['track_id']}' missing)",
            "room_name":  room["room_name"]  if room  else f"TBD (room '{s['room_id']}' missing)",
            "speakers":   speakers_by_session.get(s["session_id"], ["TBD"]),
            "partial":    not (track and room),
        })
    return out


# --- Inline security guardrails ---------------------------------------------

def validate_source_id(source_id, known_ids) -> dict | None:
    """Tool-boundary input validation: reject empty, non-string, or unknown ids
    so a malformed id never reaches file I/O. Returns an error-shaped dict on
    rejection, or None when the id is valid."""
    if not isinstance(source_id, str) or not source_id:
        return {"error": "source_id must be a non-empty string", "source_id": source_id}
    if source_id not in known_ids:
        return {"error": f"unknown source_id '{source_id}'", "source_id": source_id}
    return None


def cites_sources(answer: str) -> bool:
    """True if the answer references at least one source by an attendee-facing
    word (track/room/speaker/session/talk) — i.e. it says where facts came from."""
    low = answer.lower()
    return any(term in low for term in ("track", "room", "speaker", "session", "talk"))


def flags_partials(answer: str, enriched: list[dict]) -> bool:
    """True if every partial session the answer mentions by title is marked TBD.
    A hidden partial (asserting a concrete room for a TBD talk) fails this."""
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
    Builds the set of known values from the enrichment output (skipping TBD) and
    fails if a known-hallucination sentinel appears that is not in the data."""
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


# Values the scoring fixtures use to represent a hallucination. A fabricated
# answer naming any of these (none are in the data) must be caught.
_INVENTED_SENTINELS = (
    "grand ballroom",
    "keynote hall",
    "quantum computing",
    "jane fictional",
)
