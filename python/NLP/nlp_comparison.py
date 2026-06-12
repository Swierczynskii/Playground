import os

# Speed: cap CPU thread pools to reduce overhead on small docs
os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("MKL_NUM_THREADS", "8")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import difflib
import shutil
import time
from pathlib import Path
from typing import Any, Dict

# Speed: limit PyTorch to a single thread
try:
    import torch

    torch.set_num_threads(1)
    if hasattr(torch, "set_num_interop_threads"):
        torch.set_num_interop_threads(1)
except Exception:
    torch = None  # type: ignore

import spacy
import stanza
from stanza.pipeline.core import DownloadMethod


# Create Stanza pipelines cache keyed by processors only
_stanza_cache: Dict[str, Any] = {}

# Create spaCy singleton pipeline for CPU
_spacy_nlp = None


def resolve_stanza_resources_dir():
    """
    Resolve Stanza resources directory for offline use.

    Checks STANZA_RESOURCES_DIR environment variable first, then ~/stanza_resources, then ./stanza_resources as fallback.
    Validates that the directory exists, contains resources.json, and has a 'pl' subdirectory.
    Raises RuntimeError with guidance if validation fails.
    """
    candidates = []
    env_dir = os.environ.get("STANZA_RESOURCES_DIR")
    if env_dir:
        candidates.append(env_dir)
    candidates.extend(["~/stanza_resources", "./stanza_resources"])
    resolved_dir = None
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.is_dir():
            resolved_dir = str(path)
            break

    if not resolved_dir:
        raise RuntimeError(
            "Stanza resources directory not found. "
            "Set STANZA_RESOURCES_DIR environment variable to the path containing Stanza models, "
            "or place models in ~/stanza_resources or ./stanza_resources. "
            "Expected layout: stanza_resources/resources.json and stanza_resources/pl/ with model files. "
            "Download models offline and place them manually for strict offline operation."
        )

    # Validate presence of resources.json and pl subdir
    resources_json = Path(resolved_dir) / "resources.json"
    pl_dir = Path(resolved_dir) / "pl"
    if not resources_json.exists():
        raise RuntimeError(
            f"Stanza resources.json not found in {resolved_dir}. "
            "Download models offline and ensure resources.json is present."
        )
    if not pl_dir.is_dir():
        raise RuntimeError(
            f"Stanza 'pl' language directory not found in {resolved_dir}. "
            f"Download Polish models offline and place them in {resolved_dir}/pl/."
        )

    return str(Path(resolved_dir).resolve())




def get_stanza_nlp(processors: str):
    """
    Build or retrieve a cached Stanza pipeline.

    - processors: e.g. "tokenize,pos,lemma" or "tokenize,ner".
    """
    key = processors
    if key in _stanza_cache:
        return _stanza_cache[key]

    resources_dir = resolve_stanza_resources_dir()

    try:
        nlp = stanza.Pipeline(
            lang="pl",
            processors=processors,
            use_gpu=False,
            dir=resources_dir,
            verbose=False,
            download_method=DownloadMethod.REUSE_RESOURCES,
            tokenize_batch_size=8192,
            pos_batch_size=8192,
            lemma_batch_size=8192,
            ner_batch_size=8192,
        )
    except Exception as e:
        print(f"Pipeline creation failed: {e}")
        print(
            "This likely indicates Stanza is still attempting a network download despite local resources."
        )
        raise

    _stanza_cache[key] = nlp
    return nlp


def get_spacy_nlp():
    global _spacy_nlp
    if _spacy_nlp is None:
        # Prefer local model under NLP/spacy_models/pl_core_news_lg for offline use
        local_model_dir = Path(__file__).parent / "spacy_models" / "pl_core_news_lg"
        if local_model_dir.is_dir():
            _spacy_nlp = spacy.load(str(local_model_dir))
        else:
            # Fallback to environment-installed package
            _spacy_nlp = spacy.load("pl_core_news_lg")
    return _spacy_nlp


def truncate_sent(sent: str, max_len: int) -> str:
    if len(sent) <= max_len:
        return sent
    return sent[:max_len] + "..."


try:
    from rapidfuzz.distance import Levenshtein

    def levenshtein_distance(s1, s2):
        return Levenshtein.distance(s1, s2)

    def levenshtein_normalized_similarity(s1, s2):
        return Levenshtein.normalized_similarity(s1, s2)
except ImportError:

    def levenshtein_distance(s1, s2):
        return len(list(difflib.ndiff(s1, s2)))

    def levenshtein_normalized_similarity(s1, s2):
        sm = difflib.SequenceMatcher(None, s1, s2)
        return sm.ratio()


def analyze_spacy(text: str):
    """Analyze text with spaCy: process, collect sentences, tokens, and entities."""
    nlp = get_spacy_nlp()

    start_proc = time.time()
    doc = nlp(text)
    total_proc_time = (time.time() - start_proc) * 1000  # ms

    sentences = [
        (sent.start_char, sent.end_char, sent.text.strip()) for sent in doc.sents
    ]

    tokens = [(token.text, token.lemma_) for token in doc if token.text.strip()]

    ents = [(ent.start_char, ent.end_char, ent.label_, ent.text) for ent in doc.ents]

    return {
        "sentences": sentences,
        "tokens": tokens,
        "ents": ents,
        "timings": {
            "total_process_ms": total_proc_time,
        },
    }


def analyze_stanza_component(text: str, nlp: stanza.Pipeline, processors: str):
    """Analyze text with Stanza using specified processors."""
    try:
        print(f"Analyzing with Stanza processors: {processors}")

        start_proc = time.time()
        doc: Any = nlp(text)
        total_proc_time = (time.time() - start_proc) * 1000  # ms

        result: Dict[str, Any] = {"timings": {"total_process_ms": total_proc_time}}

        if "tokenize" in processors:
            sentences = []
            for sent in doc.sentences:
                sent_start = sent.words[0].start_char if sent.words else 0
                sent_end = sent.words[-1].end_char if sent.words else 0
                sentences.append(
                    (sent_start, sent_end, " ".join(w.text for w in sent.words).strip())
                )
            result["sentences"] = sentences

        if "lemma" in processors:
            tokens = []
            for sent in doc.sentences:
                for word in sent.words:
                    tokens.append((word.text, word.lemma))
            result["tokens"] = tokens

        if "ner" in processors:
            ents = []
            for sent in doc.sentences:
                for ent in getattr(sent, "ents", []):
                    ents.append((ent.start_char, ent.end_char, ent.type, ent.text))
            result["ents"] = ents

        return result
    except Exception as e:
        print(f"Stanza analysis failed for {processors}: {e}")
        import traceback

        traceback.print_exc()
        return None


def build_boundary_marked_text(text: str, sentences):
    """Build a string with | inserted at sentence boundaries."""
    if not sentences:
        return text
    marked = []
    prev_end = 0
    for start, end, _ in sentences:
        marked.append(text[prev_end:start])
        marked.append(text[start:end])
        marked.append("|")
        prev_end = end
    marked.append(text[prev_end:])
    return "".join(marked)


def compare_segmentation(sent1, sent2, text, file_path, label2="Stanza"):
    """Compare sentence segmentation and write differences to file."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("=== Sentence Segmentation Comparison ===\n")
        f.write(f"spaCy sentences: {len(sent1)}\n")
        if sent2 is None:
            f.write(f"{label2} sentences: N/A (failed)\n")
            return
        spacy_marked = build_boundary_marked_text(text, sent1)
        other_marked = build_boundary_marked_text(text, sent2)

        dist = levenshtein_distance(spacy_marked, other_marked)
        sim = levenshtein_normalized_similarity(spacy_marked, other_marked)

        f.write(f"{label2} sentences: {len(sent2)}\n")
        f.write(f"Levenshtein distance: {dist}\n")
        f.write(f"Levenshtein normalized similarity: {sim:.3f}\n")

        # List differing sentences
        spacy_texts = [sent for _, _, sent in sent1]
        other_texts = [sent for _, _, sent in sent2]
        matcher = difflib.SequenceMatcher(None, spacy_texts, other_texts)
        differences = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag in ("replace", "delete", "insert"):
                spacy_group = [truncate_sent(s, 100) for s in spacy_texts[i1:i2]]
                other_group = [truncate_sent(s, 100) for s in other_texts[j1:j2]]
                differences.append((tag, spacy_group, other_group))
        if differences:
            f.write("Sentences that differ:\n")
            for tag, spacy_group, other_group in differences:
                if tag == "replace":
                    f.write("  - spaCy sentences:\n")
                    for s in spacy_group:
                        f.write(f"      {s}\n")
                    f.write(f"  - {label2} sentences:\n")
                    for s in other_group:
                        f.write(f"      {s}\n")
                elif tag == "delete":
                    f.write(f"  - spaCy sentences (no match in {label2}):\n")
                    for s in spacy_group:
                        f.write(f"      {s}\n")
                elif tag == "insert":
                    f.write(f"  - {label2} sentences (no match in spaCy):\n")
                    for s in other_group:
                        f.write(f"      {s}\n")
        else:
            f.write("All sentences match.\n")


def compare_lemmatization(tok1, tok2, file_path, label2="Stanza"):
    """Compare lemmatization and write differences to file."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("=== Lemmatization Differences ===\n")
        if tok2 is None:
            f.write(f"{label2} lemmatization N/A (failed)\n")
            return

        spacy_texts = [t[0] for t in tok1]
        other_texts = [t[0] for t in tok2]

        matcher = difflib.SequenceMatcher(None, spacy_texts, other_texts)
        spacy_lemmas = {i: l for i, (_, l) in enumerate(tok1)}
        other_lemmas = {i: l for i, (_, l) in enumerate(tok2)}

        differences = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for i in range(i1, i2):
                    orig = spacy_texts[i]
                    spacy_l = spacy_lemmas.get(i, "")
                    other_l = other_lemmas.get(j1 + (i - i1), "")
                    if spacy_l != other_l:
                        differences.append(
                            f"Original: {orig} | spaCy: {spacy_l} | {label2}: {other_l}"
                        )

        if differences:
            for diff in differences:
                f.write(diff + "\n")
        else:
            f.write("No lemma differences found.\n")


def compare_ner(ent1, ent2, file_path, label2="Stanza"):
    """Compare NER and write differences to file."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("=== NER Differences ===\n")
        if ent2 is None:
            f.write(f"{label2} NER N/A (failed)\n")
            return

        # Simple comparison: list entities that differ
        spacy_ents = set((start, end, label, text) for start, end, label, text in ent1)
        other_ents = set((start, end, label, text) for start, end, label, text in ent2)

        only_spacy = spacy_ents - other_ents
        only_other = other_ents - spacy_ents

        if only_spacy:
            f.write("Entities only in spaCy:\n")
            for ent in only_spacy:
                f.write(f"  {ent[3]} ({ent[0]}-{ent[1]}, {ent[2]})\n")
        if only_other:
            f.write(f"Entities only in {label2}:\n")
            for ent in only_other:
                f.write(f"  {ent[3]} ({ent[0]}-{ent[1]}, {ent[2]})\n")
        if not only_spacy and not only_other:
            f.write("All NER entities match.\n")


def print_timings(times, label):
    """Print timings for a library."""
    print(f"{label} timings (ms):")
    for key, val in times.items():
        try:
            print(f"  {key}: {val:.2f}")
        except Exception:
            print(f"  {key}: {val}")
    print()


def main():
    # Set STANZA_RESOURCES_DIR to local stanza_resources for offline use
    os.environ["STANZA_RESOURCES_DIR"] = str(Path(__file__).parent / "stanza_resources")

    input_path = "desc.txt"
    text = Path(input_path).read_text(encoding="utf-8")

    # Recreate results and differences directories (absolute paths)
    results_dir = Path.cwd() / "results"
    differences_dir = Path.cwd() / "differences"
    shutil.rmtree(results_dir, ignore_errors=True)
    shutil.rmtree(differences_dir, ignore_errors=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    differences_dir.mkdir(parents=True, exist_ok=True)

    print("Warming up models...")
    # Warm spaCy
    nlp_spacy = get_spacy_nlp()
    nlp_spacy("test")
    # Warm Stanza pipelines
    nlp_stanza_all = get_stanza_nlp("tokenize,pos,lemma,ner")
    nlp_stanza_all("test")
    nlp_stanza_sent = get_stanza_nlp("tokenize")
    nlp_stanza_sent("test")
    nlp_stanza_lemma = get_stanza_nlp("tokenize,pos,lemma")
    nlp_stanza_lemma("test")
    nlp_stanza_ner = get_stanza_nlp("tokenize,ner")
    nlp_stanza_ner("test")
    print("Warm-up complete.\n")

    # Analyze spaCy (all in one)
    print("Analyzing with spaCy...")
    spacy_result = analyze_spacy(text)
    print_timings(spacy_result["timings"], "spaCy")

    #
    # Analyze Stanza
    print("Analyzing with Stanza...")
    stanza_all = analyze_stanza_component(text, nlp_stanza_all, "tokenize,pos,lemma,ner")
    stanza_sent = analyze_stanza_component(text, nlp_stanza_sent, "tokenize")
    stanza_lem = analyze_stanza_component(text, nlp_stanza_lemma, "tokenize,pos,lemma")
    stanza_ner = analyze_stanza_component(text, nlp_stanza_ner, "tokenize,ner")
    print_timings(
        {
            "total_process_ms": stanza_all["timings"]["total_process_ms"]
            if stanza_all
            else float("nan"),
        },
        "stanza_tokenize",
    )
    print_timings(
        {
            "total_process_ms": stanza_sent["timings"]["total_process_ms"]
            if stanza_sent
            else float("nan"),
        },
        "stanza_tokenize",
    )
    print_timings(
        {
            "total_process_ms": stanza_lem["timings"]["total_process_ms"]
            if stanza_lem
            else float("nan"),
        },
        "stanza_lemmatizer",
    )
    print_timings(
        {
            "total_process_ms": stanza_ner["timings"]["total_process_ms"]
            if stanza_ner
            else float("nan"),
        },
        "stanza_ner",
    )

    # Create results directory
    os.makedirs("results", exist_ok=True)

    # Save full results for spaCy
    with open(results_dir / "spacy_sentences.txt", "w", encoding="utf-8") as f:
        for _, _, sent in spacy_result["sentences"]:
            f.write(sent + "\n")
    with open(results_dir / "spacy_lemmas.txt", "w", encoding="utf-8") as f:
        for orig, lem in spacy_result["tokens"]:
            f.write(f"{orig}\t{lem}\n")
    with open(results_dir / "spacy_ner.txt", "w", encoding="utf-8") as f:
        for start, end, label, text_ent in spacy_result["ents"]:
            f.write(f"{start}-{end}\t{label}\t{text_ent}\n")

    # Save full results for Stanza (tokenize/lemma/ner)
    with open(results_dir / "stanza_sentences.txt", "w", encoding="utf-8") as f:
        if stanza_sent and "sentences" in stanza_sent:
            for _, _, sent in stanza_sent["sentences"]:
                f.write(sent + "\n")
    with open(results_dir / "stanza_lemmas.txt", "w", encoding="utf-8") as f:
        if stanza_lem and "tokens" in stanza_lem:
            for orig, lem in stanza_lem["tokens"]:
                f.write(f"{orig}\t{lem}\n")
    with open(results_dir / "stanza_ner.txt", "w", encoding="utf-8") as f:
        if stanza_ner and "ents" in stanza_ner:
            for start, end, label, text_ent in stanza_ner["ents"]:
                f.write(f"{start}-{end}\t{label}\t{text_ent}\n")

    # Write differences (spaCy vs Stanza)
    compare_segmentation(
        spacy_result["sentences"],
        stanza_sent["sentences"] if stanza_sent else None,
        text,
        differences_dir / "sentence_differences.txt",
        label2="Stanza"
    )
    compare_lemmatization(
        spacy_result["tokens"],
        stanza_lem["tokens"] if stanza_lem else None,
        differences_dir / "lemmatization_differences.txt",
        label2="Stanza",
    )
    compare_ner(
        spacy_result["ents"],
        stanza_ner["ents"] if stanza_ner else None,
        differences_dir / "NER_differences.txt",
        label2="Stanza",
    )

    print(f"Results saved to {results_dir}. Differences written to {differences_dir}.")


if __name__ == "__main__":
    main()
