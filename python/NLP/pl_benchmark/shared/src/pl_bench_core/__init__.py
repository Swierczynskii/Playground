"""Shared, dependency-free benchmark primitives used by every pipeline runner
and the orchestrator. Installed (as a path dependency) into each pipeline venv so
the data model and helpers stay identical across interpreters."""

from .core import (
    BenchmarkResult,
    EntitySpan,
    SentenceSpan,
    TokenLemma,
    average_runtime,
    build_runner_parser,
    configure_runtime,
    emit_result,
    read_text,
    write_json,
)

__all__ = [
    "BenchmarkResult",
    "EntitySpan",
    "SentenceSpan",
    "TokenLemma",
    "average_runtime",
    "build_runner_parser",
    "configure_runtime",
    "emit_result",
    "read_text",
    "write_json",
]
