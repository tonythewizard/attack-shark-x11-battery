#!/usr/bin/env python3
"""Compatibility launcher for running directly from a source checkout."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from attack_shark_x11.app import main  # noqa: E402

raise SystemExit(main())
