"""The evaluation suite — the "catch hallucinations early" theme in one file.

Everything here runs with NO model and NO network: it imports only stdlib + the
project modules and uses fixed, hard-coded candidate answers. Run it as:

    python evaluation.py

It prints PASS/FAIL for each check and exits 0 only if all pass. An OPTIONAL
model-in-the-loop pass (needs Strands + Bedrock) runs only behind --model.

The checks, in order:
  1. layer served            — the governed layer text has the expected headers
  2. sources load            — every known source reads back non-empty rows
  3. S06 enrichment joins    — a talk enriches correctly across all three keys
  4. S10 flagged TBD/partial — a missing room is flagged, not invented
  5. no structure in prompt  — the system prompt leaks no source/column/join word
  6-9. scoring predicates    — the guardrails reject bad answers, accept good ones
"""
from __future__ import annotations
import re
import sys
import argparse

import semantic
from data_platform import read_source, list_sources
from orchestration import (
    enrich_sessions, cites_sources, flags_partials, invents_nothing,
)
from agent import SYSTEM_PROMPT


# Structural tokens that must NEVER appear in the system prompt: the four source
# ids + the three join-key tokens. Matched as case-insensitive whole words, so
# the legitimate attendee words room/track/speaker and column names like
# room_name/track_name are deliberately NOT flagged.
FORBIDDEN = [
    "sessions", "tracks", "speakers", "rooms",   # source ids
    "track_id", "room_id", "session_id",         # join-key tokens
]


def _by_id() -> dict:
    return {r["session_id"]: r for r in enrich_sessions()}


# --- Check 1: the governed layer is served ----------------------------------

def check_layer_served() -> int:
    served = semantic.read_semantic_layer()
    ok = all(t in served for t in ("Source Catalog", "Join Semantics", "session_id"))
    _report(1, "layer_served", ok, "semantic layer served (catalog + join semantics)")
    return int(ok)


# --- Check 2: every source loads --------------------------------------------

def check_sources_load() -> int:
    ok = True
    for sid in list_sources():
        rows = read_source(sid)
        if isinstance(rows, dict) or not rows:   # error dict or empty
            ok = False
    _report(2, "sources_load", ok, "every known source loads with rows")
    return int(ok)


# --- Check 3: S06 enriches across all three keys ----------------------------

def check_s06_enriches() -> int:
    s06 = _by_id()["S06"]  # Production-Grade Agent Architectures
    ok = (s06["track_name"] == "AI & Agents"
          and s06["room_name"] == "Workshop Room C"
          and "Sam Okoye" in s06["speakers"]
          and s06["partial"] is False)
    _report(3, "s06_enriches", ok, "talk joined across tracks/rooms/speakers")
    return int(ok)


# --- Check 4: S10's missing room is flagged TBD/partial ---------------------

def check_s10_partial() -> int:
    s10 = _by_id()["S10"]  # room_id='Main', absent from rooms.csv
    ok = s10["partial"] is True and "TBD" in s10["room_name"]
    _report(4, "s10_partial", ok, "missing room flagged TBD (partial), not invented")
    return int(ok)


# --- Check 5: the system prompt carries no schedule structure (INV-3) -------

def check_prompt_no_structure() -> int:
    low = SYSTEM_PROMPT.lower()
    leaked = [t for t in FORBIDDEN if re.search(r"\b" + re.escape(t) + r"\b", low)]
    ok = not leaked
    _report(5, "prompt_no_structure", ok,
            "system prompt carries no schedule structure"
            if ok else f"leaked tokens {leaked}")
    return int(ok)


# --- Checks 6-9: the scoring predicates catch bad answers, accept good ------

def check_rejects_uncited() -> int:
    # A fact with no source word at all must be rejected by cites_sources.
    ok = not cites_sources("It starts at 11:00 and ends at 11:45.")
    _report(6, "rejects_uncited", ok, "uncited answer rejected")
    return int(ok)


def check_rejects_hidden_partial() -> int:
    enriched = enrich_sessions()
    s10 = {r["session_id"]: r for r in enriched}["S10"]
    bad = f"The talk '{s10['title']}' (from the sessions source) is in Hall A."
    ok = not flags_partials(bad, enriched)
    _report(7, "rejects_hidden_partial", ok, "answer hiding S10's partial rejected")
    return int(ok)


def check_rejects_invented() -> int:
    enriched = enrich_sessions()
    bad = "The talk is in the Grand Ballroom, with a speaker from the speakers data."
    ok = not invents_nothing(bad, enriched)
    _report(8, "rejects_invented", ok, "invented room rejected")
    return int(ok)


def check_accepts_good() -> int:
    enriched = enrich_sessions()
    by_id = {r["session_id"]: r for r in enriched}
    s06, s10 = by_id["S06"], by_id["S10"]
    good = (
        f"The talk '{s06['title']}' is in {s06['room_name']} with speaker "
        f"{s06['speakers'][0]} (room from the room data, speaker from the speaker "
        f"data). The talk '{s10['title']}' has its room TBD -- it is not listed in "
        f"the room data, so I will not invent one."
    )
    ok = (cites_sources(good)
          and flags_partials(good, enriched)
          and invents_nothing(good, enriched))
    _report(9, "accepts_good", ok, "correct cited + TBD-flagged answer accepted")
    return int(ok)


def _report(num: int, name: str, ok: bool, detail: str) -> None:
    print(f"{'PASS' if ok else 'FAIL'} #{num} {name}: {detail}")


_CHECKS = [
    check_layer_served,
    check_sources_load,
    check_s06_enriches,
    check_s10_partial,
    check_prompt_no_structure,
    check_rejects_uncited,
    check_rejects_hidden_partial,
    check_rejects_invented,
    check_accepts_good,
]


def run_all() -> None:
    """Run every deterministic check and assert a perfect score."""
    results = [check() for check in _CHECKS]
    score, total = sum(results), len(results)
    print(f"\nScore: {score}/{total} checks passed.")
    assert score == total, f"eval regression: {score}/{total}"
    print("All eval checks passed.")


# --- OPTIONAL model-in-the-loop (needs Strands + Bedrock; never required) ---

def run_model_in_the_loop() -> None:
    """Build a LIVE agent, ask the demo question, and score its answer with the
    same guardrail predicates. Only runs behind --model. Any build/runtime
    failure is printed as a skip, never raised, so it cannot break the suite."""
    question = "What AI talks are on Tuesday, who is speaking, and in which room?"
    try:
        from agent import build_agent
        live = build_agent()
    except Exception as e:  # SDK missing / model not configured / auth
        print(f"SKIP model-in-the-loop: agent could not be built ({e})")
        return
    try:
        answer = str(live(question))
    except Exception as e:  # network / throttling / auth at runtime
        print(f"SKIP model-in-the-loop: live call failed ({e})")
        return
    enriched = enrich_sessions()
    scores = {
        "cites_sources": cites_sources(answer),
        "flags_partials": flags_partials(answer, enriched),
        "invents_nothing": invents_nothing(answer, enriched),
    }
    for name, ok in scores.items():
        print(f"{'PASS' if ok else 'FAIL'} model.{name}")
    print(f"\nModel-in-the-loop: {sum(scores.values())}/{len(scores)} predicates passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Conference Concierge eval")
    parser.add_argument("--model", action="store_true",
                        help="also run optional live model scoring (needs Bedrock)")
    args = parser.parse_args()

    run_all()
    if args.model:
        run_model_in_the_loop()
