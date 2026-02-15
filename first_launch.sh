#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Verify Python version meets minimum requirement (3.9+)
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [[ "$MAJOR" -lt 3 ]] || { [[ "$MAJOR" -eq 3 ]] && [[ "$MINOR" -lt 9 ]]; }; then
  echo "Error: Python 3.9+ required (found $PYTHON_VERSION)" >&2
  exit 1
fi

if [[ ! -d ".venv" ]]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q

echo "Launching Neon City Chess..."
python main.py
