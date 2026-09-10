"""Authored molecular motion and reaction storyboards, separate from MD evidence."""
from __future__ import annotations

import copy
from itertools import pairwise

import numpy as np

from .io import InputError, check_kind, digest, read_json, write_json
from .scene import ELEMENT_COLORS, cylinder, new_scene, sphere


def _animation_settings(scene, frames, fps, provenance):
    if not 2 <= frames <= 240 or not 1 <= fps <= 60:
        raise InputError("Animation requires 2–240 frames and 1–60 fps")
    scene["animation"] = {"frames": frames, "fps": fps,
                          "interpolation": "LINEAR", **provenance}
    scene["geometry_sha256"] = digest(scene["objects"])


def diffusion_scene(host_scene, guest_scene, output, waypoints, frames=48, fps=12,
                    show_path=True):
    """Translate a rigid molecule along authored Cartesian waypoints (angstrom)."""
    scene, guest = read_json(host_scene), read_json(guest_scene)
    check_kind(scene, "scene")
    check_kind(guest, "scene")
    points = np.asarray(waypoints, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or len(points) < 2 or not np.isfinite(points).all():
        raise InputError("waypoints must contain at least two finite xyz positions in angstrom")
    if len(points) > frames:
        raise InputError("Use at least as many frames as waypoints")
    atoms = [o["position"] for o in guest["objects"] if o["type"] == "sphere"]
    if not atoms:
        raise InputError("Guest scene contains no molecular atoms")
    center = np.mean(atoms, axis=0)
    times = np.linspace(1, frames, len(points)).round().astype(int)
    for original in guest["objects"]:
        obj = copy.deepcopy(original)
        obj["group"] = "diffusing_guest/" + obj.get("group", "molecule")
        obj["keyframes"] = []
        for frame, point in zip(times, points):
            key = {"frame": int(frame)}
            for field in ("position", "start", "end"):
                if field in obj:
                    key[field] = (np.asarray(obj[field]) - center + point).tolist()
            if "vertices" in obj:
                raise InputError("Use a molecular ball-stick/sticks/spacefill guest scene")
            obj["keyframes"].append(key)
        obj.update({k: v for k, v in obj["keyframes"][0].items() if k != "frame"})
        scene["objects"].append(obj)
    if show_path:
        for a, b in pairwise(points):
            cylinder(scene, a, b, 0.045, scene["style"]["accent"], "authored_path")
    _animation_settings(scene, frames, fps, {
        "type": "authored_diffusion", "waypoints_angstrom": points.tolist(),
        "coordinate_origin": "user-authored rigid translation; not MD",
        "physical_time": None, "diffusivity": None, "steric_validation": "not performed",
        "guest_source": guest["provenance"],
    })
    return {"scene": write_json(output, scene), "frames": frames,
            "meaning": "schematic trajectory; no physical diffusion rate is implied"}


def reaction_scene(surface_scene, output, snapshots, frames=48, fps=12):
    """Animate explicit atom-conserving snapshots and explicit changing bonds.

    snapshots: [{frame, label, atoms:[{id,element,position}], bonds:[[a,b], ...]}].
    No chemical mechanism, atom position, charge transfer or energy is inferred.
    """
    scene = read_json(surface_scene)
    check_kind(scene, "scene")
    if len(snapshots) < 2:
        raise InputError("At least two explicit reaction snapshots are required")
    times = [s["frame"] for s in snapshots]
    if times != sorted(set(times)) or times[0] != 1 or times[-1] != frames:
        raise InputError("Snapshot frames must increase from 1 to the final frame")
    maps = [{str(a["id"]): a for a in s["atoms"]} for s in snapshots]
    identity = {k: a["element"] for k, a in maps[0].items()}
    for snap, atoms in zip(snapshots, maps):
        if len(atoms) != len(snap["atoms"]) or {k: a["element"] for k, a in atoms.items()} != identity:
            raise InputError("Atom ids and elements must remain identical across reaction snapshots")
        for atom in atoms.values():
            p = np.asarray(atom["position"], dtype=float)
            if p.shape != (3,) or not np.isfinite(p).all():
                raise InputError("Each reaction atom needs a finite xyz position")
    bond_sets = []
    for s in snapshots:
        pairs = set()
        for a, b in s.get("bonds", []):
            a, b = str(a), str(b)
            if a not in identity or b not in identity or a == b:
                raise InputError("Invalid reaction bond endpoints")
            pairs.add(tuple(sorted((a, b))))
        bond_sets.append(pairs)
    for atom_id, element in identity.items():
        sphere(scene, maps[0][atom_id]["position"], 0.34 if element != "H" else 0.20,
               ELEMENT_COLORS.get(element, "#9CA5B7"), "reacting_atoms", element=element,
               atom_id=atom_id)
        scene["objects"][-1]["keyframes"] = [{"frame": frame, "position": m[atom_id]["position"]}
                                              for frame, m in zip(times, maps)]
    for a, b in sorted(set.union(*bond_sets)):
        cylinder(scene, maps[0][a]["position"], maps[0][b]["position"], 0.10,
                 "#738A9C", "reaction_bonds")
        keys = []
        # Interpolating a rod's rotation and length between sparse snapshots does
        # not follow its linearly moving atom endpoints. Bake endpoints per frame.
        for frame in range(1, frames + 1):
            left = min(int(np.searchsorted(times, frame, side="right")) - 1, len(times) - 2)
            fraction = (frame - times[left]) / (times[left + 1] - times[left])
            endpoints = []
            for atom_id in (a, b):
                start = np.asarray(maps[left][atom_id]["position"], dtype=float)
                end = np.asarray(maps[left + 1][atom_id]["position"], dtype=float)
                endpoints.append((start * (1 - fraction) + end * fraction).tolist())
            bonds = bond_sets[left + 1] if fraction == 1 else bond_sets[left]
            keys.append({"frame": frame, "start": endpoints[0], "end": endpoints[1],
                         "visible": (a, b) in bonds})
        scene["objects"][-1]["keyframes"] = keys
    _animation_settings(scene, frames, fps, {
        "type": "authored_reaction", "snapshots": snapshots,
        "coordinate_origin": "explicit storyboard snapshots; not a transition-state calculation",
        "atom_conservation": identity, "physical_time": None,
    })
    return {"scene": write_json(output, scene), "frames": frames,
            "meaning": "schematic reaction; no mechanism or activation energy inferred"}


def gate_open_scene(guest_scene, output, closed_angle=24.0, open_angle=90.0,
                    edge_length=6.0, depth=2.8, frames=48, fps=12, preset="porcelain",
                    width=1000, height=800):
    """A guest-induced hinged-pore storyboard, with constant framework strut lengths.

    This creates an idealized wine-rack prism; it is not a deformation of a supplied CIF.
    Angles are between the two in-plane lattice bars, in degrees.
    """
    if not 10 <= closed_angle < open_angle <= 120 or not 2 <= edge_length <= 30 or not 0.5 <= depth <= 20:
        raise InputError("Require 10 <= closed_angle < open_angle <= 120, edge_length 2–30 Å, depth 0.5–20 Å")
    if not 12 <= frames <= 240:
        raise InputError("Gate-opening requires 12–240 frames")
    guest = read_json(guest_scene)
    check_kind(guest, "scene")
    if any(o["type"] not in {"sphere", "cylinder"} for o in guest["objects"]):
        raise InputError("Use an optimized molecular ball-stick/sticks/spacefill guest scene")
    positions = [o["position"] for o in guest["objects"] if o["type"] == "sphere"]
    if not positions:
        raise InputError("Guest contains no molecular atoms")
    center = np.mean(positions, axis=0)
    scene = new_scene(np.eye(3), preset, False, width, height)
    # Pore cross-section is xy, with the pore axis along z. Explicit screen-up
    # avoids rolling an oblique xy aperture into a misleading horizontal diamond.
    scene["camera"].update(direction=[0, 0, 1], up=[0, 1, 0])
    scene["provenance"] = {"type": "idealized flexible MOF gate-opening schematic",
                           "source_cif": None, "geometry": "hinged wine-rack pore prism",
                           "frame_color": "gold", "guest_source": guest["provenance"]}
    corners, guest_centers, angles = [], [], []
    for frame in range(1, frames + 1):
        time = (frame - 1) / (frames - 1)
        opening = np.clip((time - 0.32) / 0.43, 0, 1)
        opening = opening * opening * (3 - 2 * opening)
        angle = closed_angle + (open_angle - closed_angle) * opening
        theta = np.deg2rad(angle)
        a = np.array([edge_length, 0, 0])
        b = np.array([edge_length * np.cos(theta), edge_length * np.sin(theta), 0])
        plane = [-a / 2 - b / 2, a / 2 - b / 2, a / 2 + b / 2, -a / 2 + b / 2]
        corners.append([p + [0, 0, z] for z in (-depth / 2, depth / 2) for p in plane])
        start = np.array([-0.30 * edge_length, 0.85 * edge_length, depth * 1.7])
        at_mouth = np.array([0, 0.12 * edge_length, depth / 2 + 1.6])
        if time <= 0.32:
            approach = time / 0.32
            guest_centers.append(start * (1 - approach) + at_mouth * approach)
        else:
            entry = np.clip((time - 0.32) / 0.43, 0, 1)
            entry = entry * entry * (3 - 2 * entry)
            guest_centers.append(at_mouth * (1 - entry))
        angles.append(float(angle))
    gold = "#D9A344"
    for i in range(8):
        sphere(scene, corners[0][i], 0.27, gold, "flexible_framework_nodes", node_id=i)
        scene["objects"][-1]["keyframes"] = [
            {"frame": f + 1, "position": c[i].tolist()} for f, c in enumerate(corners)]
    edges = [(i, (i + 1) % 4) for i in range(4)] + [
        (i + 4, (i + 1) % 4 + 4) for i in range(4)] + [(i, i + 4) for i in range(4)]
    for a, b in edges:
        cylinder(scene, corners[0][a], corners[0][b], 0.19, gold, "flexible_framework_struts")
        scene["objects"][-1]["keyframes"] = [
            {"frame": f + 1, "start": c[a].tolist(), "end": c[b].tolist()}
            for f, c in enumerate(corners)]
    for original in guest["objects"]:
        obj = copy.deepcopy(original)
        obj["group"] = "incoming_guest/" + obj.get("group", "atoms")
        obj["keyframes"] = []
        for frame, point in enumerate(guest_centers, 1):
            key = {"frame": frame}
            for field in ("position", "start", "end"):
                if field in original:
                    key[field] = (np.asarray(original[field]) - center + point).tolist()
            obj["keyframes"].append(key)
        obj.update({k: v for k, v in obj["keyframes"][0].items() if k != "frame"})
        scene["objects"].append(obj)
    _animation_settings(scene, frames, fps, {
        "type": "authored_gate_opening", "closed_angle_degrees": closed_angle,
        "open_angle_degrees": open_angle, "angles_by_frame": angles,
        "framework_edge_length_angstrom": edge_length, "depth_angstrom": depth,
        "strut_lengths_preserved": True, "guest_internal_geometry_preserved": True,
        "pore_axis_cartesian": [0, 0, 1], "hinge_plane": "xy",
        "guest_centers_by_frame": [p.tolist() for p in guest_centers],
        "stages": "approach closed pore -> simultaneous guest entry and opening -> open pore",
        "coordinate_origin": "parametric hinge motion and authored guest translation",
        "physical_time": None, "mechanism_status": "illustrative; not a validated specific MOF mechanism",
    })
    return {"scene": write_json(output, scene), "frames": frames,
            "meaning": "idealized gate-opening; bar lengths and guest geometry are preserved"}
