#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from attack_shark_x11.app import make_ico, make_png  # noqa: E402

make_ico(ROOT / "assets" / "attack_shark_x11.ico")
make_png(ROOT / "assets" / "attack_shark_x11.png", 256)
print("Generated application icons.")
