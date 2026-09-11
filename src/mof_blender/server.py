"""Small stdio MCP surface shared by Codex, Claude Code and other MCP hosts."""
from __future__ import annotations

import contextlib
import sys

from mcp.server.fastmcp import FastMCP

from . import __version__
from .animation import diffusion_scene, gate_open_scene, reaction_scene
from .layers import layer_scene
from .render import doctor, render_scene
from .scene import compose_scene, make_scene, molecule_scene
from .structures import inspect_cif
from .topology import analyze_cif
from .views import change_view

mcp = FastMCP("mof-blender", instructions=(
    "Analyze CIFs with AuToGraFS and render molecular/framework geometry with Blender. "
    "Preserve sources, distinguish net candidates from proven assignments, and use absolute paths. "
    "Generate scene JSON first, then render. Camera changes preserve geometry. "
    "Read the mof-blender skill for supported natural-language camera syntax and scientific boundaries."
))


def quiet(function, **kwargs):
    # Third-party scientific libraries may print banners. stdout belongs to MCP.
    with contextlib.redirect_stdout(sys.stderr):
        return function(**kwargs)


@mcp.tool()
def environment_status() -> dict:
    """Check installed scientific dependencies and the Blender executable."""
    return {"version": __version__, **doctor()}


@mcp.tool()
def inspect_structure(path: str, block: str | None = None) -> dict:
    """Inspect CIF data blocks, occupancy and disorder without changing the input."""
    result = inspect_cif(path, block)
    result.pop("_block_text", None)
    return result


@mcp.tool()
def analyze_framework(path: str, output: str, block: str | None = None,
                      identify: bool = True, bond_scale: float = 1.15) -> dict:
    """CIF -> AuToGraFS units/periodic graph/net candidates and immutable analysis JSON.

    identify=False prepares an atomic picture without topology identification.
    Ordered CIFs only. Errors remain errors; no silent topology fallback.
    """
    return quiet(analyze_cif, path=path, output=output, block=block, identify=identify,
                 bond_scale=bond_scale)


@mcp.tool()
def create_framework_scene(analysis: str, output: str, representation: str = "polyhedra",
                           repeat: list[int] | None = None, preset: str = "paper",
                           view: str | None = None, transparent: bool = True,
                           width: int = 1400, height: int = 1100, node_scale: float = 0.22,
                           edge_radius: float = 0.10, atom_scale: float = 0.34,
                           bond_radius: float = 0.085, show_hydrogen: bool = False,
                           node_color: str | None = None, edge_color: str | None = None) -> dict:
    """Create editable scene JSON. Representations: polyhedra, net, hybrid, ball-stick,
    sticks, spacefill. Presets: paper, porcelain, midnight. n-connected nodes use
    physical connection directions; coplanar nodes remain polygons. Does not render yet.
    """
    repeat = repeat or [2, 2, 2]
    return quiet(make_scene, **locals())


@mcp.tool()
def create_molecule_scene(output: str, source: str | None = None, smiles: str | None = None,
                          representation: str = "ball-stick", preset: str = "paper",
                          transparent: bool = True, width: int = 1200, height: int = 900,
                          view: str | None = None, optimize: bool = True, conformers: int = 8) -> dict:
    """Create a scene from XYZ/MOL/SDF/PDB or SMILES. SMILES coordinates are generated
    conformers, not experimental structures. Optimize with MMFF94s or UFF by default;
    exports optimized SDF/XYZ and convergence metadata. XYZ needs optimize=False.
    Choose ball-stick, sticks or spacefill.
    """
    return quiet(molecule_scene, **locals())


@mcp.tool()
def set_view(scene: str, output: str, instruction: str | None = None,
             direction: list[float] | None = None, kind: str = "uvw",
             projection: str | None = None) -> dict:
    """Change only the camera. Examples: 沿a轴看, 沿[1 1 0]看, 看(1 0 0)晶面,
    俯视, 向右旋转30度, 绕c轴旋转30度, 反方向, 正交, 透视. For other wording the
    agent translates intent into an explicit uvw/hkl/cartesian vector. Returns geometry hash.
    """
    return change_view(**locals())


@mcp.tool()
def compose_schematic(output: str, components: list[dict], arrows: list[dict] | None = None,
                       preset: str = "paper", view: str = "俯视", transparent: bool = True,
                       width: int = 1600, height: int = 1000) -> dict:
    """Compose scenes with user-defined placements. Component keys: scene (path), name,
    translate [x,y,z], scale. Arrow keys: start, end, radius, color. No reaction inference.
    """
    return compose_scene(**locals())


@mcp.tool()
def render_figure(scene: str, output_dir: str, samples: int = 64,
                  blender: str | None = None, timeout: int = 600, animate: bool = False) -> dict:
    """Render through Blender Cycles in a fresh process; save PNG + editable .blend + audit.
    output_dir must be new. Typical runtime is tens of seconds. Use samples=128+ for finals.
    """
    return render_scene(**locals())


@mcp.tool()
def create_diffusion_animation(host_scene: str, guest_scene: str, output: str,
                                waypoints: list[list[float]], frames: int = 48,
                                fps: int = 12, show_path: bool = True) -> dict:
    """Move a rigid molecular guest along Cartesian waypoints in a framework. Creates
    editable keyframes, not an MD simulation. No rate, barrier or steric clearance is inferred.
    Render with animate=True to export GIF and PNG frames in addition to the .blend.
    """
    return diffusion_scene(**locals())


@mcp.tool()
def create_reaction_animation(surface_scene: str, output: str, snapshots: list[dict],
                               frames: int = 48, fps: int = 12) -> dict:
    """Create an explicit interface-reaction storyboard. Each snapshot has frame, label,
    atoms [{id,element,position}], and bonds [[id,id]]. Atom ids/elements must be conserved.
    Coordinates, bonds and mechanism are supplied by the user/agent, never inferred as evidence.
    """
    return reaction_scene(**locals())


@mcp.tool()
def create_layer_scene(output: str, material: str = "graphene", repeat: list[int] | None = None,
                        layers: int = 1, stacking: str = "AB", lattice_a: float | None = None,
                        interlayer: float = 3.35, representation: str = "ball-stick",
                        preset: str = "paper", view: str = "俯视", transparent: bool = False,
                        width: int = 1400, height: int = 1000) -> dict:
    """Generate idealized graphene or hbn sheets, optionally stacked AA/AB. Coordinates
    are model values, not a relaxed structure. Returns scene JSON, CIF and XYZ.
    For inclined views create the scene, then use set_view with a Cartesian direction.
    """
    repeat = repeat or [8, 8, 1]
    return layer_scene(**locals())


@mcp.tool()
def create_gate_open_animation(guest_scene: str, output: str, closed_angle: float = 24.0,
                                open_angle: float = 90.0, edge_length: float = 6.0,
                                depth: float = 2.8, frames: int = 48, fps: int = 12,
                                preset: str = "porcelain", width: int = 1000, height: int = 800) -> dict:
    """Create guest-induced gate-opening of an idealized hinged MOF pore. Fixed strut
    lengths and changing angle open a rhombic pore as an optimized guest enters.
    Does not deform an experimental CIF or calculate the material's mechanism or energy.
    """
    return gate_open_scene(**locals())


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
