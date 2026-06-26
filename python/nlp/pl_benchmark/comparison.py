from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pl_bench_core.core import (
    BenchmarkResult,
    configure_runtime,
    read_text,
    write_json,
)
from pl_bench_core.gold import GoldReference, LemmaProbe, build_gold_reference

PROJECT_ROOT = Path(__file__).resolve().parent
PIPELINES_ROOT = PROJECT_ROOT / "pipelines"
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "desc.txt"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"


@dataclass(frozen=True)
class PipelineConfig:
    name: str
    directory: str
    python_env_var: str
    # Dedicated venv (relative to PROJECT_ROOT) used when the env var is unset.
    # None means run in the main .venv alongside the orchestrator.
    runner_venv: str | None = None


PIPELINES = [
    PipelineConfig("spacy", "spacy", "SPACY_RUNNER_PYTHON"),
    PipelineConfig("stanza", "stanza", "STANZA_RUNNER_PYTHON"),
    PipelineConfig("morfeusz2", "morfeusz2", "MORFEUSZ2_RUNNER_PYTHON"),
    PipelineConfig(
        "spacy-pl",
        "spacy_pl",
        "SPACY_PL_RUNNER_PYTHON",
        runner_venv="pipelines/spacy_pl/.venv",
    ),
    PipelineConfig(
        "spacy-pl-trf",
        "spacy_pl_trf",
        "SPACY_PL_TRF_RUNNER_PYTHON",
        runner_venv="pipelines/spacy_pl_trf/.venv",
    ),
]


def _main_runner_python() -> str:
    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _runner_python(config: PipelineConfig) -> str:
    override = os.environ.get(config.python_env_var)
    if override:
        return override
    if config.runner_venv:
        dedicated = PROJECT_ROOT / config.runner_venv / "bin" / "python"
        if dedicated.exists():
            return str(dedicated)
    return _main_runner_python()


def _normalize_space(text: str) -> str:
    return " ".join(text.split())


def _sentence_boundaries(sentences: list[Any]) -> set[int]:
    if not sentences:
        return set()
    return {sentence.end for sentence in sentences[:-1]}


def _safe_rate(value: int, total: int) -> float | None:
    if total == 0:
        return None
    return value / total


def _f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None or precision + recall == 0:
        return None
    return 2 * precision * recall / (precision + recall)


def _normalize_entity_label(label: str) -> str:
    lowered = label.lower()
    if "pers" in lowered or "person" in lowered:
        return "PERSON"
    if "org" in lowered:
        return "ORG"
    if "place" in lowered or "loc" in lowered or "gpe" in lowered:
        return "LOC"
    if "date" in lowered:
        return "DATE"
    if "money" in lowered or "currency" in lowered:
        return "MONEY"
    return label.upper()


def _normalize_lemma(lemma: str) -> str:
    return lemma.split(":", maxsplit=1)[0].split("~", maxsplit=1)[0]


def _score_sentences(result: BenchmarkResult, gold: GoldReference) -> dict[str, Any]:
    if not result.sentences:
        return {
            "available": False,
            "precision": None,
            "recall": None,
            "f1": None,
            "predicted_count": 0,
            "gold_count": len(gold.sentences),
        }

    predicted = _sentence_boundaries(result.sentences)
    expected = _sentence_boundaries(gold.sentences)
    matches = len(predicted & expected)
    precision = _safe_rate(matches, len(predicted))
    recall = _safe_rate(matches, len(expected))
    return {
        "available": True,
        "precision": precision,
        "recall": recall,
        "f1": _f1(precision, recall),
        "predicted_count": len(result.sentences),
        "gold_count": len(gold.sentences),
        "exact_text_match": [
            _normalize_space(sentence.text) for sentence in result.sentences
        ]
        == [_normalize_space(sentence.text) for sentence in gold.sentences],
    }


def _lookup_probe(tokens: list[Any], probe: LemmaProbe) -> Any | None:
    seen = 0
    for token in tokens:
        if token.text == probe.text:
            seen += 1
            if seen == probe.occurrence:
                return token
    return None


def _score_lemmas(result: BenchmarkResult, gold: GoldReference) -> dict[str, Any]:
    if not result.lemmas:
        return {
            "available": False,
            "top1_accuracy": None,
            "candidate_accuracy": None,
            "matched_probes": 0,
            "probe_count": len(gold.lemma_probes),
            "missing_probes": [probe.text for probe in gold.lemma_probes],
        }

    top1_hits = 0
    candidate_hits = 0
    matched = 0
    missing: list[str] = []

    for probe in gold.lemma_probes:
        token = _lookup_probe(result.lemmas, probe)
        if token is None:
            missing.append(probe.text)
            continue
        matched += 1
        expected = _normalize_lemma(probe.expected_lemma)
        if _normalize_lemma(token.lemma) == expected:
            top1_hits += 1
        candidates = token.lemma_candidates or [token.lemma]
        normalized_candidates = {_normalize_lemma(candidate) for candidate in candidates}
        if expected in normalized_candidates:
            candidate_hits += 1

    return {
        "available": True,
        "top1_accuracy": _safe_rate(top1_hits, matched),
        "candidate_accuracy": _safe_rate(candidate_hits, matched),
        "matched_probes": matched,
        "probe_count": len(gold.lemma_probes),
        "missing_probes": missing,
    }


def _score_pos(result: BenchmarkResult, gold: GoldReference) -> dict[str, Any]:
    probes = [probe for probe in gold.lemma_probes if probe.expected_upos]
    has_pos = any(token.upos for token in result.lemmas)
    if not result.lemmas or not has_pos or not probes:
        return {
            "available": False,
            "top1_accuracy": None,
            "candidate_accuracy": None,
            "matched_probes": 0,
            "probe_count": len(probes),
        }

    top1_hits = 0
    candidate_hits = 0
    matched = 0

    for probe in probes:
        token = _lookup_probe(result.lemmas, probe)
        if token is None:
            continue
        matched += 1
        if token.upos == probe.expected_upos:
            top1_hits += 1
        candidates = token.upos_candidates or [token.upos]
        if probe.expected_upos in set(candidates):
            candidate_hits += 1

    return {
        "available": True,
        "top1_accuracy": _safe_rate(top1_hits, matched),
        "candidate_accuracy": _safe_rate(candidate_hits, matched),
        "matched_probes": matched,
        "probe_count": len(probes),
    }


def _score_entities(result: BenchmarkResult, gold: GoldReference) -> dict[str, Any]:
    if not result.entities:
        return {
            "available": False,
            "precision": None,
            "recall": None,
            "f1": None,
            "predicted_count": 0,
            "gold_count": len(gold.entities),
        }

    predicted = {
        (entity.start, entity.end, _normalize_entity_label(entity.label))
        for entity in result.entities
    }
    expected = {
        (entity.start, entity.end, _normalize_entity_label(entity.label))
        for entity in gold.entities
    }
    matches = len(predicted & expected)
    precision = _safe_rate(matches, len(predicted))
    recall = _safe_rate(matches, len(expected))
    return {
        "available": True,
        "precision": precision,
        "recall": recall,
        "f1": _f1(precision, recall),
        "predicted_count": len(predicted),
        "gold_count": len(expected),
    }


def _format_metric(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.3f}"


def _run_pipeline(config: PipelineConfig, input_path: Path, repeats: int) -> BenchmarkResult:
    python_executable = _runner_python(config)
    runner_path = PIPELINES_ROOT / config.directory / "runner.py"
    command = [
        python_executable,
        str(runner_path),
        "--input",
        str(input_path),
        "--repeats",
        str(repeats),
    ]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        error = completed.stderr.strip() or completed.stdout.strip() or "Unknown runner failure"
        return BenchmarkResult(
            pipeline=config.name,
            available=False,
            error=error,
            notes=[f"runner={python_executable}"],
        )

    try:
        payload = json.loads(completed.stdout)
        result = BenchmarkResult.from_dict(payload)
    except json.JSONDecodeError as exc:
        return BenchmarkResult(
            pipeline=config.name,
            available=False,
            error=f"Runner returned invalid JSON: {exc}",
            notes=[completed.stdout.strip(), completed.stderr.strip()],
        )

    result.notes.append(f"runner={python_executable}")
    return result


def _summarize(result: BenchmarkResult, gold: GoldReference, text: str) -> dict[str, Any]:
    chars_per_second = None
    if result.process_ms:
        chars_per_second = len(text) / (result.process_ms / 1000)

    return {
        "pipeline": result.pipeline,
        "available": result.available,
        "version": result.version,
        "model": result.model,
        "error": result.error,
        "load_ms": result.load_ms,
        "process_ms": result.process_ms,
        "chars_per_second": chars_per_second,
        "sentence_metrics": _score_sentences(result, gold),
        "lemma_metrics": _score_lemmas(result, gold),
        "pos_metrics": _score_pos(result, gold),
        "entity_metrics": _score_entities(result, gold),
        "notes": result.notes,
    }


def _build_markdown(summary: list[dict[str, Any]]) -> str:
    lines = [
        "# Polish NLP Comparison",
        "",
        "| Pipeline | Status | Load ms | Process ms | Chars/s | Sentence F1 | "
        "Lemma top1 | Lemma any | POS top1 | POS any | NER F1 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for item in summary:
        status = "ok" if item["available"] else "unavailable"
        load_ms = "N/A" if item["load_ms"] is None else f"{item['load_ms']:.1f}"
        process_ms = "N/A" if item["process_ms"] is None else f"{item['process_ms']:.1f}"
        chars_per_second = (
            "N/A"
            if item["chars_per_second"] is None
            else f"{item['chars_per_second']:.1f}"
        )
        sentence_f1 = _format_metric(item["sentence_metrics"]["f1"])
        lemma_top1 = _format_metric(item["lemma_metrics"]["top1_accuracy"])
        lemma_any = _format_metric(item["lemma_metrics"]["candidate_accuracy"])
        pos_top1 = _format_metric(item["pos_metrics"]["top1_accuracy"])
        pos_any = _format_metric(item["pos_metrics"]["candidate_accuracy"])
        entity_f1 = _format_metric(item["entity_metrics"]["f1"])
        lines.append(
            f"| {item['pipeline']} | {status} | {load_ms} | {process_ms} | "
            f"{chars_per_second} | {sentence_f1} | {lemma_top1} | {lemma_any} | "
            f"{pos_top1} | {pos_any} | {entity_f1} |"
        )

    for item in summary:
        lines.extend(
            [
                "",
                f"## {item['pipeline']}",
                "",
                f"- Available: `{item['available']}`",
                f"- Version: `{item['version']}`",
                f"- Model: `{item['model']}`",
                f"- Error: `{item['error']}`",
                f"- Notes: `{'; '.join(note for note in item['notes'] if note)}`",
            ]
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    configure_runtime()
    input_path = DEFAULT_INPUT_PATH
    repeats = 3
    reports_dir = DEFAULT_REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)

    text = read_text(input_path)
    gold = build_gold_reference(text)
    summary: list[dict[str, Any]] = []

    for config in PIPELINES:
        result = _run_pipeline(config, input_path, repeats)
        write_json(reports_dir / f"{config.name}.json", result.to_dict())
        summary.append(_summarize(result, gold, text))

    write_json(reports_dir / "summary.json", {"pipelines": summary})
    (reports_dir / "summary.md").write_text(_build_markdown(summary), encoding="utf-8")

    print("Pipeline comparison complete.")
    for item in summary:
        status = "ok" if item["available"] else "unavailable"
        print(
            f"{item['pipeline']}: {status}, process_ms={item['process_ms']}, "
            f"sentence_f1={_format_metric(item['sentence_metrics']['f1'])}, "
            f"lemma_top1={_format_metric(item['lemma_metrics']['top1_accuracy'])}, "
            f"pos_top1={_format_metric(item['pos_metrics']['top1_accuracy'])}, "
            f"ner_f1={_format_metric(item['entity_metrics']['f1'])}"
        )
    print(f"Detailed results written to {reports_dir}")


if __name__ == "__main__":
    main()
