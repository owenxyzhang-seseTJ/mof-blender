# MOF Blender development

Work in this repository's `.venv`. `scripts/run.py` launches the source tree without an editable
install. Preserve source structures and output revisions. Keep topology candidates, measured
geometry, generated molecular conformers and schematic trajectories distinguishable.

Run `.venv/bin/python -m pytest -q` and `.venv/bin/ruff check src scripts tests`. Real Blender
verification uses `scripts/create_examples.py`; it writes fresh output folders. Render and inspect
images after changing visual geometry, cameras, materials or lights. Blender rendering may need
normal desktop permissions on macOS.

ChemBlender is a source reference only. Do not import its GPL source, node libraries or assets
into this independent implementation. References and inspected revisions live in docs/sources.md.
