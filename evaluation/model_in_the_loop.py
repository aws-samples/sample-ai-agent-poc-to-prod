"""OPTIONAL model-in-the-loop scoring (design section 5A).

Behind eval_runner.py --model only. Builds a live agent, asks it the demo
question, and scores its own answer with the SAME orchestration.guardrails
predicates the deterministic path uses. NEVER imported by the deterministic path
(the core eval passes with this module absent and with strands uninstalled).

Requires Strands + configured Bedrock access; a build/runtime failure is
reported, not raised past the runner.
"""
from __future__ import annotations
from pathlib import Path

from semantic import SemanticLayer
from data_platform import build_platform
from orchestration.enrichment import enrich_sessions
from orchestration.guardrails import cites_sources, flags_partials, invents_nothing

_ROOT = Path(__file__).resolve().parent.parent
_SEM_DIR = _ROOT / "semantic"

_QUESTION = "What AI talks are on Tuesday, who is speaking, and in which room?"


def _enriched() -> list[dict]:
    layer = SemanticLayer(_SEM_DIR)
    return enrich_sessions(build_platform(layer.schema(), _ROOT))


def _score_answer(answer: str, enriched: list[dict]) -> dict:
    """Run the deterministic guardrail predicates over a live answer string."""
    return {
        "cites_sources": cites_sources(answer),
        "flags_partials": flags_partials(answer, enriched),
        "invents_nothing": invents_nothing(answer, enriched),
    }


def run_all(question: str = _QUESTION) -> None:
    """Build a live agent, ask the demo question, and score the answer with the
    guardrail predicates. Prints the scored result. Any build/runtime failure is
    printed as a skipped model check rather than crashing the runner."""
    try:
        from concierge.agent import build_agent
        agent = build_agent()
    except Exception as e:  # SDK missing / model not configured / auth
        print(f"SKIP model-in-the-loop: agent could not be built ({e})")
        return

    try:
        answer = str(agent(question))
    except Exception as e:  # network / throttling / auth at runtime
        print(f"SKIP model-in-the-loop: live call failed ({e})")
        return

    enriched = _enriched()
    scores = _score_answer(answer, enriched)
    for name, ok in scores.items():
        print(f"{'PASS' if ok else 'FAIL'} model.{name}")
    passed = sum(1 for ok in scores.values() if ok)
    print(f"\nModel-in-the-loop: {passed}/{len(scores)} guardrail predicates passed.")


if __name__ == "__main__":
    run_all()
