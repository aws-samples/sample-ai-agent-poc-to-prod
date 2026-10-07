"""Deterministic quality/hallucination scoring (design sections 5A/6/3.1).

Five checks (#5-#9). Check #5 is the prompt-structure guard (INV-3). Checks
#6-#9 run the orchestration.guardrails predicates over enrich_sessions output +
fixed synthetic candidate answers, each returning 0/1. No model, no network: the
candidate answers are hard-coded fixtures, not model output.
"""
from __future__ import annotations
import re
from pathlib import Path

from semantic import SemanticLayer
from data_platform import build_platform
from orchestration.enrichment import enrich_sessions
from orchestration.guardrails import cites_sources, flags_partials, invents_nothing

_ROOT = Path(__file__).resolve().parent.parent
_SEM_DIR = _ROOT / "semantic"

# Structural tokens that must never appear in the system prompt (design section
# 3.1): the four catalog source ids + the three join-key tokens. Matched
# case-insensitively as \b-bounded whole words over the lowercased prompt, so the
# legitimate attendee words room/track/speaker and generic column names
# (room_name, track_name) are deliberately NOT scanned.
FORBIDDEN = [
    "sessions", "tracks", "speakers", "rooms",   # catalog source ids
    "track_id", "room_id", "session_id",         # join-key tokens
]


def _enriched() -> list[dict]:
    layer = SemanticLayer(_SEM_DIR)
    platform = build_platform(layer.schema(), _ROOT)
    return enrich_sessions(platform)


def _by_id(enriched: list[dict]) -> dict:
    return {r["session_id"]: r for r in enriched}


def test_prompt_carries_no_structure() -> int:
    """#5 The system prompt names no source id / column name / join key — a
    \\b-bounded, case-insensitive whole-word scan over the lowercased prompt finds
    none of FORBIDDEN (INV-3). Returns 1 on pass, 0 on fail."""
    from concierge.agent import SYSTEM_PROMPT
    low = SYSTEM_PROMPT.lower()
    leaked = [t for t in FORBIDDEN if re.search(r"\b" + re.escape(t) + r"\b", low)]
    ok = not leaked
    if ok:
        print("PASS #5 test_prompt_carries_no_structure: system prompt carries no schedule structure")
    else:
        print(f"FAIL #5 test_prompt_carries_no_structure: leaked tokens {leaked}")
    return int(ok)


def test_scoring_rejects_missing_citation() -> int:
    """#6 An answer that reports a fact without citing any source scores fail
    (cites_sources is False). Returns 1 when the predicate correctly rejects it."""
    # No enrichment needed: this check is purely on the candidate answer string.
    # Reports a fact with no source word (track/room/speaker/session/talk) at
    # all, so the citation predicate must reject it.
    bad_answer = "It starts at 11:00 and ends at 11:45."
    rejected = not cites_sources(bad_answer)
    _report(6, "test_scoring_rejects_missing_citation",
            rejected, "uncited answer rejected")
    return int(rejected)


def test_scoring_rejects_hidden_partial() -> int:
    """#7 An answer that states S10's room without flagging it TBD scores fail
    (flags_partials is False). Returns 1 when the predicate correctly rejects it."""
    enriched = _enriched()
    s10 = _by_id(enriched)["S10"]
    # Mentions S10's title and asserts a concrete room, hiding the partial.
    bad_answer = (
        f"The talk '{s10['title']}' (from the sessions source) is in Hall A."
    )
    rejected = not flags_partials(bad_answer, enriched)
    _report(7, "test_scoring_rejects_hidden_partial",
            rejected, "answer hiding S10's partial rejected")
    return int(rejected)


def test_scoring_rejects_invented_value() -> int:
    """#8 An answer naming a room/track/speaker absent from the data scores fail
    (invents_nothing is False). Returns 1 when the predicate correctly rejects
    it. Uses the hallucination sentinels from orchestration.guardrails."""
    enriched = _enriched()
    # Names a room that does not exist in the data (a hallucination sentinel).
    bad_answer = (
        "The talk is in the Grand Ballroom, with a speaker from the speakers data."
    )
    rejected = not invents_nothing(bad_answer, enriched)
    _report(8, "test_scoring_rejects_invented_value",
            rejected, "invented room rejected")
    return int(rejected)


def test_scoring_passes_good_answer() -> int:
    """#9 A correct answer that cites its sources, flags S10's partial as TBD, and
    invents nothing scores pass (all three predicates True). Returns 1 on pass."""
    enriched = _enriched()
    by_id = _by_id(enriched)
    s06 = by_id["S06"]
    s10 = by_id["S10"]
    good_answer = (
        f"The talk '{s06['title']}' is in {s06['room_name']} with speaker "
        f"{s06['speakers'][0]} (room from the room data, speaker from the speaker "
        f"data). The talk '{s10['title']}' has its room TBD -- it is not listed in "
        f"the room data, so I will not invent one."
    )
    passed = (
        cites_sources(good_answer)
        and flags_partials(good_answer, enriched)
        and invents_nothing(good_answer, enriched)
    )
    _report(9, "test_scoring_passes_good_answer",
            passed, "correct cited + TBD-flagged answer accepted")
    return int(passed)


def _report(num: int, name: str, ok: bool, detail: str) -> None:
    status = "PASS" if ok else "FAIL"
    print(f"{status} #{num} {name}: {detail}")


def run_all() -> None:
    """Run the five scoring checks (#5-#9) and print a total score. Asserts a
    perfect score so the deterministic eval fails loudly on any regression."""
    results = [
        test_prompt_carries_no_structure(),
        test_scoring_rejects_missing_citation(),
        test_scoring_rejects_hidden_partial(),
        test_scoring_rejects_invented_value(),
        test_scoring_passes_good_answer(),
    ]
    score = sum(results)
    total = len(results)
    print(f"\nScoring: {score}/{total} checks passed.")
    assert score == total, f"scoring regression: {score}/{total}"


if __name__ == "__main__":
    run_all()
