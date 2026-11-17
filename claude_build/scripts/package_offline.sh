#!/usr/bin/env bash
# Task 7 — package the tool for offline install.
#
# Run this ON A MACHINE WITH INTERNET to produce an offline bundle, then
# copy the whole project folder (including the new wheels/ and
# ollama_models/ directories it creates) to the air-gapped machine.
#
# Usage:
#   bash scripts/package_offline.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1. Downloading Python wheels for offline install =="
mkdir -p wheels
pip download -r requirements.txt -d wheels/

echo "== 2. Locating Ollama model storage =="
OLLAMA_MODELS_DIR="${OLLAMA_MODELS:-$HOME/.ollama/models}"
if [ -d "$OLLAMA_MODELS_DIR" ]; then
  echo "Found Ollama models at $OLLAMA_MODELS_DIR"
  echo "Copy that whole directory to the offline machine's same path"
  echo "(or set OLLAMA_MODELS to point Ollama at the copy) -- do NOT"
  echo "upload it to GitHub, it's multiple GB. Suggested models:"
  echo "  ollama pull llama3.2:3b"
  echo "  ollama pull nomic-embed-text"
else
  echo "WARNING: $OLLAMA_MODELS_DIR not found. Pull your models first:"
  echo "  ollama pull llama3.2:3b && ollama pull nomic-embed-text"
fi

echo "== 3. Disabling telemetry (Chroma, Streamlit) =="
export ANONYMIZED_TELEMETRY=False
mkdir -p "$HOME/.streamlit"
cat > "$HOME/.streamlit/config.toml" <<'EOF'
[browser]
gatherUsageStats = false
EOF
echo "Set ANONYMIZED_TELEMETRY=False and disabled Streamlit usage stats."
echo "(install.sh also sets these on the target machine.)"

echo "== Done. Bundle contents: =="
du -sh wheels/ 2>/dev/null || true
echo "Copy this whole project directory, plus your Ollama model folder, to the offline machine."
