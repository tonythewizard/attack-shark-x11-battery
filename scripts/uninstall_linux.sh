#!/usr/bin/env bash
set -euo pipefail

APP_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/AttackSharkX11"
APP_DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"

rm -f "$HOME/.local/bin/attack-shark-x11"
rm -f "$APP_DESKTOP_DIR/attack-shark-x11.desktop"
rm -f "$ICON_DIR/attack-shark-x11.png"
rm -f "$AUTOSTART_DIR/attack-shark-x11.desktop"
rm -rf "$APP_HOME"

echo "Attack Shark X11 removed."
