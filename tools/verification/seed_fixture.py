#!/usr/bin/env python3
"""Opt-in non-VEX calibration data for native conversion/browser verification.

Run: .venv/bin/python tools/verification/seed_fixture.py --prepare
Use TACHYON_DATA_DIR=.local/verification-workspace for a separate verification
server. The default user workspace is never changed. A nonempty destination is
refused. All geometry and its narrowly scoped authorship evidence are generated
locally; this script never reads or qualifies research/user CAD.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path


def seed(project_root: Path, *, prepare: bool = False):
    sys.path.insert(0, str(project_root / "server"))
    sys.path.insert(0, str(project_root / "server/tests"))
    os.environ.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "tachyon-verification-cache"))
    from fixture_support import create_calibration_workspace

    workspace = create_calibration_workspace(
        project_root, project_root / ".local/verification-workspace")
    if prepare:
        from tachyon.cad.prepare import prepare_component

        catalog = workspace.catalog()
        catalog.register()
        prepare_component(catalog, workspace.component)
    return workspace


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate original Tachyon test_fixture data (non-VEX); converter/render verification only")
    parser.add_argument("--prepare", action="store_true", help="Also register and run native STEP-to-GLB conversion in the separate verification workspace")
    args = parser.parse_args(argv)
    try:
        workspace = seed(Path(__file__).resolve().parents[2], prepare=args.prepare)
    except FileExistsError:
        parser.exit(2, "Calibration test_fixture destination must be new or empty.\n")
    print(f"Converter/render test_fixture (non-VEX): {workspace.component.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
