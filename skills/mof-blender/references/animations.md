# Animation recipes

All coordinates and translation waypoints are Cartesian angstroms in the scene's original
coordinate system. Group scaling is an illustrative composition choice, recorded separately.
The example generator includes three schematic animations among its 16 examples: pore
diffusion, an interface reaction, and idealized hinged-pore gate opening. Frame counts and
`fps` control presentation timing, not physical simulation time.

## Diffusion in a pore

1. Prepare a host scene and an RDKit-optimized molecular guest scene.
2. Choose path waypoints inside the intended channel using the actual geometry.
3. Call `create_diffusion_animation` with both scene paths, a new output JSON and waypoints.
4. Call `render_figure` with `animate=True`, a new output directory, and sufficient timeout.

Example arguments:

```json
{
  "host_scene": "/project/host.scene.json",
  "guest_scene": "/project/co2.scene.json",
  "output": "/project/diffusion.scene.json",
  "waypoints": [[6.4, 6.4, 1.0], [6.4, 6.4, 12.0], [6.4, 6.4, 24.0]],
  "frames": 48,
  "fps": 12
}
```

These are absolute centers for the guest. Its internal geometry is unchanged during motion.
The built-in path does not check steric clearance or simulate thermal motion. If a physically
realistic trajectory is needed, use externally supplied trajectory coordinates; do not relabel
an authored path as MD. This version does not yet expose a full MD trajectory importer.

## Idealized hinged-pore gate opening

Use CLI `gate-open` or MCP `create_gate_open_animation` to build an idealized hinged pore
around an optimized molecular guest. The pore is generated from explicit geometric parameters;
**it is not a deformation of an uploaded CIF or a validated material mechanism**. The guest
path and opening schedule are authored together, without computing a causal response, energy
barrier, physical timescale or steric clearance.

The aperture lies in the XY plane and the pore depth runs along Z. The default camera is
front-on from +Z: `direction=[0,0,1]`, `up=[0,1,0]`. Since direction points from the target
toward the camera, this camera looks toward −Z with +Y up on screen. The guest approaches
from the upper-left/front of the aperture (−X, +Y, on the +Z side), then enters along the
depth while the in-plane rhombus opens into a square at `open_angle=90`. Each aperture bar
keeps length `edge_length`; the bars along the depth keep length `depth`. The guest's internal
geometry stays rigid throughout the animation.

Run the following from the repository root using the existing environment. Save the three
JSON requests below in the working directory and choose a fresh output path for each revision.
No separate host scene or CIF is needed.

1. Optimize methane and retain the reusable molecular files. Save `methane.json`:

```json
{
  "smiles": "C",
  "output": "output/gate-demo/methane.scene.json",
  "optimize": true,
  "conformers": 8,
  "representation": "ball-stick",
  "preset": "paper"
}
```

```bash
.venv/bin/python scripts/run.py call molecule --args-file methane.json
```

The result includes `methane.scene.json`, `methane.scene.sdf`, `methane.scene.xyz`, and
convergence metadata. Keep these together. The coordinates are a generated RDKit force-field
minimum, not experimental coordinates or a demonstrated global minimum.

2. Build the gate-opening scene. Save `gate-open.json`:

```json
{
  "guest_scene": "output/gate-demo/methane.scene.json",
  "output": "output/gate-demo/gate-open.scene.json",
  "frames": 48,
  "fps": 12,
  "closed_angle": 24,
  "open_angle": 90,
  "edge_length": 6,
  "depth": 2.8
}
```

```bash
.venv/bin/python scripts/run.py call gate-open --args-file gate-open.json
```

The angles are between the two in-plane bars, in degrees. Lengths are in Å. This recipe
uses 6 Å aperture bars and 2.8 Å depth; only the hinge angle changes from 24° to 90°.

3. Render an animated preview. Save `gate-render.json`:

```json
{
  "scene": "output/gate-demo/gate-open.scene.json",
  "output_dir": "output/gate-demo/render-v1",
  "animate": true,
  "samples": 64,
  "timeout": 1800
}
```

```bash
.venv/bin/python scripts/run.py call render --args-file gate-render.json
```

`output_dir` must be new. A successful animated render produces an editable `scene.blend`,
`render.png`, `animation.gif`, individual PNG frames, and an audit manifest. Check the
manifest and inspect the images before claiming rendering succeeded.

The CLI also accepts MCP long-name aliases: replace `molecule` with `create_molecule_scene`,
`gate-open` with `create_gate_open_animation`, and `render` with `render_figure`. These are
alternative names for the same calls; execute each stage once per output revision. With MCP,
call those three long-name tools in order with the corresponding JSON arguments above.

Natural-language requests:

> 优化甲烷，让它从理想化铰接孔口的左上方、孔口前侧接近，再沿深度进入；菱形孔同时展开为
> 正方形，保持杆长和客体几何不变。从 +Z 正对孔口、以 +Y 为屏幕上方，制作示意动画。

> Optimize methane and animate an idealized hinged pore opening from a rhombus into a
> square as the rigid guest approaches from the upper-left/front and enters along the depth.
> Keep bar lengths fixed; view front-on from +Z with +Y up and label the motion schematic.

## Interface reaction

Prepare a support scene, then supply snapshots. Each snapshot contains `frame`, an optional
`label`, `atoms` with stable `id`, `element`, `position`, and `bonds` as id pairs. Start at frame
1 and end at the requested final frame. Atom identities and element counts must match.

```json
{
  "surface_scene": "/project/support.scene.json",
  "output": "/project/reaction.scene.json",
  "frames": 24,
  "fps": 12,
  "snapshots": [
    {"frame": 1, "label": "approach", "atoms": [
      {"id": "O", "element": "O", "position": [0, 0, 3]},
      {"id": "H", "element": "H", "position": [0, 0, 5]}
    ], "bonds": []},
    {"frame": 24, "label": "illustrative bond", "atoms": [
      {"id": "O", "element": "O", "position": [0, 0, 3]},
      {"id": "H", "element": "H", "position": [0, 0, 3.98]}
    ], "bonds": [["O", "H"]]}
  ]
}
```

Positions interpolate linearly; bond visibility changes at the explicitly supplied frame.
Only the author's supplied atoms participate in the animated reaction. A surface atom that
participates must be removed from the static illustration and included with its stable id in
every snapshot, avoiding duplicate atoms. Charge, spin, energy and transition-state validity
are not computed by this drawing tool.

## Composition

`compose_schematic` combines existing scene files with explicit `translate`, `scale` and
optional arrows. Each component is `{scene, name, translate:[x,y,z], scale:1}`; each arrow is
`{start:[x,y,z], end:[x,y,z], radius:0.12, color:"#758DA4"}`. The shared camera controls the whole
scene. Scientific labels are best overlaid in a document/vector layout after rendering.
