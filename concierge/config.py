"""Settings: model id, region, and cost rates read from .env (swappable).

Provider-agnostic (NFR-3): to swap providers, change BEDROCK_MODEL_ID/region, or
substitute a different Strands model class in agent.py — a config change, not a
refactor. The .env is read by a minimal stdlib parser (no python-dotenv dep).
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path


def _load_env(path: Path) -> None:
    """Minimal .env loader (no dependency). KEY=VALUE lines; '#' comments."""
    if not path.exists(): return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


@dataclass(frozen=True)
class Settings:
    model_id: str
    region: str
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0

    @classmethod
    def from_env(cls, env_path: Path | None = None) -> "Settings":
        _load_env(env_path or Path(__file__).parent.parent / ".env")
        return cls(
            # Default id is a placeholder — VERIFY against the current Bedrock catalog
            # and the team's enabled account/region at build time (see design §7.1).
            model_id=os.environ.get("BEDROCK_MODEL_ID",
                                    "us.anthropic.claude-3-5-haiku-20241022-v1:0"),
            region=os.environ.get("AWS_REGION", "us-east-1"),
            input_cost_per_1k=float(os.environ.get("INPUT_COST_PER_1K", "0") or 0),
            output_cost_per_1k=float(os.environ.get("OUTPUT_COST_PER_1K", "0") or 0),
        )
