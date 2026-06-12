#!/usr/bin/env bash
set -euo pipefail

# Script to set up uv environment via pyproject.toml, install dependencies, and download Polish models locally
# Run from the NLP/ directory: ./setup.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJ_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Checking uv..."
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "Ensuring Python 3.12 is available in uv..."
uv python install 3.12

echo "Creating .venv with Python 3.12 (via uv)..."
cd "$SCRIPT_DIR"
uv venv -p 3.12 .venv

echo "Activating venv..."
# shellcheck source=/dev/null
source .venv/bin/activate

echo "Installing project dependencies from pyproject.toml..."
uv sync

echo "Installing pip into venv..."
uv pip install pip

echo "Preparing local spaCy Polish..."
python - <<'PY'
import spacy
try:
    nlp = spacy.load("pl_core_news_lg")
    print("spaCy Polish model already installed.")
except OSError:
    print("Downloading spaCy Polish model...")
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "pl_core_news_lg"], check=True)
PY

echo "Downloading Stanza Polish models locally..."
STANZA_DIR="$SCRIPT_DIR/stanza_resources"
export STANZA_RESOURCES_DIR="$STANZA_DIR"
python - <<'PY'
import os, stanza
target = os.environ.get("STANZA_RESOURCES_DIR")
os.makedirs(target, exist_ok=True)
stanza.download('pl', model_dir=target, processors='tokenize,pos,lemma,ner', verbose=False)
print("Downloaded Stanza models to:", target)
PY

echo "Setup and download complete. Activate venv: source .venv/bin/activate"
