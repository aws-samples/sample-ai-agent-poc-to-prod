"""Stdlib leaf: a span/timing context manager and an enable flag, no-op when disabled. Lowest layer; orchestration and concierge may depend on it. Knows nothing about conferences, models, or the agent."""
from .tracing import span, is_enabled, set_enabled, span_count, configure_logging

__all__ = ["span", "is_enabled", "set_enabled", "span_count", "configure_logging"]
