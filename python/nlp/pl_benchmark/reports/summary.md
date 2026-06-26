# Polish NLP Comparison

| Pipeline | Status | Load ms | Process ms | Chars/s | Sentence F1 | Lemma top1 | Lemma any | POS top1 | POS any | NER F1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| spacy | ok | 1858.2 | 20.8 | 32096.8 | 1.000 | 0.714 | 0.714 | 1.000 | 1.000 | 0.667 |
| stanza | ok | 6105.0 | 2089.4 | 319.7 | 1.000 | 0.929 | 0.929 | 1.000 | 1.000 | 0.737 |
| morfeusz2 | ok | 44.5 | 1.7 | 398577.4 | N/A | 0.857 | 1.000 | 1.000 | 1.000 | N/A |
| spacy-pl | ok | 7463.4 | 1009.5 | 661.7 | 0.750 | 0.857 | 0.857 | 1.000 | 1.000 | 0.636 |
| spacy-pl-trf | ok | 3619.7 | 307.4 | 2173.1 | 1.000 | 0.857 | 0.857 | 0.929 | 0.929 | 0.737 |

## spacy

- Available: `True`
- Version: `3.8.14`
- Model: `/home/jswie/Github/Playground/python/NLP/pl_benchmark/models/spacy/pl_core_news_lg`
- Error: `None`
- Notes: `runner=/home/jswie/Github/Playground/python/NLP/pl_benchmark/.venv/bin/python`

## stanza

- Available: `True`
- Version: `1.13.0`
- Model: `tokenize,pos,lemma,ner`
- Error: `None`
- Notes: `resources_dir=/home/jswie/Github/Playground/python/NLP/pl_benchmark/models/stanza; runner=/home/jswie/Github/Playground/python/NLP/pl_benchmark/.venv/bin/python`

## morfeusz2

- Available: `True`
- Version: `1.99.15`
- Model: `Morfeusz()`
- Error: `None`
- Notes: `Morfeusz2 is a non-disambiguating morphological analyzer; it returns all candidate lemmas/tags. Sentence and NER scores are intentionally N/A.; runner=/home/jswie/Github/Playground/python/NLP/pl_benchmark/.venv/bin/python`

## spacy-pl

- Available: `True`
- Version: `2.3.2`
- Model: `pl_spacy_model_morfeusz`
- Error: `None`
- Notes: `pl_spacy_model_morfeusz on spaCy 2.2.4 (dedicated .venv).; runner=/home/jswie/Github/Playground/python/NLP/pl_benchmark/pipelines/spacy_pl/.venv/bin/python`

## spacy-pl-trf

- Available: `True`
- Version: `3.5.4`
- Model: `pl_nask`
- Error: `None`
- Notes: `pl_nask HerBERT transformer on spaCy 3.3 (dedicated .venv).; runner=/home/jswie/Github/Playground/python/NLP/pl_benchmark/pipelines/spacy_pl_trf/.venv/bin/python`
