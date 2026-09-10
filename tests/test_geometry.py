from pathlib import Path

import numpy as np
import pytest

from mof_blender.animation import diffusion_scene, gate_open_scene, reaction_scene
from mof_blender.graph import periodic_dimensions, simplify_graph, unwrap_nonperiodic_axes
from mof_blender.io import InputError, digest, read_json, write_json
from mof_blender.scene import new_scene, polyhedron, sphere
from mof_blender.structures import load_cif
from mof_blender.views import change_view, interpret_view, lattice_direction


def test_triclinic_reciprocal_is_not_direct_direction():
    cell = [[10, 0, 0], [3, 8, 0], [2, 1, 7]]
    normal = lattice_direction(cell, [1, 0, 0], "hkl")
    direct = lattice_direction(cell, [1, 0, 0], "uvw")
    assert not np.allclose(normal, direct)
    assert np.isclose(np.dot(cell[1], normal), 0)
    assert np.isclose(np.dot(cell[2], normal), 0)


def test_lattice_view_and_orbit():
    cell = [[5, 0, 0], [-2.5, 4.330127, 0], [0, 0, 8]]
    view = interpret_view("沿b轴看", cell)
    assert np.allclose(view["direction"], np.array(cell[1]) / 5)
    rotated = interpret_view("绕c轴旋转90度", cell, interpret_view("沿a轴看", cell))
    assert np.allclose(rotated["direction"], [0, 1, 0], atol=1e-8)
    assert interpret_view("从侧面观察", cell)["direction"] == [1.0, 0.0, 0.0]
    with pytest.raises(InputError):
        interpret_view("随便旋转一下", cell)


def test_planar_square_and_tetrahedron_are_distinct():
    _, faces, kind = polyhedron([[1, 0, 0], [0, 1, 0], [-1, 0, 0], [0, -1, 0]])
    assert kind == "planar_polygon" and len(faces) == 1 and len(faces[0]) == 4
    _, faces, kind = polyhedron([[1, 1, 1], [-1, -1, 1], [-1, 1, -1], [1, -1, -1]])
    assert kind == "convex_polyhedron" and len(faces) == 4


def test_periodic_linker_contraction_preserves_self_edge_voltage():
    graph = {"nodes": [{"id": 0, "kind": "node"}, {"id": 1, "kind": "linker"}],
             "edges": [{"a": 0, "b": 1, "shift": [0, 0, 0]},
                       {"a": 0, "b": 1, "shift": [-1, 0, 0]}]}
    # Keep the node id irrespective of which representative is suppressed.
    simple = simplify_graph(graph)
    assert len(simple["nodes"]) == 1 and len(simple["edges"]) == 1
    assert simple["edges"][0]["shift"] == [-1, 0, 0]
    assert simple["nodes"][0]["degree"] == 2
    assert periodic_dimensions(simple)[0]["dimension"] == 1


def test_six_connected_pcu_periodic_dimension():
    graph = {"nodes": [{"id": 0}], "edges": [
        {"a": 0, "b": 0, "shift": s} for s in [[1, 0, 0], [0, 1, 0], [0, 0, 1]]]}
    simple = simplify_graph(graph)
    assert simple["nodes"][0]["degree"] == 6
    assert periodic_dimensions(simple)[0]["dimension"] == 3


def test_layer_unwrap_preserves_bond_vectors_and_removes_z_seams():
    graph = {"nodes": [{"id": 0, "fractional": [0, 0, 0]},
                        {"id": 1, "fractional": [0.5, 0.5, 1]}],
             "edges": [{"a": 0, "b": 1, "shift": [0, 0, -1]},
                       {"a": 0, "b": 1, "shift": [1, 0, -1]},
                       {"a": 0, "b": 1, "shift": [0, 1, -1]}]}
    updated, changes = unwrap_nonperiodic_axes(graph)
    assert changes == {"1": [0, 0, -1]}
    assert all(e["shift"][2] == 0 for e in updated["edges"])
    for before, after in zip(graph["edges"], updated["edges"]):
        def vector(g, e):
            return np.array(g["nodes"][e["b"]]["fractional"]) + e["shift"] - g["nodes"][e["a"]]["fractional"]
        assert np.allclose(vector(graph, before), vector(updated, after))


def test_view_change_preserves_every_object_and_source(tmp_path):
    data = new_scene(np.eye(3))
    sphere(data, [0, 0, 0], 1, "#446677", "molecule")
    source = write_json(tmp_path / "first.json", data)
    before = Path(source).read_bytes()
    result = change_view(source, tmp_path / "second.json", instruction="沿[1 1 0]看")
    assert result["geometry_unchanged"]
    assert read_json(result["scene"])["objects"] == data["objects"]
    assert Path(source).read_bytes() == before
    with pytest.raises(FileExistsError):
        change_view(source, source, instruction="俯视")


def test_diffusion_rigid_body_and_reaction_atom_conservation(tmp_path):
    data = new_scene(np.eye(3))
    sphere(data, [0, 0, 0], 0.3, "#446677", "atoms")
    sphere(data, [1, 0, 0], 0.2, "#AA4444", "atoms")
    source = write_json(tmp_path / "molecule.json", data)
    result = diffusion_scene(source, source, tmp_path / "diffusion.json", [[0, 0, 0], [4, 2, 1]], frames=12)
    moving = read_json(result["scene"])["objects"][-3:-1]
    for frame in (0, 1):
        a, b = [np.array(o["keyframes"][frame]["position"]) for o in moving]
        assert np.isclose(np.linalg.norm(a - b), 1)
    snapshots = [{"frame": 1, "atoms": [{"id": 0, "element": "C", "position": [0, 0, 0]}]},
                 {"frame": 12, "atoms": [{"id": 0, "element": "O", "position": [0, 0, 1]}]}]
    with pytest.raises(InputError, match="identical"):
        reaction_scene(source, tmp_path / "bad.json", snapshots, frames=12)


CIF = """data_first
_cell_length_a 10
_cell_length_b 11
_cell_length_c 12
_cell_angle_alpha 90
_cell_angle_beta 100
_cell_angle_gamma 90
_symmetry_space_group_name_H-M 'P 1'
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
C1 C 0.1 0.2 0.3 1
"""


def test_cif_block_selection_and_disorder(tmp_path):
    path = tmp_path / "multiple.cif"
    path.write_text(CIF + CIF.replace("data_first", "data_second"))
    before = digest(path.read_bytes())
    with pytest.raises(InputError, match="Multiple"):
        load_cif(path)
    atoms, info = load_cif(path, "second")
    assert info["selected_block"] == "second" and len(atoms) == 1
    assert np.allclose(atoms.get_scaled_positions()[0], [0.1, 0.2, 0.3])
    assert digest(path.read_bytes()) == before
    path = tmp_path / "disorder.cif"
    path.write_text(CIF.replace("0.3 1", "0.3 0.5"))
    with pytest.raises(InputError, match="occupancy"):
        load_cif(path)


def test_gate_opening_strut_lengths_and_guest_rigidity(tmp_path):
    guest = new_scene(np.eye(3))
    sphere(guest, [0, 0, 0], 0.4, "#4488AA", "atoms")
    sphere(guest, [1, 0, 0], 0.2, "#DDDDDD", "atoms")
    guest_path = write_json(tmp_path / "guest.json", guest)
    result = gate_open_scene(guest_path, tmp_path / "gate.json", frames=16)
    data = read_json(result["scene"])
    for obj in data["objects"]:
        if obj["group"] == "flexible_framework_struts":
            lengths = [np.linalg.norm(np.array(k["end"]) - k["start"]) for k in obj["keyframes"]]
            assert np.ptp(lengths) < 1e-9
    moving = [o for o in data["objects"] if o["group"].startswith("incoming_guest")]
    for a, b in zip(moving[0]["keyframes"], moving[1]["keyframes"]):
        assert np.isclose(np.linalg.norm(np.array(a["position"]) - b["position"]), 1)
    angles = data["animation"]["angles_by_frame"]
    assert angles[0] == 24 and angles[-1] == 90
    assert np.all(np.diff(angles) >= 0)
    assert data["camera"]["direction"] == [0, 0, 1]
    assert data["camera"]["up"] == [0, 1, 0]
    centers = np.array(data["animation"]["guest_centers_by_frame"])
    assert centers[0, 0] < 0 and centers[0, 1] > 0
    assert np.allclose(centers[-1], [0, 0, 0])
    assert np.all(np.diff(centers[:, 2]) <= 1e-10)


def test_reaction_rotating_bond_tracks_atoms_at_intermediate_frames(tmp_path):
    surface = write_json(tmp_path / "surface.json", new_scene(np.eye(3)))
    snapshots = [
        {"frame": 1, "atoms": [{"id": "C", "element": "C", "position": [0, 0, 0]},
                                {"id": "O", "element": "O", "position": [0, 0, 2]}],
         "bonds": [["C", "O"]]},
        {"frame": 5, "atoms": [{"id": "C", "element": "C", "position": [1, 0, 0]},
                                {"id": "O", "element": "O", "position": [-1, 0, 0]}],
         "bonds": []},
    ]
    result = reaction_scene(surface, tmp_path / "reaction.json", snapshots, frames=5)
    rod = next(o for o in read_json(result["scene"])["objects"] if o["group"] == "reaction_bonds")
    middle = next(k for k in rod["keyframes"] if k["frame"] == 3)
    assert np.allclose(middle["start"], [0.5, 0, 0])
    assert np.allclose(middle["end"], [-0.5, 0, 1])
    assert middle["visible"] and not rod["keyframes"][-1]["visible"]
