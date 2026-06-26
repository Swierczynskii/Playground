from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import stanza
from stanza.pipeline.core import DownloadMethod

from pl_bench_core import (
    BenchmarkResult,
    EntitySpan,
    SentenceSpan,
    TokenLemma,
    average_runtime,
    build_runner_parser,
    configure_runtime,
    emit_result,
    read_text,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_RESOURCES_DIR = PROJECT_ROOT / "models" / "stanza"
DEFAULT_INPUT = PROJECT_ROOT / "data" / "desc.txt"


def _resolve_resources_dir() -> str:
    candidates = []
    env_dir = os.environ.get("STANZA_RESOURCES_DIR")
    if env_dir:
        candidates.append(Path(env_dir).expanduser())
    candidates.append(LOCAL_RESOURCES_DIR)
    candidates.append(Path.cwd() / "stanza_resources")
    candidates.append(Path("~/stanza_resources").expanduser())

    for candidate in candidates:
        if (candidate / "resources.json").exists() and (candidate / "pl").is_dir():
            return str(candidate.resolve())

    raise RuntimeError(
        f"Could not find Stanza resources. Set STANZA_RESOURCES_DIR or run setup.sh "
        f"to populate {LOCAL_RESOURCES_DIR}."
    )


def _build_pipeline() -> tuple[stanza.Pipeline, str]:
    resources_dir = _resolve_resources_dir()
    pipeline = stanza.Pipeline(
        lang="pl",
        processors="tokenize,pos,lemma,ner",
        use_gpu=False,
        dir=resources_dir,
        verbose=False,
        download_method=DownloadMethod.REUSE_RESOURCES,
    )
    return pipeline, resources_dir


def _extract(doc: Any) -> tuple[list[SentenceSpan], list[TokenLemma], list[EntitySpan]]:
    sentences: list[SentenceSpan] = []
    lemmas: list[TokenLemma] = []
    entities: list[EntitySpan] = []

    for sentence in doc.sentences:
        words = list(sentence.words)
        if words:
            start = words[0].start_char or 0
            end = words[-1].end_char or start
            text = sentence.text.strip() if getattr(sentence, "text", None) else ""
            if not text:
                text = " ".join(word.text for word in words).strip()
            sentences.append(SentenceSpan(start=start, end=end, text=text))

        for word in words:
            upos = word.upos or ""
            lemmas.append(
                TokenLemma(
                    text=word.text,
                    lemma=word.lemma or "",
                    lemma_candidates=[word.lemma or ""],
                    upos=upos,
                    upos_candidates=[upos],
                )
            )

        for entity in getattr(sentence, "ents", []):
            entities.append(
                EntitySpan(
                    start=entity.start_char,
                    end=entity.end_char,
                    label=entity.type,
                    text=entity.text,
                )
            )

    return sentences, lemmas, entities


def main() -> None:
    parser = build_runner_parser("Run the Stanza Polish benchmark.", DEFAULT_INPUT)
    args = parser.parse_args()

    configure_runtime()
    text = read_text(args.input)

    try:
        load_started = time.perf_counter()
        pipeline, resources_dir = _build_pipeline()
        load_ms = (time.perf_counter() - load_started) * 1000

        pipeline("To jest test.")
        doc, process_ms = average_runtime(lambda: pipeline(text), args.repeats)
        sentences, lemmas, entities = _extract(doc)
        result = BenchmarkResult(
            pipeline="stanza",
            available=True,
            version=stanza.__version__,
            model="tokenize,pos,lemma,ner",
            load_ms=load_ms,
            process_ms=process_ms,
            repeats=args.repeats,
            sentences=sentences,
            lemmas=lemmas,
            entities=entities,
            notes=[f"resources_dir={resources_dir}"],
        )
    except Exception as exc:
        result = BenchmarkResult(
            pipeline="stanza",
            available=False,
            version=getattr(stanza, "__version__", None),
            error=str(exc),
        )

    emit_result(result)


if __name__ == "__main__":
    main()
