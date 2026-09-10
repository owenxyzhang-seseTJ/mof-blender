# Methods, source references and provenance / 方法与来源

Inspected on 2026-09-10. External documentation describes its own software; implemented and
tested behavior is recorded separately in [validation.md](validation.md).

## AuToGraFS

- [Project](https://github.com/DCoupry/autografs)
- [Deconstruction documentation](https://github.com/DCoupry/autografs/blob/master/docs/deconstruction.md)
- [Original paper, DOI 10.1021/jp507643v](https://doi.org/10.1021/jp507643v)
- Inspected development revision: `cd975211583e92a173a9db283a28c216405786be`.
- Executed version: **PyPI AuToGraFS 3.2.0**, not an unpinned development checkout.

The PyPI release lacks the newer public `Deconstruction.blueprint` field. The version-gated
adapter reuses the installed engine's bond graph, connected-unit unwrapping and quotient
helpers; reconstructed quotient edges must exactly match the engine's result. If they do not,
rendering stops. Net candidates and per-subframework tiers are retained. The engine uses
coordination-sequence signatures; no graph-isomorphism proof is claimed.

The four included framework inputs are generated with the shipped AuToGraFS topology and SBU
libraries. `scripts/create_examples.py` records each blueprint, SBU mapping and source hash.
They demonstrate a round trip and are not experimental validation across an arbitrary CIF corpus.
The upstream IRMOF-1 test fixture contained a trailing empty CIF loop; it was not used as a
valid fixture or silently repaired in the shipped examples.

## ChemBlender source study

- [Official download page](https://www.chemblender.com/download)
- [ChemBlender 2.0 upstream source](https://github.com/sphereman/ChemBlender_2_0)
- Inspected revision: `9077096b776cd18ca85adb4b50253a0d3c18fd76`.

The official download page linked this repository. Inspection focused on `node.py`
(`Supercell`, `CoordPolyhedra`), `chem_utils.py` (`Chem_OT_ViewSet`), `_math.py`
(fractional/Cartesian handling), and `render.py` (`quick_render`).

| Reference concept | Independent implementation here |
| --- | --- |
| Crystal supercells and representations | ASE/Gemmi input, explicit periodic graph and JSON geometry |
| Coordination polyhedra | SciPy convex hull of real connection directions; separate planar polygon handling |
| Viewing controls | Numerically tested direct-lattice `[uvw]` and reciprocal-lattice `(hkl)` mapping |
| Quick rendering | Separate Blender process, three area lights, three curated palettes, Cycles denoising |
| Reusable scene objects | Named Blender collections, shared primitive meshes, embedded JSON and provenance |

No ChemBlender Python source, `.blend` node library, material, logo, screenshot or other asset
is copied into this repository. ChemBlender is GPL-licensed; it is a reference, not a bundled
runtime dependency. The user's attached slide images served as capability references and are
not republished in this public repository.

## Molecular geometry and layers

- [RDKit official Python guide](https://www.rdkit.org/docs/GettingStartedInPython.html): molecular
  parsing, explicit hydrogens, ETKDG conformers and force-field optimization.
- [ASE project](https://ase-lib.org/): `ase.build.graphene` and its honeycomb basis; the installed
  3.29.0 source was inspected directly. Graphene's example lattice parameter is 2.46 Å; AB
  stacking uses the basis displacement and an explicitly chosen 3.35 Å layer separation.

Generated SMILES geometries are optimized copies. MMFF94s is preferred when all parameters
exist; UFF is the fallback when fully parameterized. The recorded energy is in kcal/mol and
is used only to choose among converged local molecular conformers. Molecular animation
translates those coordinates without changing internal distances.

Layer and reaction schematics are not force-field-optimized slabs or transition states.

## Rendering and transport

- [Blender 5.2 RenderSettings API](https://docs.blender.org/api/5.2/bpy.types.RenderSettings.html)
- [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
- [MCP tools](https://modelcontextprotocol.io/specification/2025-03-26/server/tools)
- [Claude Code plugin reference](https://code.claude.com/docs/en/plugins-reference)

Blender rendering uses a trusted local worker script and a data-only scene recipe. Auto-running
scripts from input files is disabled. The MCP implementation uses the installed official Python
SDK (`mcp` 1.30.0); no custom imitation of the wire protocol is used. Codex registration syntax
was checked against the locally installed `codex mcp add --help`, and its plugin manifest was
checked with the local plugin schema validator.
