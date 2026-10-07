"""Deterministic join/enrichment engine (no model, no network).

Direct port of the reference enrich_sessions(), re-pointed at the typed
DataPlatform (design section 3.3). The join keys and partial/TBD semantics are
byte-for-byte the reference's; the only change is the signature.
"""
from __future__ import annotations
from data_platform import DataPlatform
from data_platform.types import SourceError


def enrich_sessions(platform: DataPlatform) -> list[dict]:
    """Deterministic reference: enrich each talk with track name, room name, and
    speaker(s) on the documented keys. Missing track/room/speaker is flagged
    (partial=True) and marked TBD, never invented, never dropped."""
    def rows(sid: str) -> list[dict]:
        r = platform.read_rows(sid)
        return [] if isinstance(r, SourceError) else r

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
