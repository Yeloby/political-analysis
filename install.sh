#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"

python3 -m venv --system-site-packages "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/pip" install -e "$ROOT"

mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.local/share/icons/hicolor/scalable/apps"

ln -sf "$VENV/bin/political-analysis" \
  "$HOME/.local/bin/political-analysis"

ln -sf "$VENV/bin/political-analysis-gui" \
  "$HOME/.local/bin/political-analysis-gui"

ln -sf "$VENV/bin/pol" \
  "$HOME/.local/bin/pol"

install -m 644 \
  "$ROOT/packaging/political-analysis.desktop" \
  "$HOME/.local/share/applications/political-analysis.desktop"

install -m 644 \
  "$ROOT/assets/political-analysis.svg" \
  "$HOME/.local/share/icons/hicolor/scalable/apps/political-analysis.svg"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database \
      "$HOME/.local/share/applications" || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache \
      "$HOME/.local/share/icons/hicolor" || true
fi

echo
echo "Political Analysis installed."
echo "CLI: political-analysis or pol"
echo "GUI: political-analysis-gui"
echo "Application launcher: Political Analysis"
