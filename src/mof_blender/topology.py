"""An adapter to AuToGraFS; candidate matching is not an isomorphism proof."""
from __future__ import annotations

from functools import lru_cache
from importlib.metadata import version
from types import SimpleNamespace

import numpy as np

from .graph import periodic_dimensions, simplify_graph
from .io import InputError, write_json
from .structures import atom_payload, load_cif


@lru_cache(maxsize=1)
def generator():
    try:
        from autografs import Autografs
    except ImportError as exc:
        raise InputError("AuToGraFS is unavailable; install project dependencies first") from exc
    return Autografs()


def deconstruct_atoms(atoms, fuse_parallel_bridges=False):
    from pymatgen.core import Structure

    structure = Structure(np.asarray(atoms.cell), atoms.get_chemical_symbols(),
                          atoms.get_scaled_positions())
    import inspect

    engine = generator()
    if fuse_parallel_bridges:
        if "fuse_parallel_bridges" not in inspect.signature(engine.deconstruct).parameters:
            raise InputError("Installed AuToGraFS does not support fuse_parallel_bridges")
        result = engine.deconstruct(structure, fuse_parallel_bridges=True)
    else:
        result = engine.deconstruct(structure)
    candidates = list(result.net_candidates)
    report = {
        "engine": "AuToGraFS", "engine_version": version("autografs"),
        "candidates": candidates,
        "identification": "coordination-sequence signature candidates; not an isomorphism proof",
        "subframeworks": [{"candidates": list(x), "tier": getattr(x, "tier", None)}
                          for x in result.subframework_nets],
        "periodic_components": result.n_periodic_components,
        "removed_guest_formulas": list(result.guest_formulas),
        "rod_units": len(result.rod_units),
        "fuse_parallel_bridges": fuse_parallel_bridges,
        "fused_bridges": getattr(result, "fused_bridges", 0),
    }
    if result.rod_units:
        # Infinite rod SBUs do not have a finite centroid/polyhedron.
        report["render_status"] = "atomic-only: rod points-of-extension rendering is not implemented"
        return None, report
    blueprint = getattr(result, "blueprint", None)
    if blueprint is None:
        blueprint = _release_geometry(result)
        report["geometry_adapter"] = "3.2.0 internal bond graph; exact quotient cross-check"
    else:
        report["geometry_adapter"] = "public Deconstruction.blueprint"
    if len(blueprint.centers) != len(result.units):
        raise InputError("AuToGraFS returned inconsistent unit/centroid indexing")
    ports = {i: [] for i in range(len(result.units))}
    for a, b, pa, pb in blueprint.cuts:
        if result.units[b].kind != "cap":
            ports[a].append(list(pa))
        if result.units[a].kind != "cap":
            ports[b].append(list(pb))
    nodes = [{"id": i, "kind": u.kind, "name": u.name,
              "fractional": list(blueprint.centers[i]),
              "ports_fractional": ports[i], "cut_bond_count": u.n_connections,
              "atom_indices_in_guest_free_structure": list(u.atom_indices)}
             for i, u in enumerate(result.units)]
    edges = [{"a": int(a), "b": int(b), "shift": list(s), "multiplicity": int(count)}
             for (a, b, s), count in sorted(result.quotient_edges.items())]
    graph = {"nodes": nodes, "edges": edges}
    report["periodic_dimension"] = periodic_dimensions(graph)
    report["render_status"] = "ready"
    report["unit_atom_index_basis"] = "AuToGraFS guest-free structure, not the original CIF rows"
    report["guest_free_atoms"] = [{"element": str(s.specie),
                                    "fractional": list(s.frac_coords)}
                                   for s in result.structure]
    return graph, report


def _release_geometry(result):
    """Version-gated adapter for the PyPI release, before the public blueprint API.

    Reuse the engine's bond graph/unwrapping functions and REQUIRE its reconstructed
    quotient to equal the analysis output. A radius-only centroid guess is unsafe.
    """
    if version("autografs") != "3.2.0":
        raise InputError("Unknown AuToGraFS geometry API; update the adapter before rendering")
    import importlib
    dc = importlib.import_module("autografs.deconstruct")
    bonds = dc._structure_bond_graph(result.structure)
    units = [set(u.atom_indices) for u in result.units]
    atom_to_unit = {a: i for i, atoms in enumerate(units) for a in atoms}
    unwraps = []
    for atoms in units:
        rank, images, _ = dc._component_periodicity(bonds.subgraph(atoms), atoms)
        if rank:
            raise InputError("An infinite building unit cannot be rendered as a finite polyhedron")
        unwraps.append(images)
    frac = result.structure.frac_coords
    images = dc._unit_images(frac, units, unwraps)
    cuts = dc._cut_bonds(bonds, atom_to_unit)
    quotient = dc._unit_quotient(cuts, atom_to_unit, unwraps, images)
    if quotient != result.quotient_edges:
        raise InputError("AuToGraFS geometry/quotient cross-check failed; render was stopped")
    centers = [np.mean([frac[a] + unwraps[i][a] for a in sorted(atoms)], axis=0) - images[i]
               for i, atoms in enumerate(units)]
    positions = []
    for a, b, shift in cuts:
        i, j = atom_to_unit[a], atom_to_unit[b]
        pa = (frac[a] + frac[b] + shift) / 2 + unwraps[i][a] - images[i]
        pb = (frac[a] + frac[b] - shift) / 2 + unwraps[j][b] - images[j]
        positions.append((i, j, pa, pb))
    return SimpleNamespace(centers=centers, cuts=positions)


def analyze_cif(path, output, block=None, identify=True, fuse_parallel_bridges=False,
                bond_scale=1.15):
    atoms, info = load_cif(path, block)
    data = {"schema": "mof-blender/analysis/1", "input": info,
            "structure": atom_payload(atoms, bond_scale),
            "notes": ["Source coordinates are preserved; symmetry is expanded for visualization.",
                      "Display bonds use a distance heuristic independent of AuToGraFS bonding."]}
    if identify:
        graph, report = deconstruct_atoms(atoms, fuse_parallel_bridges)
        data["topology"] = report
        data["quotient_graph"] = graph
        data["display_graph"] = simplify_graph(graph) if graph else None
    else:
        data["topology"] = {"render_status": "not requested", "candidates": []}
        data["quotient_graph"] = data["display_graph"] = None
    target = write_json(output, data)
    return {"analysis": target, "formula": info["formula"],
            "atoms": len(atoms), "topology": {k: v for k, v in data["topology"].items()
                                              if k != "guest_free_atoms"}}
