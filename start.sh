#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
VENV=".venv"
PORT="${PORT:-8000}"

if [ ! -d "$VENV" ]; then
  echo "creating venv..."
  python -m venv "$VENV"
fi
source "$VENV/bin/activate"
if [ -f requirements.txt ]; then
  pip install -q -r requirements.txt
else
  pip install -q pandas numpy networkx scikit-learn scipy pytest
fi
echo "serving on http://localhost:$PORT/sandbox/sandbox.html"
python -m webbrowser "http://localhost:$PORT/sandbox/sandbox.html" 2>/dev/null || true
exec python -m http.server "$PORT"