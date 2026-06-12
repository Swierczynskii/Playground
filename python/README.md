# Python

Python experiments and projects.

## Projects

### `NLP/` — Polish NLP comparison

Compares Polish NLP pipelines (spaCy, Stanza, Trankit) on tokenization,
POS tagging, lemmatization, and named-entity recognition.

```bash
cd NLP
./setup.sh                     # creates .venv via uv, installs deps + PL models
source .venv/bin/activate
python nlp_comparison.py
```

Sample input data lives in `examples.txt` (synthetic Polish text).
