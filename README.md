# MOF Blender

**CIF topology → editable framework geometry → Blender figures and schematic molecular motion.**

[简体中文](README.zh-CN.md) · [Examples](docs/gallery.md) · [Methods and sources](docs/sources.md) · [Validation](docs/validation.md)

MOF Blender is an agent-neutral Python toolkit with a stdio MCP server and a reusable skill.
It connects **AuToGraFS** topology analysis, **RDKit** molecular modeling and **Blender Cycles**
rendering. Codex and Claude Code can use the same core; other MCP-capable agents can use the
same tools or the JSON CLI.

![Rendered example gallery](docs/assets/contact-sheet.jpg)

## What it does

| Area | Implemented behavior |
| --- | --- |
| CIF inspection | Select a crystallographic data block, inspect occupancy/disorder, expand symmetry, retain source hashes |
| MOF / COF topology | Call AuToGraFS, record building units, periodic quotient edges, candidate nets, match tiers and periodic dimensions |
| Topology figures | Contract ditopic linkers for display; draw net nodes, connection-direction polyhedra and connecting rods |
| Molecular modeling | Read SMILES/MOL/SDF/PDB; generate ETKDG conformers; optimize with MMFF94s or UFF; export SDF and XYZ |
| Atomic rendering | Ball-and-stick, sticks, space filling, topology-only and hybrid atom/polyhedron scenes |
| 2D materials | Idealized graphene and h-BN sheets, AA/AB stacking, per-layer colors, CIF/XYZ export |
| Camera control | Direct-lattice directions `[uvw]`, reciprocal-plane normals `(hkl)`, Cartesian directions, orbiting, orthographic/perspective projection |
| Schematics | Compose structures with explicit placements and arrows |
| Animation | Rigid molecular motion along authored pore paths; atom-conserving interface-reaction snapshots and explicit bond changes; idealized hinged-pore gate opening |
| Artifacts | PNG, editable `.blend`, scene JSON, SHA-256 manifests; GIF and individual PNG frames for animations |

This is a **working first release**, not a universal topology solver or dynamics package.
Read the [limitations](#scientific-boundaries-and-limitations) before treating a drawing as scientific evidence.

## Example gallery

The example generator provides **16 examples, including three schematic animations**, spanning
three rendering presets:

- **paper:** white background, muted scientific colors and broad soft lighting;
- **porcelain:** pale neutral background and a soft ceramic appearance;
- **midnight:** dark blue background with teal nodes and warm connecting rods.

| Examples | Structure / representation |
| --- | --- |
| 01–02 | Optimized ethanol in ball-and-stick; optimized caffeine in space filling |
| 03–05 | Generated MOF-5: atomic pore view, six-connected `pcu` polyhedra, node-and-edge net |
| 06–07 | Generated boroxine COF: an atomic layer and three-connected `hcb` polygons |
| 08–09 | Four-connected `dia` tetrahedra and twelve-connected `fcu` node polyhedra |
| 10 | MOF-5 with transparent topology polyhedra over its atomic structure |
| 11–12 | CO₂ motion through a pore; an illustrative interface reaction storyboard |
| 13–15 | Graphene top view, inclined single layer, and AB-stacked bilayer |
| 16 | Optimized methane entering an idealized hinged pore as its rhombic aperture opens from 24° to a 90° square |

See [all examples with captions](docs/gallery.md). Framework inputs are generated models,
not uploaded experimental refinements. Every molecular guest is optimized before it is placed
in a schematic. The three animations are authored illustrations, not MD trajectories.
The gate-opening example constructs an idealized pore; it does not deform an uploaded CIF.

## Install

### Requirements

- Python **3.12 or newer**; Python 3.12 is the tested runtime.
- Blender installed separately. Rendering was tested with **Blender 5.2.1 LTS on macOS arm64**.
  Blender 4.5+ is the intended API range; other versions/platforms have not been run through the full gallery.
- A local environment with enough memory for the requested supercell. Atomic scenes are
  bounded at 25,000 atom instances; large systems are usually clearer in topology mode.

Using `uv`:

```bash
git clone https://github.com/owenxyzhang-seseTJ/mof-blender.git
cd mof-blender
uv venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.lock.txt
uv pip install --python .venv/bin/python --no-deps .
.venv/bin/python scripts/run.py doctor
```

Or use standard Python tools:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m pip install --no-deps .
```

On Windows replace `.venv/bin/python` with `.venv\Scripts\python.exe`. The lock file captures
the tested versions; availability of wheels can vary by platform. `pip install .` resolves the
package's declared requirements when the exact tested lock cannot be used.

These commands install a normal, noneditable package. The source launcher
`.venv/bin/python scripts/run.py ...` loads the checkout directly, so new invocations reflect
source edits without reinstalling. When using the installed `mof-blender` or `mof-blender-mcp`
entrypoints, reinstall the package after checkout updates: add `--reinstall` to the `uv pip
install` command above, or `--force-reinstall` to the `python -m pip install` command.

The chemistry libraries live in the project environment. Nothing needs to be installed into
Blender's bundled Python. Set `BLENDER_PATH` when Blender is outside a standard location:

```bash
export BLENDER_PATH="/Applications/Blender.app/Contents/MacOS/Blender"
```

## Connect an agent

### Codex

Register the stdio server using **absolute paths**:

```bash
codex mcp add mof-blender -- /absolute/mof-blender/.venv/bin/python /absolute/mof-blender/scripts/run.py mcp
```

Copy `skills/mof-blender` to your Codex skill directory, or load the included Codex plugin
manifest with your host's plugin workflow. For long render calls configure the server with
`tool_timeout_sec = 1800`; the generated TOML snippet includes this value.

### Claude Code

```bash
claude mcp add --scope user --transport stdio mof-blender -- /absolute/mof-blender/.venv/bin/python /absolute/mof-blender/scripts/run.py mcp
```

Copy `skills/mof-blender` into `.claude/skills/` for a project skill. The repository also includes
`.claude-plugin/plugin.json`; when the package executable is on PATH the root `.mcp.json` can
serve as the plugin's MCP configuration.
If the host does not inherit the virtual environment's PATH, use the generated absolute-path
configuration below.

### Cursor, Windsurf, VS Code and other agents

Generate absolute-path snippets for this checkout:

```bash
.venv/bin/python scripts/configure_agents.py --output integrations/local
```

The command produces:

- `codex.toml` for Codex;
- `mcp.json` with a `mcpServers` map for Claude/Cursor/Windsurf-style configurations;
- `vscode-mcp.json` with a `servers` map for VS Code;
- `register-commands.txt` with the local registration commands on Unix-like systems.

Merge the appropriate snippet into your host's configuration. The generator does **not**
modify global configuration. Do not register both a plugin-provided and a manually configured
copy of the same server. Restart/reload the host after installing. A real MCP client handshake
is tested; every listed agent's UI has not been exercised individually.

## Natural-language use

Examples of requests to the agent:

> Analyze this CIF with AuToGraFS. Draw the nodes as polyhedra and the linkers as thin lines.
> Use a white background and a 3 × 3 × 2 supercell.

> Optimize ethanol with RDKit, show it as a ball-and-stick molecule, and export its SDF and XYZ.

> 沿 b 轴看。保持结构与配色不变，再向右旋转 30 度。

> Show the `(1 0 0)` plane normal with an orthographic camera.

> Create an AB-stacked graphene bilayer and look at it from an inclined angle.

> Place optimized CO₂ in this pore and animate it along these waypoints. Label the motion schematic.

> Optimize methane, then animate it approaching an idealized hinged pore from the upper-left
> and in front of the aperture, entering along the pore depth as the in-plane rhombus opens
> into a square. Keep bar lengths and the guest's internal geometry fixed. View the pore
> front-on from +Z with +Y up, and label the motion schematic.

The camera tool directly understands a compact English/Chinese vocabulary. For more free-form
language the agent translates intent into the typed direction/projection arguments. `[uvw]`
uses the direct lattice; `(hkl)` uses the reciprocal lattice. They are different in a general
non-orthogonal crystal. `direction` points **from the target toward the camera**.

## CLI workflow

Run `.venv/bin/python scripts/run.py tools` to inspect current operation signatures. JSON
argument files avoid shell quoting problems and work across hosts. The CLI accepts short
operation names and their MCP long-name aliases: for example, `molecule` / `create_molecule_scene`,
`view` / `set_view`, `gate-open` / `create_gate_open_animation`, and `render` / `render_figure`.

### CIF → topology → figure

Create `analyze.json`:

```json
{
  "path": "examples/mof5_generated.cif",
  "output": "output/demo/mof5.analysis.json"
}
```

```bash
.venv/bin/python scripts/run.py call analyze --args-file analyze.json
```

Create `scene.json`:

```json
{
  "analysis": "output/demo/mof5.analysis.json",
  "output": "output/demo/mof5.scene.json",
  "representation": "polyhedra",
  "repeat": [3, 3, 2],
  "preset": "porcelain",
  "view": "沿[1 1 0]看",
  "node_scale": 0.22,
  "edge_radius": 0.1,
  "width": 1600,
  "height": 1200,
  "transparent": false
}
```

```bash
.venv/bin/python scripts/run.py call scene --args-file scene.json
```

Create `render.json`:

```json
{
  "scene": "output/demo/mof5.scene.json",
  "output_dir": "output/demo/render-v1",
  "samples": 128
}
```

```bash
.venv/bin/python scripts/run.py call render --args-file render.json
```

The output directory must be new. It contains `render.png`, `scene.blend`, `scene.json`,
`blender_audit.json`, `blender.log` and `manifest.json`. The manifest is written only after
all required artifacts exist.

### Molecules, layers and animations

Use the same `call ... --args-file ...` pattern:

| Operation | Key arguments |
| --- | --- |
| `molecule` | `smiles` or `source`, `output`, `optimize=true`, `conformers=8`, `representation` |
| `layer` | `material="graphene"`, `output`, `repeat=[8,8,1]`, `layers=2`, `stacking="AB"` |
| `view` | `scene`, `output`, `instruction`, or `direction` + `kind` |
| `compose` | `output`, `components` with scene/translation/scale, optional `arrows` |
| `diffusion` | `host_scene`, `guest_scene`, `output`, `waypoints`, `frames`, `fps` |
| `reaction` | `surface_scene`, `output`, explicit atom/bond `snapshots`, `frames`, `fps` |
| `gate-open` | `guest_scene`, `output`, `frames=48`, `fps=12`, `closed_angle=24`, `open_angle=90`, `edge_length=6`, `depth=2.8` |
| `render` | `scene`, `output_dir`, `samples`, `animate=true`, `timeout` |

See the [animation recipes](skills/mof-blender/references/animations.md) for complete snapshot
schemas. Animation coordinates are Cartesian angstroms. `fps` is presentation timing, not
physical simulation time.

The [complete gate-opening recipe](skills/mof-blender/references/animations.md#idealized-hinged-pore-gate-opening)
optimizes methane with `molecule` and `smiles="C"`, builds the gate animation, then renders it
with `animate=true`. The aperture lies in the XY plane and the pore depth runs along Z.
The default camera has `direction=[0,0,1]` and `up=[0,1,0]`: it sits on the +Z side looking
toward −Z, with +Y up on screen. The rigid guest approaches from the upper-left/front of the
aperture, then enters along the depth while the in-plane rhombus opens into a square.
All framework bar lengths remain constant.

## MCP tools

`environment_status`, `inspect_structure`, `analyze_framework`, `create_framework_scene`,
`create_molecule_scene`, `create_layer_scene`, `set_view`, `compose_schematic`,
`create_diffusion_animation`, `create_reaction_animation`, `create_gate_open_animation`, and
`render_figure`.

All tools expose typed schemas. They do not accept arbitrary Python code or remote shell
commands. Third-party library output is redirected away from MCP's protocol stdout.

## Architecture

```text
Agent request / CLI JSON
          │
          ├── CIF ── ASE + Gemmi ── AuToGraFS ── analysis JSON
          ├── molecule ── RDKit conformers + MMFF94s/UFF
          └── layer model ── ASE honeycomb basis / stacking
                                  │
                          independent scene JSON
                                  │
                 camera / composition / authored keyframes
                                  │
                    Blender process + Cycles renderer
                                  │
                    PNG / BLEND / GIF / audit manifest
```

The periodic edge's integer image shift is part of its identity. Node positions and bond
vectors share the same crystallographic image convention. For the PyPI AuToGraFS 3.2.0 API,
the geometry adapter reconstructs the engine's unit image convention and requires an exact
quotient-graph cross-check before producing a topology scene.

Planar-layer display unwrapping changes periodic images only along nonperiodic directions;
tests verify that bond vectors remain unchanged. Camera changes have their own geometry hash
check. The `.blend` embeds the scene JSON and provenance as well as editable objects and keyframes.

## Scientific boundaries and limitations

- AuToGraFS identification returns **signature-based candidates**, not a graph-isomorphism proof.
  `exact` is the upstream match tier, not a claim of unique experimental topology.
- Disorder and partial occupancy require an explicit ordered model. The tool does not silently repair a CIF.
- Atomic display bonds use covalent-radius cutoffs; CIF bond orders are not inferred. Topology
  deconstruction uses AuToGraFS's separate bond perception and conventions.
- Finite supercell pictures retain only edges whose endpoints are displayed. Boundary fragments
  can be visible; a finite illustration is not a chemically terminated nanoparticle.
- A four-connected node is not automatically tetrahedral. Polyhedra follow connection directions.
  Infinite rod SBUs are reported but their points-of-extension polyhedral rendering is not implemented.
- MMFF94s/UFF may lack parameters for metals or unusual chemistry. Missing parameters or
  nonconverged conformers cause an error. Force-field energies are local molecular energies,
  not free energies, adsorption energies or barriers.
- XYZ lacks bond orders: use `optimize=false` for unchanged coordinates or provide MOL/SDF/SMILES.
  PDB molecular connectivity may be perceived by RDKit.
- Authored pore motion preserves guest geometry but does not check steric clearance. There is
  no MD engine, diffusion coefficient calculation, or full MD-trajectory importer in this release.
- Interface reaction snapshots preserve atom identities but do not establish a mechanism,
  transition state, oxidation state, electron transfer or activation energy.
- Gate opening is an idealized hinged pore with a rigid guest and constant bar lengths. It
  does not deform an uploaded CIF or establish a validated material mechanism, energy barrier
  or physical timescale. Guest motion and pore opening are explicitly authored together.
- Graphene/h-BN dimensions and layer distances are explicit model parameters; the layer builder
  does not relax the slab. Publication figures still need application-specific scientific review.

## Reproduce and test

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src scripts tests
.venv/bin/python scripts/create_examples.py --output output/my-gallery --render --animations --samples 64
```

Use a new gallery directory. `--resume` skips completed render directories after preparation.
The complete example run is more expensive than the unit tests; animations render every frame.
On macOS the host sandbox may block Blender's Metal initialization even for a CPU Cycles render;
run the authorized render with desktop permissions if necessary.

Tests cover nonorthogonal direct/reciprocal views, periodic graph contraction, planar polygons,
layer image seams, immutable source files, RDKit convergence, molecule export, reaction atom
conservation and an actual MCP stdio client. AuToGraFS integration tests round-trip MOF and COF CIFs.
See [validation details](docs/validation.md) for actual tested versions and render checks.

## ChemBlender reference, licensing and citation

ChemBlender 2.0 was inspected as a reference for molecular/crystal representation, supercell
controls, polyhedra, viewing directions and rendering workflow. **Its code, Geometry Nodes
libraries, assets, materials and default render settings are not bundled or copied.**
This implementation uses its own scene representation, geometry generation, three-light studio
and agent interface. See [sources and comparison](docs/sources.md).

Project code is distributed under the [MIT license](LICENSE). Dependencies retain their own
licenses. Please cite the underlying scientific software when used for research, especially
[AuToGraFS, Addicoat et al., 2014](https://doi.org/10.1021/jp507643v),
[RDKit](https://www.rdkit.org/), [ASE](https://ase-lib.org/) and [Blender](https://www.blender.org/).
