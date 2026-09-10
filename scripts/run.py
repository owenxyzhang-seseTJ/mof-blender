#!/usr/bin/env python3
"""Source-tree launcher; no editable install or network access during startup."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mof_blender.cli import main

main()
