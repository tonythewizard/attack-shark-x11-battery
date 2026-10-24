#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo: sudo $0" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RULE_SOURCE="$ROOT/packaging/linux/70-attack-shark-x11.rules"
RULE_TARGET="/etc/udev/rules.d/70-attack-shark-x11.rules"

install -m 0644 "$RULE_SOURCE" "$RULE_TARGET"
udevadm control --reload-rules
udevadm trigger --subsystem-match=hidraw
udevadm trigger --subsystem-match=usb

echo "Installed the Attack Shark X11 udev rule. Unplug and reconnect the wireless dongle, then run attack-shark-x11 --check."
