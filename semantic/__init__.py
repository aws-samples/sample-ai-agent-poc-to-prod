"""Governed, versioned semantic layer: catalog + field map + join rules + guardrail contract, assembled and served at runtime. Holds description, not data or logic."""
from .layer import SemanticLayer

__all__ = ["SemanticLayer"]
