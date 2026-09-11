"""Idealized graphene and h-BN layers as auditable periodic model scenes."""
from __future__ import annotations

from pathlib import Path

from .io import InputError, digest, write_json
from .scene import _atomic_objects, new_scene
from .structures import atom_payload
from .views import interpret_view


def layer_scene(output, material="graphene", repeat=(8, 8, 1), layers=1, stacking="AB",
                lattice_a=None, interlayer=3.35, representation="ball-stick", preset="paper",
                view="俯视", transparent=True, width=1400, height=1000):
    from ase.build import graphene
    from ase.io import write

    if material not in {"graphene", "hbn"}:
        raise InputError("Supported generated layers: graphene, hbn")
    if representation not in {"ball-stick", "sticks", "spacefill"}:
        raise InputError("Layers support ball-stick, sticks or spacefill")
    if len(repeat) != 3 or repeat[2] != 1:
        raise InputError("Use repeat=[nx, ny, 1]; control layer count with layers")
    if not 1 <= layers <= 8 or stacking not in {"AA", "AB"}:
        raise InputError("layers must be 1–8 and stacking AA or AB")
    a = float(lattice_a if lattice_a is not None else (2.46 if material == "graphene" else 2.50))
    if not 1 < a < 10 or not 1 < interlayer < 20:
        raise InputError("Invalid lattice_a or interlayer distance")
    base = graphene(formula="C2" if material == "graphene" else "BN", a=a, vacuum=6)
    base.positions[:, 2] = 0
    basis_shift = base.positions[1] - base.positions[0]
    structure = base.copy()
    for i in range(1, layers):
        layer = base.copy()
        layer.positions += (basis_shift * (i % 2) if stacking == "AB" else 0)
        layer.positions[:, 2] += i * interlayer
        structure += layer
    structure.set_cell([base.cell[0], base.cell[1], [0, 0, 12 + (layers - 1) * interlayer]])
    structure.pbc = [True, True, False]
    scene = new_scene(structure.cell, preset, transparent, width, height)
    scene["provenance"] = {"type": "generated idealized 2D model", "material": material,
                           "lattice_a_angstrom": a, "layers": layers, "stacking": stacking,
                           "interlayer_angstrom": interlayer if layers > 1 else None,
                           "pbc": [True, True, False], "repeat": list(repeat),
                           "coordinate_origin": "ASE honeycomb basis; no structural relaxation",
                           "representation": representation}
    _atomic_objects(scene, atom_payload(structure), repeat, representation, 0.34, 0.065, True)
    # Give each sheet its own palette while keeping every atom's element metadata.
    if layers > 1:
        layer_colors = ["#426B86", "#BA8D60"]
        for obj in scene["objects"]:
            z = obj["position"][2] if obj["type"] == "sphere" else (obj["start"][2] + obj["end"][2]) / 2
            layer_index = round(z / interlayer)
            obj["color"] = layer_colors[layer_index % 2]
            obj["layer"] = layer_index
        scene["provenance"]["colors"] = "layer colors; not element colors"
    scene["camera"] = interpret_view(view, scene["cell"])
    scene["geometry_sha256"] = digest(scene["objects"])
    output = Path(output).expanduser().resolve()
    cif, xyz = output.with_suffix(".cif"), output.with_suffix(".xyz")
    if cif.exists() or xyz.exists():
        raise FileExistsError("Layer coordinate sidecars already exist")
    result = {"scene": write_json(output, scene), "objects": len(scene["objects"])}
    # The CIF stores a 3D vacuum cell; JSON records that z is nonperiodic in the illustration.
    display_structure = structure.repeat(repeat)
    write(cif, display_structure)
    write(xyz, display_structure, format="xyz")
    result.update(cif=str(cif), xyz=str(xyz))
    return result
