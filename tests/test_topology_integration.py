from pathlib import Path

import pytest

from mof_blender.io import digest, read_json
from mof_blender.scene import make_scene
from mof_blender.topology import analyze_cif


@pytest.mark.integration
@pytest.mark.parametrize("fixture,expected,degree,dimension", [
    ("mof5_generated.cif", "pcu", 6, 3),
    ("cof_hcb_generated.cif", "hcb", 3, 2),
])
def test_autografs_real_cif_to_connected_scene(tmp_path, fixture, expected, degree, dimension):
    source = Path(__file__).resolve().parents[1] / "examples" / fixture
    before = digest(source.read_bytes())
    result = analyze_cif(source, tmp_path / "analysis.json")
    analysis = read_json(result["analysis"])
    assert analysis["topology"]["candidates"] == [expected]
    assert analysis["topology"]["periodic_dimension"][0]["dimension"] == dimension
    assert all(n["degree"] == degree for n in analysis["display_graph"]["nodes"])
    scene = make_scene(result["analysis"], tmp_path / "scene.json", repeat=[3, 3, 1])
    objects = read_json(scene["scene"])["objects"]
    assert any(o["group"] == "topology_edges" for o in objects)
    assert digest(source.read_bytes()) == before
