from __future__ import annotations

import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

import morfeusz2

from pl_bench_core import (
    BenchmarkResult,
    TokenLemma,
    average_runtime,
    build_runner_parser,
    configure_runtime,
    emit_result,
    read_text,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "desc.txt"

# Coarse mapping from the SGJP/NKJP flexemic class (the segment before the first
# colon of a Morfeusz tag) to Universal POS, so Morfeusz can be compared against
# the UD-based taggers. The mapping is approximate by design.
NKJP_TO_UPOS = {
    "subst": "NOUN", "depr": "NOUN", "ger": "NOUN",
    "adj": "ADJ", "adja": "ADJ", "adjp": "ADJ", "adjc": "ADJ",
    "pact": "ADJ", "ppas": "ADJ",
    "adv": "ADV", "pcon": "ADV", "pant": "ADV",
    "num": "NUM", "numcol": "NUM",
    "ppron12": "PRON", "ppron3": "PRON", "siebie": "PRON",
    "fin": "VERB", "bedzie": "VERB", "praet": "VERB", "impt": "VERB",
    "imps": "VERB", "inf": "VERB", "pred": "VERB", "winien": "VERB",
    "aglt": "AUX",
    "prep": "ADP",
    "conj": "CCONJ", "comp": "SCONJ",
    "qub": "PART",
    "interj": "INTJ",
    "interp": "PUNCT",
    "brev": "X", "burk": "X", "xxx": "X", "ign": "X",
}


def _tag_to_upos(tag: str) -> str:
    flexeme = tag.split(":", maxsplit=1)[0]
    return NKJP_TO_UPOS.get(flexeme, "X")


def _collect_tokens(analysis: list[tuple[int, int, Any]]) -> list[TokenLemma]:
    per_token: "OrderedDict[tuple[int, int, str], tuple[list[str], list[str]]]" = (
        OrderedDict()
    )

    for start_node, end_node, interpretation in analysis:
        orth, lemma, tag, *_ = interpretation
        key = (start_node, end_node, orth)
        lemmas, upos_tags = per_token.setdefault(key, ([], []))
        if lemma not in lemmas:
            lemmas.append(lemma)
        upos = _tag_to_upos(tag)
        if upos not in upos_tags:
            upos_tags.append(upos)

    tokens: list[TokenLemma] = []
    for (_, _, orth), (lemmas, upos_tags) in per_token.items():
        tokens.append(
            TokenLemma(
                text=orth,
                lemma=lemmas[0] if lemmas else "",
                lemma_candidates=lemmas,
                upos=upos_tags[0] if upos_tags else "",
                upos_candidates=upos_tags,
            )
        )
    return tokens


def main() -> None:
    parser = build_runner_parser("Run the Morfeusz2 benchmark.", DEFAULT_INPUT)
    args = parser.parse_args()

    configure_runtime()
    text = read_text(args.input)

    try:
        load_started = time.perf_counter()
        analyzer = morfeusz2.Morfeusz()
        load_ms = (time.perf_counter() - load_started) * 1000

        analyzer.analyse("To jest test.")
        analysis, process_ms = average_runtime(lambda: analyzer.analyse(text), args.repeats)
        lemmas = _collect_tokens(analysis)
        result = BenchmarkResult(
            pipeline="morfeusz2",
            available=True,
            version=getattr(morfeusz2, "__version__", None),
            model="Morfeusz()",
            load_ms=load_ms,
            process_ms=process_ms,
            repeats=args.repeats,
            lemmas=lemmas,
            notes=[
                "Morfeusz2 is a non-disambiguating morphological analyzer; it returns "
                "all candidate lemmas/tags. Sentence and NER scores are intentionally N/A.",
            ],
        )
    except Exception as exc:
        result = BenchmarkResult(
            pipeline="morfeusz2",
            available=False,
            version=getattr(morfeusz2, "__version__", None),
            error=str(exc),
        )

    emit_result(result)


if __name__ == "__main__":
    main()
