#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/AttackSharkX11"
VENV="$APP_HOME/venv"
BIN_DIR="$HOME/.local/bin"
APP_DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
# Reinstall the local checkout even when its version number is unchanged.
"$VENV/bin/python" -m pip install --force-reinstall --no-deps "$ROOT"

mkdir -p "$BIN_DIR" "$APP_DESKTOP_DIR" "$ICON_DIR"
ln -sfn "$VENV/bin/attack-shark-x11" "$BIN_DIR/attack-shark-x11"
cp "$ROOT/assets/attack_shark_x11.png" "$ICON_DIR/attack-shark-x11.png"

sed "s|Exec=attack-shark-x11|Exec=$BIN_DIR/attack-shark-x11|" \
  "$ROOT/packaging/linux/attack-shark-x11.desktop" \
  > "$APP_DESKTOP_DIR/attack-shark-x11.desktop"
chmod +x "$APP_DESKTOP_DIR/attack-shark-x11.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APP_DESKTOP_DIR" >/dev/null 2>&1 || true
fi

echo "Attack Shark X11 installed. Launch it from your app menu or run: attack-shark-x11"
