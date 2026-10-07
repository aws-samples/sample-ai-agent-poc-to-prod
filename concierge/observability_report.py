"""Run-level observability report: token/cost accounting + drift record.

Lives at the application layer because it reads the agent result + Settings
(design section 7B). It composes the stdlib span leaf (step_count via
span_count()) with model/cost context. It never wires a model call into a
deterministic path — token_usage is read from a result object the caller already
has, or is None.
"""
from __future__ import annotations
from dataclasses import dataclass
from observability import span_count
from .config import Settings


@dataclass(frozen=True)
class RunReport:
    """One run's observability summary. {layer_version, quality_score} is the
    drift record compared across runs; estimated_cost_usd is derived from
    token_usage and the Settings per-1k rates (0.0 when rates/usage are absent)."""
    tool_calls: list[str]
    step_count: int
    token_usage: dict | None
    layer_version: str
    quality_score: float | None
    estimated_cost_usd: float


def _extract_token_usage(result) -> dict | None:
    """Pull {input_tokens, output_tokens, total_tokens} from a Strands agent
    result's usage metadata when present, else None. Tolerant of the metadata
    being absent or shaped differently across SDK versions."""
    if result is None:
        return None
    metrics = getattr(result, "metrics", None)
    usage = getattr(metrics, "accumulated_usage", None) if metrics is not None else None
    if usage is None:
        usage = getattr(result, "usage", None)
    if usage is None:
        return None
    get = usage.get if isinstance(usage, dict) else lambda k, d=None: getattr(usage, k, d)
    inp = get("inputTokens", get("input_tokens", 0)) or 0
    out = get("outputTokens", get("output_tokens", 0)) or 0
    total = get("totalTokens", get("total_tokens", inp + out)) or (inp + out)
    return {"input_tokens": int(inp), "output_tokens": int(out), "total_tokens": int(total)}


def _estimate_cost(token_usage: dict | None, settings: Settings) -> float:
    """Estimated USD cost from token usage and the per-1k rates (0.0 if either
    is absent/zero)."""
    if not token_usage:
        return 0.0
    inp = token_usage.get("input_tokens", 0) / 1000.0
    out = token_usage.get("output_tokens", 0) / 1000.0
    return round(inp * settings.input_cost_per_1k + out * settings.output_cost_per_1k, 6)


def build_report(settings: Settings, layer_version: str, *, tool_calls: list[str] | None = None,
                 result=None, quality_score: float | None = None) -> RunReport:
    """Assemble the run-level report. step_count is the number of tool.* spans
    emitted this process (observability.span_count()); token_usage/cost come from
    the agent result when present (None/0.0 otherwise, so the deterministic eval
    never needs a model)."""
    token_usage = _extract_token_usage(result)
    return RunReport(
        tool_calls=list(tool_calls or []),
        step_count=span_count(),
        token_usage=token_usage,
        layer_version=layer_version,
        quality_score=quality_score,
        estimated_cost_usd=_estimate_cost(token_usage, settings),
    )
