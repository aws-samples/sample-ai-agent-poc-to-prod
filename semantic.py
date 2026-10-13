"""LAYER 2 (the reader) — a tiny door onto the governed semantic layer.

THIS IS THE WHOLE IDEA OF THE PROJECT:

    The knowledge of how your data fits together does NOT live in the LLM's
    system prompt. It lives in semantic/*.md — governed, versioned markdown the
    agent reads at RUNTIME. Build it once; add a track/room/source by editing
    the layer, not the code.

semantic/ (the folder next to this file) holds that governed content:
  - sources.md    what sources exist
  - field_map.md  attendee words -> physical columns
  - joins.md      how sources relate (the only home of correlation logic)

This module just reads that folder. Two plain functions, no class, no cache.
"""
from __future__ import annotations
from pathlib import Path

# The governed markdown lives in the semantic/ folder beside this module.
_SEM_DIR = Path(__file__).resolve().parent / "semantic"
_FILES = ("sources.md", "field_map.md", "joins.md")


def read_semantic_layer() -> str:
    """Return the governed layer as ONE string: the three markdown files joined
    with a '---' separator. This is exactly the text the agent reads before it
    answers, so it can plan a correct multi-source lookup."""
    return "\n\n---\n\n".join(
        (_SEM_DIR / name).read_text(encoding="utf-8") for name in _FILES
    )


def list_sources() -> dict[str, str]:
    """Return {source_id: relative_csv_path} for every known source.

    This small dict MIRRORS the table in semantic/sources.md — to add a source,
    add a row there AND a line here. That is the governance point in miniature:
    the catalog is explicit and lives with the layer, not buried in agent code.
    """
    return {
        "sessions": "data/sessions.csv",
        "tracks":   "data/tracks.csv",
        "speakers": "data/speakers.csv",
        "rooms":    "data/rooms.csv",
    }
