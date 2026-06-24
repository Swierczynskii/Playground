# Polish NLP Comparison

Benchmarks five Polish NLP pipelines on a single annotated document, scoring
sentence segmentation, lemmatisation, POS tagging, and named-entity recognition
against a built-in gold reference (`shared/src/pl_bench_core/gold.py`) and
measuring load/processing time.

## Layout

```
pl_benchmark/
  comparison.py            orchestrator + entry point (runs every pipeline, scores, writes reports)
  pyproject.toml           main venv: orchestrator + modern pipelines
  shared/                  pl_bench_core: dependency-free data model + helpers + gold
  pipelines/
    spacy/        runner.py            ─┐
    stanza/       runner.py             ├─ run in the main .venv
    morfeusz2/    runner.py            ─┘
    spacy_pl/     runner.py + pyproject.toml   → own venv (spaCy 2.2.4, py3.8)
    spacy_pl_trf/ runner.py + pyproject.toml   → own venv (spaCy 3.3, py3.10)
  models/                  locally downloaded core models (gitignored)
  data/desc.txt            input document
  reports/                 generated results
```

Each runner is a standalone script that imports the shared `pl_bench_core`
library (installed as a path dependency into every venv) and emits a JSON
`BenchmarkResult`. The orchestrator launches each runner with the right
interpreter — auto-detected by directory — collects the JSON, and scores it.

## Pipelines

| Pipeline       | venv                          | Capabilities                              |
| -------------- | ----------------------------- | ----------------------------------------- |
| `spacy`        | main                          | sentences, lemma, POS, NER                |
| `stanza`       | main                          | sentences, lemma, POS, NER                |
| `morfeusz2`    | main                          | lemma + POS candidates (non-disambiguating analyzer; no sentences/NER) |
| `spacy-pl`     | `pipelines/spacy_pl/.venv`    | sentences, lemma, POS, NER (legacy ipipan, spaCy 2.3.2 + TF/Keras tagger, py3.8) |
| `spacy-pl-trf` | `pipelines/spacy_pl_trf/.venv`| sentences, lemma, POS, NER (ipipan pl_nask HerBERT, spaCy 3.5, py3.10) |

Morfeusz2 is a morphological *analyzer*, not a tagger: it returns every candidate
lemma/tag for each segment rather than one disambiguated reading, and offers no
sentence splitting or NER. The POS column normalises each pipeline to Universal
POS so the SGJP/NKJP tagset (Morfeusz) is comparable to the UD tagsets (the
others); that mapping is approximate.

## Setup

```bash
./setup.sh
```

Creates the three venvs (Python 3.12/3.10/3.8 via `uv`), installs each
pipeline's dependencies, and downloads all models locally:

- `models/spacy/pl_core_news_lg/` and `models/stanza/` for the modern pipelines
- the legacy `pl_spacy_model_morfeusz` and `pl_nask` models into their own venvs

The legacy ipipan packages are fragile; their dependency stacks are pinned to
specific versions (recorded in each `pipelines/*/pyproject.toml` and `uv.lock`)
so they install from wheels on a modern system. If one still fails to build,
setup keeps going and that pipeline simply reports as unavailable. Re-run with
`REBUILD_LEGACY=1` to rebuild the legacy venvs, or `UV_VENV_CLEAR=1` to recreate
the main venv.

## Run

```bash
source .venv/bin/activate
python comparison.py
```

Results land in `reports/`:

- `reports/<pipeline>.json` — raw per-pipeline output
- `reports/summary.json` / `reports/summary.md` — scored comparison table

## Overrides

| Variable                  | Purpose                                       |
| ------------------------- | --------------------------------------------- |
| `SPACY_MODEL`             | spaCy model name or path                      |
| `STANZA_RESOURCES_DIR`    | Stanza resources directory                    |
| `SPACY_PL_RUNNER_PYTHON`  | interpreter for the spaCy-PL runner           |
| `SPACY_PL_TRF_RUNNER_PYTHON` | interpreter for the spaCy-PL-TRF runner    |
| `SPACY_PL_MODEL`          | legacy spaCy-PL model name or path            |
| `SPACY_PL_TRF_MODEL`      | spaCy-PL-TRF model name or path               |
