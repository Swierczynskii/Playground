from __future__ import annotations

import collections
import os
import time
from pathlib import Path

import spacy

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
DEFAULT_INPUT = PROJECT_ROOT / "data" / "desc.txt"


def _load_model() -> tuple[object, str]:
    requested = os.environ.get("SPACY_PL_MODEL")
    candidates = [requested] if requested else ["pl_spacy_model_morfeusz", "pl_spacy_model"]
    last_error: Exception | None = None

    for candidate in candidates:
        if not candidate:
            continue
        resolved = Path(candidate).expanduser()
        target = str(resolved) if resolved.exists() else candidate
        try:
            return spacy.load(target), candidate
        except Exception as exc:
            last_error = exc

    raise RuntimeError(
        "Could not load spaCy-PL. Set SPACY_PL_MODEL to the installed package "
        "name or to an extracted model directory."
    ) from last_error


def _harden_tag_map(nlp: object) -> None:
    """Make the model's NKJP->UD tag map tolerant of unknown tags.

    The pinned Morfeusz2 dictionary emits flexemic classes (e.g. ``sym``) that the
    2020-era model's ``tag_map`` predates, which otherwise raises ``KeyError`` mid
    document. Fall back to UD ``X`` for any unknown tag.
    """
    tokenizer = getattr(nlp, "tokenizer", None)
    tag_map = getattr(tokenizer, "tag_map", None)
    if isinstance(tag_map, dict) and not isinstance(tag_map, collections.defaultdict):
        tokenizer.tag_map = collections.defaultdict(lambda: "X", tag_map)


def _extract(doc: object) -> tuple[list[SentenceSpan], list[TokenLemma], list[EntitySpan]]:
    sentences = [
        SentenceSpan(start=sent.start_char, end=sent.end_char, text=sent.text.strip())
        for sent in doc.sents
    ]
    lemmas = [
        TokenLemma(
            text=token.text,
            lemma=token.lemma_,
            lemma_candidates=[token.lemma_],
            upos=token.pos_,
            upos_candidates=[token.pos_],
        )
        for token in doc
        if token.text.strip()
    ]
    entities = [
        EntitySpan(start=ent.start_char, end=ent.end_char, label=ent.label_, text=ent.text)
        for ent in doc.ents
    ]
    return sentences, lemmas, entities


def main() -> None:
    parser = build_runner_parser("Run the legacy spaCy-PL benchmark.", DEFAULT_INPUT)
    args = parser.parse_args()

    configure_runtime()
    text = read_text(args.input)

    try:
        load_started = time.perf_counter()
        nlp, model_name = _load_model()
        _harden_tag_map(nlp)
        load_ms = (time.perf_counter() - load_started) * 1000

        nlp("To jest test.")
        doc, process_ms = average_runtime(lambda: nlp(text), args.repeats)
        sentences, lemmas, entities = _extract(doc)
        result = BenchmarkResult(
            pipeline="spacy-pl",
            available=True,
            version=spacy.__version__,
            model=model_name,
            load_ms=load_ms,
            process_ms=process_ms,
            repeats=args.repeats,
            sentences=sentences,
            lemmas=lemmas,
            entities=entities,
            notes=["pl_spacy_model_morfeusz on spaCy 2.2.4 (dedicated .venv)."],
        )
    except Exception as exc:
        result = BenchmarkResult(
            pipeline="spacy-pl",
            available=False,
            version=getattr(spacy, "__version__", None),
            error=str(exc),
            notes=["Rebuild this pipeline's venv with REBUILD_LEGACY=1 ./setup.sh."],
        )

    emit_result(result)


if __name__ == "__main__":
    main()
