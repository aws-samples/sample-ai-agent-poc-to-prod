from __future__ import annotations
import json, logging, os, time
from contextlib import contextmanager

_log = logging.getLogger("concierge.obs")
_ENABLED = os.environ.get("OBSERVABILITY", "0") not in ("", "0", "false", "False")
_SPAN_COUNT = {"n": 0}            # per-process count of emitted tool.* spans (step_count)

def is_enabled() -> bool:
    return _ENABLED

def set_enabled(flag: bool) -> None:
    """Toggle at runtime (CLI --observe turns it on; the deterministic eval leaves it off)."""
    global _ENABLED
    _ENABLED = bool(flag)

def span_count() -> int:
    return _SPAN_COUNT["n"]

@contextmanager
def span(name: str, **fields):
    """Timed span. When enabled, record duration_ms + fields and emit one JSON line;
    when disabled, yield immediately (true no-op — no logging, no timing cost)."""
    if not _ENABLED:
        yield
        return
    start = time.perf_counter()
    try:
        yield
    finally:
        dur_ms = round((time.perf_counter() - start) * 1000, 2)
        if name.startswith("tool."):
            _SPAN_COUNT["n"] += 1
        _log.info(json.dumps({"event": name, "duration_ms": dur_ms, **fields}))

def configure_logging() -> None:
    """One-line JSON logging to stderr; called by the CLI/service, never by the eval."""
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
