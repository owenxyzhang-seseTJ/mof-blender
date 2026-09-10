import numpy as np
from ase.io import read

from mof_blender.io import read_json
from mof_blender.layers import layer_scene


def test_graphene_bilayer_geometry_and_metadata(tmp_path):
    result = layer_scene(tmp_path / "graphene.json", repeat=[2, 2, 1], layers=2)
    coordinates = read(result["xyz"])
    assert len(coordinates) == 16
    assert np.allclose(np.unique(coordinates.positions[:, 2]), [0, 3.35])
    scene = read_json(result["scene"])
    assert scene["provenance"]["stacking"] == "AB"
    atoms = [o for o in scene["objects"] if o["type"] == "sphere"]
    assert len({a["color"] for a in atoms}) == 2
    assert all(a["element"] == "C" for a in atoms)
    # No spurious interlayer covalent bonds.
    assert all(abs(o["start"][2] - o["end"][2]) < 1e-8 for o in scene["objects"]
               if o["type"] == "cylinder")
