from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SentenceSpan:
    start: int
    end: int
    text: str


@dataclass
class TokenLemma:
    text: str
    lemma: str
    lemma_candidates: list[str] = field(default_factory=list)
    upos: str = ""
    upos_candidates: list[str] = field(default_factory=list)


@dataclass
class EntitySpan:
    start: int
    end: int
    label: str
    text: str


@dataclass
class BenchmarkResult:
    pipeline: str
    available: bool
    version: str | None = None
    model: str | None = None
    error: str | None = None
    load_ms: float | None = None
    process_ms: float | None = None
    repeats: int = 0
    sentences: list[SentenceSpan] = field(default_factory=list)
    lemmas: list[TokenLemma] = field(default_factory=list)
    entities: list[EntitySpan] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkResult":
        return cls(
            pipeline=data["pipeline"],
            available=data["available"],
            version=data.get("version"),
            model=data.get("model"),
            error=data.get("error"),
            load_ms=data.get("load_ms"),
            process_ms=data.get("process_ms"),
            repeats=data.get("repeats", 0),
            sentences=[SentenceSpan(**item) for item in data.get("sentences", [])],
            lemmas=[TokenLemma(**item) for item in data.get("lemmas", [])],
            entities=[EntitySpan(**item) for item in data.get("entities", [])],
            notes=list(data.get("notes", [])),
        )


def configure_runtime() -> None:
    os.environ.setdefault("OMP_NUM_THREADS", "8")
    os.environ.setdefault("MKL_NUM_THREADS", "8")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    try:
        import torch
    except Exception:
        return

    try:
        torch.set_num_threads(1)
        if hasattr(torch, "set_num_interop_threads"):
            torch.set_num_interop_threads(1)
    except Exception:
        pass


def build_runner_parser(
    description: str, default_input: Path | None = None
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input,
        required=default_input is None,
        help="Path to the input text file.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Number of timed processing runs after warm-up.",
    )
    return parser


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def average_runtime(callback: Any, repeats: int) -> tuple[Any, float]:
    started = time.perf_counter()
    last_value = None
    for _ in range(repeats):
        last_value = callback()
    elapsed_ms = (time.perf_counter() - started) * 1000
    return last_value, elapsed_ms / repeats


def emit_result(result: BenchmarkResult) -> None:
    print(json.dumps(result.to_dict(), ensure_ascii=False))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
