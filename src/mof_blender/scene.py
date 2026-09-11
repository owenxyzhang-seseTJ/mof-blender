"""Build inspectable Blender-independent geometry and style recipes."""
from __future__ import annotations

import copy
import itertools

import numpy as np
from scipy.spatial import ConvexHull

from .graph import adjacency, canonical, unwrap_nonperiodic_axes
from .io import InputError, check_kind, digest, read_json, write_json
from .structures import read_molecule
from .views import camera_default, interpret_view, unit

PRESETS = {
    "paper": {"background": "#FFFFFF", "node": "#348B94", "edge": "#728491",
              "accent": "#DCAC70", "roughness": 0.38, "metallic": 0.0,
              "world_strength": 0.65, "exposure": 0.0},
    "porcelain": {"background": "#F1F2F0", "node": "#77AEB9", "edge": "#B09A7C",
                  "accent": "#D9A475", "roughness": 0.27, "metallic": 0.04,
                  "world_strength": 0.55, "exposure": 0.0},
    "midnight": {"background": "#101E31", "node": "#47C7BD", "edge": "#C8A777",
                 "accent": "#9CAFE5", "roughness": 0.3, "metallic": 0.18,
                 "world_strength": 0.35, "exposure": 0.1},
}
ELEMENT_COLORS = {
    "H": "#E3E8EE", "C": "#4C6074", "N": "#547FD0", "O": "#D65B69",
    "S": "#DAB95C", "P": "#DCA05A", "F": "#75B792", "Cl": "#72B28B",
    "Br": "#A47764", "I": "#9284B9", "B": "#E2B6A0", "Si": "#C3AB81",
    "Zn": "#89B4BF", "Cu": "#BE895E", "Zr": "#90B9AD", "Fe": "#C88B62",
    "Co": "#8A8DC5", "Ni": "#76AC9B", "Al": "#AAAFC3", "Ti": "#9FA3B8",
}


def _color(text):
    if not isinstance(text, str) or len(text) != 7 or not text.startswith("#"):
        raise InputError("Colors must be #RRGGBB strings")
    try:
        int(text[1:], 16)
    except ValueError as exc:
        raise InputError("Invalid hex color") from exc
    return text


def _element_color(element, scene):
    if element == "C" and scene["style"]["preset"] == "midnight":
        return "#A7C4D3"
    return ELEMENT_COLORS.get(element, "#96A3B7")


def new_scene(cell, preset="paper", transparent=True, width=1400, height=1100):
    if preset not in PRESETS:
        raise InputError(f"Unknown preset; choose {list(PRESETS)}")
    if not 64 <= width <= 8192 or not 64 <= height <= 8192:
        raise InputError("Image dimensions must be 64–8192 pixels")
    return {"schema": "mof-blender/scene/1", "cell": np.asarray(cell).tolist(),
            "camera": camera_default(), "style": {"preset": preset, **PRESETS[preset]},
            "render": {"width": int(width), "height": int(height), "transparent": transparent,
                       "samples": 64, "engine": "CYCLES"},
            "objects": [], "provenance": {}, "history": []}


def sphere(scene, position, radius, color, group, **metadata):
    scene["objects"].append({"type": "sphere", "position": np.asarray(position).tolist(),
                             "radius": float(radius), "color": _color(color),
                             "group": group, **metadata})


def cylinder(scene, start, end, radius, color, group, **metadata):
    if np.linalg.norm(np.asarray(end) - start) < 1e-9:
        return
    scene["objects"].append({"type": "cylinder", "start": np.asarray(start).tolist(),
                             "end": np.asarray(end).tolist(), "radius": float(radius),
                             "color": _color(color), "group": group, **metadata})


def polyhedron(points):
    """Convex vertex figure; planar nodes remain polygons with no fake apex."""
    points = np.asarray(points, dtype=float)
    points = np.unique(np.round(points, 8), axis=0)
    centered = points - points.mean(axis=0)
    _, singular, basis = np.linalg.svd(centered, full_matrices=False)
    rank = int(sum(singular > max(singular[0] * 1e-5, 1e-8))) if len(singular) else 0
    if rank < 2 or len(points) < 3:
        return points.tolist(), [], "linear"
    if rank == 2:
        projected = centered @ basis[:2].T
        perimeter = ConvexHull(projected).vertices.tolist()
        return points.tolist(), [perimeter], "planar_polygon"
    hull = ConvexHull(points)
    faces = []
    for triangle, equation in zip(hull.simplices, hull.equations):
        a, b, c = triangle.tolist()
        if np.dot(np.cross(points[b] - points[a], points[c] - points[a]), equation[:3]) < 0:
            b, c = c, b
        faces.append([a, b, c])
    return points.tolist(), faces, "convex_polyhedron"


def _repeats(repeat):
    if len(repeat) != 3 or any(isinstance(x, bool) or int(x) != x or not 1 <= x <= 12
                               for x in repeat):
        raise InputError("repeat must contain three integers between 1 and 12")
    return [tuple(s) for s in itertools.product(*(range(int(n)) for n in repeat))]


def _topology_objects(scene, graph, repeat, representation, node_scale, edge_radius):
    graph, image_changes = unwrap_nonperiodic_axes(graph)
    scene["provenance"]["topology_display_image_changes"] = image_changes
    cell = np.asarray(scene["cell"])
    nodes = {int(n["id"]): n for n in graph["nodes"]}
    edges = {canonical(e["a"], e["b"], e["shift"]) for e in graph["edges"]}
    neighbors = adjacency(edges)
    translations = _repeats(repeat)
    copies = {(i, t): (np.asarray(n["fractional"]) + t) @ cell
              for i, n in nodes.items() for t in translations}
    kinds = {}
    polyhedra = {}
    for i, node in nodes.items():
        center = np.asarray(node["fractional"])
        vectors = [(np.asarray(nodes[j]["fractional"]) + shift - center) @ cell
                   for j, shift in neighbors[i]]
        if not vectors:
            continue
        shortest = min(np.linalg.norm(x) for x in vectors)
        # The actual cut directions avoid regularizing a distorted coordination sphere.
        ports = [(np.asarray(p) - center) @ cell for p in node.get("ports_fractional", [])]
        directions = ports if len(ports) == len(vectors) else vectors
        directions = [unit(x) * shortest * node_scale for x in directions]
        vertices, faces, kind = polyhedron(directions)
        kinds[i] = kind
        polyhedra[i] = (np.asarray(vertices), faces, shortest)
    for (i, t), position in copies.items():
        color = scene["style"]["node"] if nodes[i].get("kind") == "node" else scene["style"]["accent"]
        if representation == "net" or i not in polyhedra:
            radius = max(edge_radius * 2.2, polyhedra.get(i, (None, None, 3))[2] * node_scale * 0.4)
            sphere(scene, position, radius, color, "topology_nodes", unit_id=i, image=list(t))
            continue
        vertices, faces, shortest = polyhedra[i]
        if not faces:
            sphere(scene, position, shortest * node_scale * 0.28, color, "topology_nodes")
            continue
        vertices = vertices + position
        scene["objects"].append({"type": "mesh", "vertices": vertices.tolist(),
                                 "faces": faces, "color": color, "group": "topology_nodes",
                                 "unit_id": i, "image": list(t), "degree": len(neighbors[i]),
                                 "geometry": kinds[i], "opacity": 0.32 if representation == "hybrid" else 1.0})
        # Only true hull ridges get outlines; triangulation diagonals are suppressed.
        face_edges = {}
        for face in faces:
            normal = unit(np.cross(vertices[face[1]] - vertices[face[0]],
                                   vertices[face[2]] - vertices[face[0]]))
            for a, b in zip(face, face[1:] + face[:1]):
                face_edges.setdefault(tuple(sorted((a, b))), []).append(normal)
        for (a, b), normals in face_edges.items():
            if len(normals) == 2 and abs(np.dot(*normals)) > 0.9999:
                continue
            cylinder(scene, vertices[a], vertices[b], edge_radius * 0.34,
                     color, "polyhedron_outlines")
    for a, b, shift in sorted(edges):
        for t in translations:
            bt = tuple(np.asarray(t) + shift)
            if (b, bt) in copies:
                cylinder(scene, copies[a, t], copies[b, bt], edge_radius,
                         scene["style"]["edge"], "topology_edges")
    scene["provenance"]["node_geometry"] = {str(k): v for k, v in kinds.items()}
    scene["provenance"]["node_degree_basis"] = "full periodic graph before finite supercell cropping"
    scene["provenance"]["node_shape"] = "normalized physical connection directions, convex hull"


def _atomic_objects(scene, structure, repeat, representation, atom_scale, bond_radius, show_hydrogen):
    from ase.data import atomic_numbers, covalent_radii, vdw_radii

    structure = copy.deepcopy(structure)
    cell = np.asarray(structure["cell"])
    if any(structure["pbc"]):
        graph = {"nodes": [{"id": a["id"], "fractional": (np.asarray(a["position"]) @ np.linalg.inv(cell)).tolist()}
                           for a in structure["atoms"]], "edges": structure["bonds"]}
        graph, image_changes = unwrap_nonperiodic_axes(graph)
        scene["provenance"]["atomic_display_image_changes"] = image_changes
        for atom, node in zip(structure["atoms"], graph["nodes"]):
            atom["position"] = (np.asarray(node["fractional"]) @ cell).tolist()
        structure["bonds"] = graph["edges"]
    atoms = {int(a["id"]): a for a in structure["atoms"]
             if show_hydrogen or a["element"] != "H"}
    if not any(structure["pbc"]) and list(repeat) != [1, 1, 1]:
        raise InputError("Nonperiodic molecules cannot be repeated as a crystal")
    cell = np.asarray(structure["cell"])
    translations = _repeats(repeat)
    positions = {(i, t): np.asarray(a["position"]) + np.asarray(t) @ cell
                 for i, a in atoms.items() for t in translations}
    for (i, t), pos in positions.items():
        element = atoms[i]["element"]
        number = atomic_numbers[element]
        radius = covalent_radii[number] * atom_scale
        if representation == "spacefill":
            radius = vdw_radii[number]
            if not np.isfinite(radius):
                radius = covalent_radii[number] * 1.7
        elif representation == "sticks":
            radius = bond_radius
        sphere(scene, pos, radius, _element_color(element, scene), "atoms",
               element=element, atom_id=i, image=list(t))
    if representation == "spacefill":
        return
    for bond in structure["bonds"]:
        a, b = int(bond["a"]), int(bond["b"])
        if a not in atoms or b not in atoms:
            continue
        for t in translations:
            bt = tuple(np.asarray(t) + bond["shift"])
            if (b, bt) not in positions:
                continue
            p, q = positions[a, t], positions[b, bt]
            # Preserve multiple-bond information for molecular file/SMILES input.
            # Aromatic 1.5 bonds use one cylinder; do not draw every aromatic bond as double.
            order = bond.get("order", 1)
            count = 1 if order == 1.5 else round(order)
            count = max(1, min(count, 3))
            axis = unit(q - p)
            ref = [0, 0, 1] if abs(axis[2]) < 0.9 else [0, 1, 0]
            side = unit(np.cross(axis, ref))
            for k in range(count):
                offset = side * (k - (count - 1) / 2) * bond_radius * 2.7
                midpoint = (p + q) / 2 + offset
                cylinder(scene, p + offset, midpoint, bond_radius,
                         _element_color(atoms[a]["element"], scene), "bonds")
                cylinder(scene, midpoint, q + offset, bond_radius,
                         _element_color(atoms[b]["element"], scene), "bonds")


def make_scene(analysis, output, representation="polyhedra", repeat=(2, 2, 2),
               preset="paper", view=None, transparent=True, width=1400, height=1100,
               node_scale=0.22, edge_radius=0.10, atom_scale=0.34, bond_radius=0.085,
               show_hydrogen=False, node_color=None, edge_color=None):
    data = read_json(analysis)
    check_kind(data, "analysis")
    if representation not in {"polyhedra", "net", "hybrid", "ball-stick", "sticks", "spacefill"}:
        raise InputError("Unknown representation")
    if not 0.02 <= node_scale <= 0.45 or not 0.005 <= edge_radius <= 1:
        raise InputError("node_scale must be 0.02–0.45; edge_radius must be 0.005–1 angstrom")
    if not 0.03 <= atom_scale <= 1.5 or not 0.005 <= bond_radius <= 1:
        raise InputError("Invalid atom_scale or bond_radius")
    translations = _repeats(repeat)
    scene = new_scene(data["structure"]["cell"], preset, transparent, width, height)
    scene["provenance"] = {"input": data["input"], "analysis_sha256": digest(data),
                           "representation": representation, "repeat": list(repeat),
                           "net_candidates": data["topology"].get("candidates", []),
                           "finite_crop": "only edges with both endpoints inside retained cells"}
    if node_color:
        scene["style"]["node"] = _color(node_color)
    if edge_color:
        scene["style"]["edge"] = _color(edge_color)
    if representation in {"polyhedra", "net", "hybrid"}:
        graph = data.get("display_graph")
        if not graph:
            raise InputError("No finite-node topology graph. Use an atomic representation or inspect analysis status.")
        if len(graph["nodes"]) * len(translations) > 5000:
            raise InputError("Too many topology nodes; reduce the supercell")
        _topology_objects(scene, graph, repeat, representation, node_scale, edge_radius)
    if representation in {"ball-stick", "sticks", "spacefill", "hybrid"}:
        if len(data["structure"]["atoms"]) * len(translations) > 25000:
            raise InputError("More than 25000 atoms; reduce repeat or use topology mode")
        _atomic_objects(scene, data["structure"], repeat, representation,
                        atom_scale, bond_radius, show_hydrogen)
    if view:
        scene["camera"] = interpret_view(view, scene["cell"])
    scene["geometry_sha256"] = digest(scene["objects"])
    return {"scene": write_json(output, scene), "objects": len(scene["objects"]),
            "geometry_sha256": scene["geometry_sha256"]}


def molecule_scene(output, source=None, smiles=None, representation="ball-stick", preset="paper",
                  transparent=True, width=1200, height=900, view=None, optimize=True, conformers=8):
    if representation not in {"ball-stick", "sticks", "spacefill"}:
        raise InputError("Molecules support ball-stick, sticks or spacefill")
    molecule = read_molecule(source, smiles, optimize, conformers)
    scene = new_scene(molecule["cell"], preset, transparent, width, height)
    scene["provenance"] = {"input": molecule["source"], "representation": representation,
                           "bond_method": molecule["bond_method"]}
    _atomic_objects(scene, molecule, (1, 1, 1), representation, 0.45, 0.115, True)
    if view:
        scene["camera"] = interpret_view(view, scene["cell"])
    scene["geometry_sha256"] = digest(scene["objects"])
    from pathlib import Path
    path = Path(output).expanduser().resolve()
    sdf, xyz = path.with_suffix(".sdf"), path.with_suffix(".xyz")
    if sdf.exists() or xyz.exists():
        raise FileExistsError("Molecule sidecars already exist; choose a new output name")
    result = {"scene": write_json(output, scene), "objects": len(scene["objects"]),
              "optimization": molecule["source"].get("optimization", {"performed": False})}
    if "mol_block" in molecule:
        with sdf.open("x", encoding="utf-8") as handle:
            handle.write(molecule["mol_block"] + "\n$$$$\n")
        result["sdf"] = str(sdf)
    with xyz.open("x", encoding="utf-8") as handle:
        handle.write(f"{len(molecule['atoms'])}\nMOF Blender molecular coordinates; see scene provenance\n")
        for atom in molecule["atoms"]:
            handle.write(atom["element"] + " " + " ".join(f"{v:.9f}" for v in atom["position"]) + "\n")
    result["xyz"] = str(xyz)
    return result


def compose_scene(output, components, arrows=None, preset="paper", view="俯视",
                  transparent=True, width=1600, height=1000):
    """Combine explicit scene placements and arrows; chemistry remains user-specified."""
    scene = new_scene(np.eye(3), preset, transparent, width, height)
    scene["provenance"] = {"type": "schematic composition", "components": components,
                           "meaning": "placements and arrows are illustrative, not reaction evidence"}
    for component in components:
        child = read_json(component["scene"])
        check_kind(child, "scene")
        shift = np.asarray(component.get("translate", [0, 0, 0]), dtype=float)
        scale = float(component.get("scale", 1))
        if shift.shape != (3,) or not np.isfinite(shift).all() or not 0 < scale <= 100:
            raise InputError("Invalid composition transform")
        for original in child["objects"]:
            obj = copy.deepcopy(original)
            for key in ("position", "start", "end", "vertices"):
                if key in obj:
                    obj[key] = (np.asarray(obj[key]) * scale + shift).tolist()
            if "radius" in obj:
                obj["radius"] *= scale
            obj["group"] = component.get("name", "component") + "/" + obj.get("group", "objects")
            scene["objects"].append(obj)
    for arrow in arrows or []:
        cylinder(scene, arrow["start"], arrow["end"], arrow.get("radius", 0.12),
                 arrow.get("color", "#758DA4"), "arrows", arrow=True)
    scene["camera"] = interpret_view(view, scene["cell"])
    scene["geometry_sha256"] = digest(scene["objects"])
    return {"scene": write_json(output, scene), "objects": len(scene["objects"])}
