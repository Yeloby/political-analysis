#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"

if ! pkg-config --exists cairo gobject-introspection-1.0; then
    echo "Missing GTK/PyGObject build dependencies."
    echo
    echo "On Ubuntu/Pop!_OS, install them with:"
    echo "  sudo apt install libcairo2-dev libgirepository1.0-dev"
    exit 1
fi

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/pip" install "PyGObject==3.48.2"
"$VENV/bin/pip" install -e "$ROOT"

mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.local/share/icons/hicolor/scalable/apps"

ln -sf "$VENV/bin/samfunnsdata" \
  "$HOME/.local/bin/samfunnsdata"

ln -sf "$VENV/bin/samfunnsdata-gui" \
  "$HOME/.local/bin/samfunnsdata-gui"

install -m 644 \
  "$ROOT/packaging/samfunnsdata.desktop" \
  "$HOME/.local/share/applications/samfunnsdata.desktop"

install -m 644 \
  "$ROOT/assets/samfunnsdata.svg" \
  "$HOME/.local/share/icons/hicolor/scalable/apps/samfunnsdata.svg"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database \
      "$HOME/.local/share/applications" || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache \
      "$HOME/.local/share/icons/hicolor" || true
fi

echo
echo "Samfunnsdata installed."
echo "CLI: samfunnsdata"
echo "GUI: samfunnsdata-gui"
echo "Application launcher: Samfunnsdata"
