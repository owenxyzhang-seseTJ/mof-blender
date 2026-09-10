"""Read one explicitly selected crystallographic data block; never repair silently."""
from __future__ import annotations

import io
import re

import numpy as np

from .io import InputError, source_info


def _number(text, default=1.0):
    if text in ("?", ".", ""):
        return default
    return float(re.sub(r"\([^)]*\)$", "", str(text)))


def inspect_cif(path, block=None):
    import gemmi

    source = source_info(path)
    document = gemmi.cif.read_file(source["path"])
    blocks = [b for b in document if b.find_values("_atom_site_fract_x")]
    names = [b.name for b in blocks]
    if not blocks:
        raise InputError("No small-molecule CIF block with fractional atom coordinates was found.")
    if block is None and len(blocks) != 1:
        raise InputError(f"Multiple crystallographic blocks: {names}. Select block by name.")
    selected = next((b for b in blocks if b.name == block), None) if block else blocks[0]
    if selected is None:
        raise InputError(f"Unknown block {block!r}; available blocks: {names}")
    occupancy = [_number(v) for v in selected.find_values("_atom_site_occupancy")]
    disorder = [v for v in selected.find_values("_atom_site_disorder_group")
                if v not in (".", "?", "0")]
    return {
        "source": source, "blocks": names, "selected_block": selected.name,
        "asymmetric_sites": len(selected.find_values("_atom_site_fract_x")),
        "partial_occupancy": any(abs(x - 1) > 1e-6 for x in occupancy),
        "disorder_groups": sorted(set(disorder)), "_block_text": selected.as_string(),
    }


def load_cif(path, block=None):
    from ase.io import read

    info = inspect_cif(path, block)
    if info["partial_occupancy"] or info["disorder_groups"]:
        raise InputError("Disorder or partial occupancy requires an explicit ordered model. "
                         "The source CIF has not been changed.")
    atoms = read(io.StringIO(info.pop("_block_text")), format="cif", index=0)
    if not np.isfinite(atoms.positions).all() or abs(atoms.cell.volume) < 1e-8:
        raise InputError("Invalid coordinates or singular unit cell")
    atoms.set_pbc(True)
    info["expanded_sites"] = len(atoms)
    info["formula"] = atoms.get_chemical_formula()
    return atoms, info


def atom_payload(atoms, bond_scale=1.15):
    """Distance-based display bonds, with every periodic image retained."""
    from ase.data import covalent_radii
    from ase.neighborlist import neighbor_list

    if not 0.8 <= bond_scale <= 1.5:
        raise InputError("bond_scale must lie between 0.8 and 1.5")
    i, j, shifts = neighbor_list("ijS", atoms, covalent_radii[atoms.numbers] * bond_scale)
    bonds = set()
    for a, b, shift in zip(i, j, shifts):
        s = tuple(int(x) for x in shift)
        forward = (int(a), int(b), s)
        reverse = (int(b), int(a), tuple(-x for x in s))
        bonds.add(min(forward, reverse))
    return {
        "cell": np.asarray(atoms.cell).tolist(), "pbc": atoms.pbc.tolist(),
        "atoms": [{"id": i, "element": symbol, "position": p.tolist()}
                  for i, (symbol, p) in enumerate(zip(atoms.symbols, atoms.positions))],
        "bonds": [{"a": a, "b": b, "shift": list(s), "order": 1}
                  for a, b, s in sorted(bonds)],
        "bond_method": f"display-only covalent radii distance cutoff x {bond_scale}",
        "bond_orders": "not inferred for CIF/XYZ",
    }


def read_molecule(source=None, smiles=None, optimize=True, conformers=8):
    if (source is None) == (smiles is None):
        raise InputError("Supply exactly one of source or smiles")
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError as exc:
        raise InputError("Molecule support needs the molecules extra (RDKit)") from exc
    if smiles:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise InputError("Invalid SMILES")
        mol = Chem.AddHs(mol)
        parameters = AllChem.ETKDGv3()
        parameters.randomSeed = 20260910
        if not 1 <= conformers <= 32:
            raise InputError("conformers must be between 1 and 32")
        ids = list(AllChem.EmbedMultipleConfs(mol, numConfs=conformers, params=parameters))
        if not ids:
            raise InputError("RDKit could not generate a 3D conformer")
        provenance = {"smiles": smiles, "coordinate_origin": "generated ETKDG conformer",
                      "experimental_coordinates": False, "random_seed": 20260910}
    else:
        from pathlib import Path

        provenance = source_info(source)
        suffix = Path(source).suffix.lower()
        if suffix == ".xyz":
            if optimize:
                raise InputError("XYZ has no bond orders. Supply MOL/SDF/SMILES to optimize, "
                                 "or set optimize=False for an unchanged coordinate rendering.")
            from ase.io import read
            atoms = read(source)
            atoms.set_pbc(False)
            return {**atom_payload(atoms), "source": provenance}
        if suffix == ".sdf":
            molecules = list(Chem.SDMolSupplier(str(source), removeHs=False))
            if len(molecules) != 1:
                raise InputError("Select a single molecule from a multi-record SDF first")
            mol = molecules[0]
        elif suffix == ".mol":
            mol = Chem.MolFromMolFile(str(source), removeHs=False)
        elif suffix == ".pdb":
            mol = Chem.MolFromPDBFile(str(source), removeHs=False)
        else:
            raise InputError("Molecule input supports XYZ, MOL, SDF, PDB or SMILES")
        if mol is None or not mol.GetNumConformers():
            raise InputError("Could not read molecule coordinates")
        provenance["coordinate_origin"] = "input file"
        if optimize:
            mol = Chem.AddHs(mol, addCoords=True)
    if optimize:
        if AllChem.MMFFHasAllMoleculeParams(mol):
            forcefield = "MMFF94s"
            results = AllChem.MMFFOptimizeMoleculeConfs(mol, numThreads=1, maxIters=1000,
                                                       mmffVariant=forcefield)
        elif AllChem.UFFHasAllMoleculeParams(mol):
            forcefield = "UFF"
            results = AllChem.UFFOptimizeMoleculeConfs(mol, numThreads=1, maxIters=1000)
        else:
            raise InputError("Neither MMFF94s nor UFF has all parameters for this molecule")
        converged = [(energy, i) for i, (status, energy) in enumerate(results)
                     if status == 0 and np.isfinite(energy)]
        if not converged:
            raise InputError("No molecular conformer converged within 1000 optimization steps")
        energy, selected = min(converged)
        selected_id = list(mol.GetConformers())[selected].GetId()
        chosen = Chem.Conformer(mol.GetConformer(selected_id))
        mol.RemoveAllConformers()
        mol.AddConformer(chosen, assignId=True)
        provenance["optimization"] = {"forcefield": forcefield, "converged": True,
                                      "energy_kcal_mol": float(energy), "max_iterations": 1000,
                                      "conformers_tested": len(results),
                                      "conformers_converged": len(converged),
                                      "selected_conformer": selected,
                                      "interpretation": "local molecular force-field energy; not a free energy"}
        provenance["coordinate_origin"] += "; RDKit optimized copy"
    else:
        provenance["optimization"] = {"performed": False}
    conformer = mol.GetConformer()
    return {
        "cell": np.eye(3).tolist(), "pbc": [False] * 3,
        "source": provenance,
        "atoms": [{"id": a.GetIdx(), "element": a.GetSymbol(),
                   "position": list(conformer.GetAtomPosition(a.GetIdx()))}
                  for a in mol.GetAtoms()],
        "bonds": [{"a": b.GetBeginAtomIdx(), "b": b.GetEndAtomIdx(),
                   "shift": [0, 0, 0], "order": b.GetBondTypeAsDouble()}
                  for b in mol.GetBonds()],
        "bond_method": "RDKit molecular graph; PDB connectivity may be perceived",
        "mol_block": Chem.MolToMolBlock(mol),
    }
