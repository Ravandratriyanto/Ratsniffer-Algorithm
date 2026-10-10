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
  pip install -q numpy networkx scikit-learn
fi
echo "serving on http://localhost:$PORT/sandbox/sandbox.html"
echo "flowcharts  http://localhost:$PORT/sandbox/flowcharts.html"
echo "detector (python, run from ratsniffer/):  sniff · eval · coverage · report · procurement"
python -m webbrowser "http://localhost:$PORT/sandbox/sandbox.html" 2>/dev/null || true
python -m webbrowser "http://localhost:$PORT/sandbox/flowcharts.html" 2>/dev/null || true
exec python -m http.server "$PORT"