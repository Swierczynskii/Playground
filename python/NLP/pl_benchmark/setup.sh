#!/usr/bin/env bash
set -euo pipefail

# Sets up every Polish NLP pipeline used by the benchmark. Layout:
#   shared/                 dependency-free core library (pl_bench_core)
#   pipelines/<name>/       one directory per pipeline (runner + optional pyproject)
#
# Three venvs / pyproject.toml files:
#   .venv                       main: orchestrator + spaCy, Stanza, Morfeusz2 (py3.12)
#   pipelines/spacy_pl/.venv    legacy ipipan pl_spacy_model_morfeusz on spaCy 2.2.4 (py3.8)
#   pipelines/spacy_pl_trf/.venv  ipipan pl_nask HerBERT on spaCy 3.3 (py3.10)
#
# Core models are stored locally under models/; legacy models install into their
# own venvs. comparison.py auto-detects each venv by directory, so no env vars are
# needed. The legacy upstream packages are fragile: failures are reported but do
# not abort the core setup. Set REBUILD_LEGACY=1 to rebuild the legacy venvs and
# UV_VENV_CLEAR=1 to recreate the main venv.
#
# Run from the pl_benchmark/ directory: ./setup.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Checking uv..."
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "Ensuring Python 3.12 is available in uv..."
uv python install 3.12

if [ -d .venv ] && [ -z "${UV_VENV_CLEAR:-}" ]; then
  echo "Reusing existing main .venv (set UV_VENV_CLEAR=1 to recreate)..."
else
  echo "Creating main .venv with Python 3.12 (via uv)..."
  uv venv -p 3.12 --clear .venv
fi

echo "Activating main venv..."
# shellcheck source=/dev/null
source .venv/bin/activate

echo "Installing main dependencies (orchestrator + modern pipelines + shared lib)..."
uv sync

echo "Installing pip into venv (needed by spaCy's model downloader)..."
uv pip install pip

MODELS_DIR="$SCRIPT_DIR/models"
mkdir -p "$MODELS_DIR/spacy" "$MODELS_DIR/stanza"

echo "Preparing local spaCy Polish model in models/spacy ..."
SPACY_TARGET="$MODELS_DIR/spacy/pl_core_news_lg" python - <<'PY'
import importlib
import os
import shutil
from pathlib import Path

import spacy

target = Path(os.environ["SPACY_TARGET"])
if (target / "config.cfg").exists():
    print("spaCy Polish model already present at", target)
else:
    try:
        pkg = importlib.import_module("pl_core_news_lg")
    except ModuleNotFoundError:
        print("Downloading spaCy Polish model (pl_core_news_lg)...")
        spacy.cli.download("pl_core_news_lg")
        importlib.invalidate_caches()
        pkg = importlib.import_module("pl_core_news_lg")

    pkg_dir = Path(pkg.__file__).resolve().parent
    data_dir = next(p for p in pkg_dir.iterdir() if (p / "config.cfg").exists())
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(data_dir, target)
    print("Copied spaCy model to", target)
PY

echo "Downloading Stanza Polish models into models/stanza ..."
STANZA_DIR="$MODELS_DIR/stanza"
export STANZA_RESOURCES_DIR="$STANZA_DIR"
python - <<'PY'
import os, stanza
target = os.environ["STANZA_RESOURCES_DIR"]
os.makedirs(target, exist_ok=True)
stanza.download('pl', model_dir=target, processors='tokenize,pos,lemma,ner', verbose=False)
print("Downloaded Stanza models to:", target)
PY

# --------------------------------------------------------------------------
# Legacy ipipan pipelines (dedicated venvs, fragile upstream packages).
# --------------------------------------------------------------------------

# The published wheel has an invalid PEP 440 version ("any"); use the sdist.
PL_NASK_SDIST="https://huggingface.co/ipipan/pl_nask/resolve/main/pl_nask-0.0.7.tar.gz"
echo "=== spaCy-PL-TRF (pl_nask, HerBERT transformer, spaCy 3.3, py3.10) ==="
if [ -x pipelines/spacy_pl_trf/.venv/bin/python ] \
  && pipelines/spacy_pl_trf/.venv/bin/python -c "import pl_nask" 2>/dev/null \
  && [ -z "${REBUILD_LEGACY:-}" ]; then
  echo "Reusing existing pipelines/spacy_pl_trf/.venv (set REBUILD_LEGACY=1 to rebuild)."
elif uv python install 3.10 \
  && uv sync --project pipelines/spacy_pl_trf \
  && uv pip install --python pipelines/spacy_pl_trf/.venv/bin/python --no-deps "$PL_NASK_SDIST"; then
  # Model is packaged data only; --no-deps keeps the pinned spaCy stack intact.
  echo "spaCy-PL-TRF environment ready."
else
  echo "WARNING: spaCy-PL-TRF setup failed (see output above); pipeline will be unavailable."
fi

PL_MODEL_URL="https://zil.ipipan.waw.pl/SpacyPL?action=AttachFile&do=get&target=pl_spacy_model_morfeusz-0.1.3.tar.gz"
echo "=== spaCy-PL (pl_spacy_model_morfeusz, spaCy 2.2.4, py3.8) ==="
if [ -x pipelines/spacy_pl/.venv/bin/python ] \
  && pipelines/spacy_pl/.venv/bin/python -c "import spacy, pl_spacy_model_morfeusz" 2>/dev/null \
  && [ -z "${REBUILD_LEGACY:-}" ]; then
  echo "Reusing existing pipelines/spacy_pl/.venv (set REBUILD_LEGACY=1 to rebuild)."
elif uv python install 3.8 \
  && uv sync --project pipelines/spacy_pl \
  && PL_TMP_MODEL="$(mktemp -d)/pl_spacy_model_morfeusz-0.1.3.tar.gz" \
  && curl -L -o "$PL_TMP_MODEL" "$PL_MODEL_URL" \
  && uv pip install --python pipelines/spacy_pl/.venv/bin/python --no-deps "$PL_TMP_MODEL"; then
  echo "spaCy-PL environment ready."
else
  echo "WARNING: spaCy-PL setup failed (see output above); pipeline will be unavailable."
fi

cat <<'EOF'

Setup complete. Core models live under models/; legacy models live in their
dedicated venvs (pipelines/spacy_pl/.venv, pipelines/spacy_pl_trf/.venv).

Run the full benchmark (all five pipelines auto-detected):
  source .venv/bin/activate
  python comparison.py

Override interpreters or model names if needed:
  export SPACY_PL_RUNNER_PYTHON=/path/to/python
  export SPACY_PL_TRF_RUNNER_PYTHON=/path/to/python
  export SPACY_PL_MODEL=pl_spacy_model_morfeusz
  export SPACY_PL_TRF_MODEL=pl_nask
EOF
