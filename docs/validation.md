# Validation record / 验证记录

Verified on **2026-09-10**, macOS arm64, using the repository's Python environment.
This records executed checks. Cross-platform and arbitrary experimental-CIF coverage are not implied.

## Runtime / 运行环境

| Component | Executed version |
| --- | --- |
| Python | 3.12.13 |
| Blender | 5.2.1 LTS |
| AuToGraFS | 3.2.0 |
| RDKit | 2026.3.6 |
| ASE | 3.29.0 |
| Gemmi | 0.7.5 |
| NumPy / SciPy | 2.5.3 / 1.18.1 |
| MCP Python SDK | 1.30.0 |

The tested dependency versions are recorded in `requirements.lock.txt`. The Blender executable
is installed separately. Renders use Cycles CPU, four threads, denoising and three area lights.

## Automated checks / 自动检查

```text
.venv/bin/python -m pytest -q
17 passed, 8 warnings in 19.09s

.venv/bin/ruff check src scripts tests
All checks passed!
```

The tests exercise periodic edges including image shifts, ditopic-node contraction, planar
polygon geometry, nonperiodic layer unwrapping, direct versus reciprocal directions in an
oblique lattice, immutable source data, CIF block selection and partial occupancy rejection.
They also check RDKit convergence and molecular exports, graphene bilayer geometry,
reaction atom conservation and an actual MCP client handshake/tool call/error response.
The reaction regression test also checks that a rotating bond follows its moving atom
endpoints at intermediate frames; rod endpoints are baked on every integer frame.

The new gate-opening test verifies constant framework strut lengths, constant guest interatomic
distances, monotonic opening angles, the front-on camera, an upper-left starting position,
inward motion along the pore depth and a final guest center inside the aperture.

The eight warnings come from ASE's deprecated NumPy shape assignment (four) and Pymatgen's
unassigned oxidation-state radius heuristics (four). They do not fail the tests. The latter
are relevant to upstream bond perception; this small fixture set does not establish universal
chemical connectivity accuracy.

## Package installation / 软件包安装

Wheel and source distributions were built with `.venv/bin/python -m build --no-isolation`.
The wheel includes every Python runtime module and the Blender worker. The source archive
also includes both READMEs, generated CIF fixtures, tests, scripts, documentation and public
previews, the reusable skill, both plugin manifests and the MCP configuration. The unpacked
source archive passed all 17 tests; local environments and private render outputs are excluded.

A normal wheel installation was checked both in the project environment and in a fresh
Python 3.12 environment with its own dependencies and system-site-packages disabled. With
the working directory set to `/tmp` and `PYTHONPATH` unset, both environments imported the
installed package from `site-packages`, passed CLI help/tool/doctor checks, and completed a
real MCP handshake, tool listing, optimized water creation and a geometry-preserving camera
change. Installed runtime files matched the wheel; `pip check` reported no broken requirements.

An editable-install failure was isolated to this macOS filesystem: Python 3.12 skipped the
editable `.pth` file when its `UF_HIDDEN` flag was set. Clearing only that flag restored the
import, but it was reapplied locally without changing the file contents; the responsible
process was not identified. Normal installation (`pip install --no-deps .` after installing
dependencies) avoids this `.pth` dependency and is the recommended path. The source launcher
`scripts/run.py` also passed from `/tmp` and remains suitable for development.

## Real CIF analysis / 实际 CIF 分析

| Generated input | AuToGraFS candidate | Display node degree | Periodicity |
| --- | --- | --- | --- |
| `mof5_generated.cif` | `pcu` | 6 | 3D |
| `cof_hcb_generated.cif` | `hcb` | 3 | 2D |
| `dia_generated.cif` | `dia` | 4 | 3D |
| `fcu_generated.cif` | `fcu` | 12 | 3D |

All four models were generated, parsed and analyzed in the gallery run. The automated
integration tests repeat the MOF-5 and COF analyses, compare source hashes and require
connected scene edges. The private AuToGraFS 3.2.0 geometry adapter must match the engine's
quotient graph before use. Net names are **signature candidates**, not isomorphism proofs.

以上四个结构是生成模型，用于演示完整流程。没有把生成模型的回读验证写成对任意实验 CIF 的验证。
部分占位、无序或无限杆状构筑单元仍需按 README 中的限制处理。

## Rendered artifacts / 实际渲染产物

**16 scenes were rendered and visually inspected**, including three graphene views and
three animations. Every selected scene has a nonempty PNG, editable `.blend`, JSON recipe,
Blender audit and SHA-256 manifest. The gallery exporter rechecked every manifest artifact hash.

| Animation | Original PNG frames | Public GIF duration | Notes |
| --- | --- | --- | --- |
| Pore diffusion | 36 | 3.00 s | Rigid optimized CO₂ along an authored path |
| Interface reaction | 36 | 3.00 s | Explicit atom-conserving snapshots |
| Gate opening | 48 | 4.00 s | 24° → 90° hinge angle; final open-pore hold |

The public gate GIF stores 37 distinct frames because unchanged final frames are merged into
a hold; all **48 original PNG frames** exist locally. GIF timing is rounded to centiseconds
with the total presentation duration preserved. These seconds are playback time, not physical time.

Visual inspection covered geometry, framing, the three palettes, layer visibility, and animation
start/middle/end frames. Corrections made during QA included COF layer image seams, visible net
nodes, the dark graphene contrast, Chinese contact-sheet labels, and gate-opening camera/path
directions. Reaction rods were corrected to avoid drifting from atoms between sparse snapshots.
The gate now faces +z with +y upward, so the rhombus opens into a square in the image.
Earlier output revisions were preserved locally.

An additional **480 × 360 transparent acetone** render has an RGBA alpha range of **0–255**;
its foreground bounding box is `(32, 39, 448, 321)`, within the image. Acetone was optimized
with MMFF94s, with 8/8 conformers converged. The CLI call used the MCP-name alias
`create_molecule_scene` and the natural-language view `从侧面观察`.

[Public preview settings and hashes](assets/render-verification.json) omit personal local paths.
[Gallery](gallery.md) contains the resulting images and GIFs. Local `.blend` files and full
PNG frame sequences are generated by the reproduction command; they are not committed as large binaries.

## Agent integration / Agent 接入

An independent subagent completed a skill-only forward test: optimized acetone, SDF/XYZ
round trips, camera-only changes, and 21 geometry/source checks. That test found two usability
issues: missing MCP-name CLI aliases and the Chinese phrase `从侧面观察`. Both were fixed;
the complete transparent render above exercises the corrected call.

The Codex plugin schema validator passed. The MCP smoke test starts an actual server subprocess,
lists tools, creates a molecule, changes its camera and verifies an invalid direction returns a
structured error. Installation snippets are provided for Codex, Claude Code, Cursor/Windsurf
and VS Code, but those desktop clients have not all been individually end-to-end tested.

## Scientific meaning / 科学含义

Framework schematics, idealized layers and authored animations are modeling/illustration tools.
The gate model is an ideal hinged prism and is **not a deformation of an uploaded CIF**.
No simulation of pressure, adsorption stress, free energy, diffusion rate or reaction barrier
is performed. Force-field optimization applies to molecular guests, not to the framework or
reaction pathway. Application-specific material mechanisms still require external evidence.
