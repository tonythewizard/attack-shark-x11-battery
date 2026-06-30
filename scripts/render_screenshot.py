#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(ROOT / "src"))

from attack_shark_x11.ui_qt import THEMES, render_theme_preview  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", choices=THEMES, default="minimal_dark")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()
    output = args.output or ROOT / f"screenshot-{args.theme}.png"
    render_theme_preview(args.theme, output, (args.width, args.height))
    print(output)


if __name__ == "__main__":
    main()
