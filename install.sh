#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/pip" install -e "$ROOT"

mkdir -p "$HOME/.local/bin"

ln -sf "$VENV/bin/political-analysis" \
  "$HOME/.local/bin/political-analysis"

ln -sf "$VENV/bin/pol" \
  "$HOME/.local/bin/pol"

echo "Political Analysis installed."
