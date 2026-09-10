"""Revise selected local preview scenes after visual QA; keep first-pass artifacts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mof_blender.animation import diffusion_scene
from mof_blender.io import read_json, write_json
from mof_blender.render import render_scene
from mof_blender.scene import make_scene


def main():
    output = ROOT / "output" / "gallery"
    recipes = [
        ("05-mof5-net", "mof5", "net", "midnight", [4, 4, 3], "等轴测"),
        ("06-cof-atoms", "cof", "sticks", "paper", [3, 3, 1], "沿c轴看"),
        ("07-cof-polygons", "cof", "polyhedra", "porcelain", [4, 4, 1], "沿c轴看"),
    ]
    results = {}
    for slug, model, representation, preset, repeat, view in recipes:
        scene = output / f"{slug}-r2.scene.json"
        if not scene.exists():
            make_scene(output / "inputs" / f"{model}.analysis.json", scene,
                       representation=representation, preset=preset, repeat=repeat,
                       view=view, width=1200, height=900, edge_radius=0.13)
        print("Revising", slug, flush=True)
        results[slug] = {"id": slug + "-r2", "scene": str(scene),
                         **render_scene(scene, output / f"{slug}-r2", samples=64)}
    slug = "11-pore-diffusion"
    host = output / "diffusion-host-r2.scene.json"
    make_scene(output / "inputs" / "mof5.analysis.json", host, repeat=[2, 2, 3],
               preset="porcelain", width=800, height=650, edge_radius=0.13, node_scale=0.18)
    scene = output / "11-pore-diffusion-r2.scene.json"
    length = read_json(output / "inputs" / "mof5.analysis.json")["structure"]["cell"][0][0]
    diffusion_scene(host, output / "co2-guest.scene.json", scene,
                    [[length * 0.5, length * 0.5, z * length] for z in [0.05, 0.65, 1.3, 1.95]],
                    frames=36, fps=12)
    print("Revising", slug, flush=True)
    results[slug] = {"id": slug + "-r2", "scene": str(scene),
                     **render_scene(scene, output / f"{slug}-r2", samples=16, animate=True, timeout=1800)}
    write_json(output / "qa-revisions.json", results)
    print(json.dumps({"revisions": list(results)}))


if __name__ == "__main__":
    main()
