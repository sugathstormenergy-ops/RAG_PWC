#!/usr/bin/env bash
# Task 7 — install on a machine with NO internet access.
#
# Prerequisites (must already be on the offline machine, copied over from
# scripts/package_offline.sh run on an online machine):
#   - This whole project folder, including wheels/ (downloaded wheels)
#   - Ollama installed (the Ollama installer itself must be copied/run
#     separately -- see https://ollama.com/download -- it is not a Python
#     package and is not handled by this script)
#   - The Ollama model folder copied to the path OLLAMA_MODELS points to
#     (default ~/.ollama/models), containing llama3.2:3b and
#     nomic-embed-text already pulled on an online machine
#
# Usage:
#   bash install.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "== Installing Python dependencies from local wheels (no network) =="
python3 -m pip install --no-index --find-links wheels/ -r requirements.txt

echo "== Disabling telemetry =="
export ANONYMIZED_TELEMETRY=False
mkdir -p "$HOME/.streamlit"
cat > "$HOME/.streamlit/config.toml" <<'EOF'
[browser]
gatherUsageStats = false
EOF

echo "== Checking Ollama =="
if command -v ollama >/dev/null 2>&1; then
  echo "Ollama found: $(ollama --version)"
  if ollama list | grep -q "llama3.2:3b\|qwen2.5"; then
    echo "Chat model present."
  else
    echo "WARNING: no chat model found in 'ollama list'. Make sure the"
    echo "model folder was copied to \$OLLAMA_MODELS before running offline."
  fi
else
  echo "WARNING: 'ollama' command not found. Install Ollama first"
  echo "(copy the offline installer from https://ollama.com/download,"
  echo "obtained on an online machine beforehand)."
fi

echo "== Ingesting documents and building the search index =="
python3 src/ingest.py --rebuild
python3 src/search_index.py --build

echo ""
echo "Install complete. Try it:"
echo "  python3 src/ask.py \"What is the vibration test duration for RADAR-100?\""
echo "  streamlit run ui/app.py     # optional web UI, binds to 127.0.0.1 only"
