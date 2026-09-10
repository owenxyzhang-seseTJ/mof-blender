import numpy as np
from rdkit import Chem

from mof_blender.io import read_json
from mof_blender.scene import molecule_scene
from mof_blender.structures import read_molecule


def test_ethanol_optimized_and_roundtrips_as_sdf(tmp_path):
    result = molecule_scene(tmp_path / "ethanol.json", smiles="CCO", conformers=3)
    optimization = result["optimization"]
    assert optimization["converged"] and optimization["forcefield"] == "MMFF94s"
    molecule = next(iter(Chem.SDMolSupplier(result["sdf"], removeHs=False)))
    assert molecule.GetNumAtoms() == 9
    positions = molecule.GetConformer().GetPositions()
    original = [o["position"] for o in read_json(result["scene"])["objects"] if o["type"] == "sphere"]
    assert np.allclose(positions, original, atol=5e-5)


def test_optimization_is_reproducible():
    first = read_molecule(smiles="O=C=O", conformers=2)
    second = read_molecule(smiles="O=C=O", conformers=2)
    assert first["atoms"] == second["atoms"]
    positions = np.array([a["position"] for a in first["atoms"]])
    assert np.linalg.norm(np.cross(positions[0] - positions[1], positions[2] - positions[1])) < 1e-3
