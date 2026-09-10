"""Reproduce the example gallery; generated structures are explicitly illustrative."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mof_blender.animation import diffusion_scene, gate_open_scene, reaction_scene
from mof_blender.io import digest, read_json, write_json
from mof_blender.layers import layer_scene
from mof_blender.render import render_scene
from mof_blender.scene import make_scene, molecule_scene, new_scene, sphere
from mof_blender.topology import analyze_cif, generator
from mof_blender.views import change_view


def prepare(output):
    output.mkdir(parents=True, exist_ok=False)
    inputs = output / "inputs"
    inputs.mkdir()
    generated = []
    engine = generator()
    for name, net, node in [("mof5", "pcu", "Zn_mof5_octahedral"),
                            ("cof", "hcb", "Boroxine_triangle"),
                            ("dia", "dia", "N66_tetrahedral"),
                            ("fcu", "fcu", "UIO66_Zr_icosahedral")]:
        topology = engine.topologies[net]
        mapping = {s: node if len(s.atoms.indices_from_symbol("X")) > 2 else "Benzene_linear"
                   for s in topology.mappings}
        model = engine.build(topology, mappings=mapping, max_rmsd=0.7)
        cif = inputs / f"{name}_generated.cif"
        model.write_cif(cif)
        analyze_cif(cif, inputs / f"{name}.analysis.json")
        generated.append({"cif": str(cif), "sha256": digest(cif.read_bytes()), "net_blueprint": net,
                          "node_sbu": node, "linker_sbu": "Benzene_linear",
                          "origin": "AuToGraFS generated model; not experimental structure refinement"})
    write_json(inputs / "sources.json", generated)
    entries = []

    def framework(slug, title, model, rep, preset, repeat, view, description):
        target = output / f"{slug}.scene.json"
        make_scene(inputs / f"{model}.analysis.json", target, representation=rep, preset=preset,
                   repeat=repeat, view=view, width=1200, height=900, edge_radius=0.13)
        entries.append({"id": slug, "title": title, "scene": str(target), "description": description,
                        "animation": False})
        return target

    ethanol = output / "01-ethanol.scene.json"
    molecule_scene(ethanol, smiles="CCO", view="俯视", width=1200, height=900)
    entries.append({"id": "01-ethanol", "title": "乙醇 · 优化球棍模型", "scene": str(ethanol),
                    "description": "RDKit ETKDG 多构象 + MMFF94s；白底与柔和高光。", "animation": False})
    caffeine = output / "02-caffeine.scene.json"
    molecule_scene(caffeine, smiles="Cn1c(=O)c2c(ncn2C)n(C)c1=O", representation="spacefill",
                   preset="porcelain", view="俯视", width=1200, height=900)
    entries.append({"id": "02-caffeine", "title": "咖啡因 · 空间填充模型", "scene": str(caffeine),
                    "description": "RDKit 优化构象；范德华球面与哑光材质。", "animation": False})
    framework("03-mof5-atoms", "MOF-5 · 晶体球棍", "mof5", "ball-stick", "paper",
              [2, 2, 2], "沿a轴看", "AuToGraFS 生成模型；沿 a 轴观察孔道，2×2×2 超胞。")
    host = framework("04-mof5-polyhedra", "pcu · 六连接节点多面体", "mof5", "polyhedra",
                     "porcelain", [3, 3, 3], "等轴测", "由实际连接方向构建八面体，连接子抽象为细杆。")
    framework("05-mof5-net", "pcu · 深色节点线框", "mof5", "net", "midnight",
              [4, 4, 3], "等轴测", "深蓝背景、青绿色节点与暖金连接线。")
    framework("06-cof-atoms", "二维 COF · 单层原子结构", "cof", "sticks", "paper",
              [3, 3, 1], "沿c轴看", "硼氧六环 COF 的 hcb 生成模型；单层俯视。")
    framework("07-cof-polygons", "hcb · 三连接平面节点", "cof", "polyhedra", "porcelain",
              [4, 4, 1], "沿c轴看", "三连接节点保持三角形，不增加虚构的锥顶。")
    framework("08-dia-tetrahedra", "dia · 四连接三维框架", "dia", "polyhedra", "midnight",
              [2, 2, 2], "等轴测", "有机四连接构筑单元生成的 dia 模型；四面体节点。")
    framework("09-fcu-polyhedra", "fcu · 十二连接节点", "fcu", "polyhedra", "paper",
              [2, 2, 2], "等轴测", "Zr 簇生成模型的连接方向凸包；十二连接几何。")
    framework("10-mof5-hybrid", "MOF-5 · 原子与拓扑叠加", "mof5", "hybrid", "paper",
              [2, 2, 2], "等轴测", "透明多面体覆盖原子模型，展示抽象节点对应的局部结构。")

    guest = output / "co2-guest.scene.json"
    molecule_scene(guest, smiles="O=C=O", preset="paper", view="俯视", width=800, height=650)
    length = read_json(inputs / "mof5.analysis.json")["structure"]["cell"][0][0]
    moving_host_target = output / "diffusion-host-base.scene.json"
    make_scene(inputs / "mof5.analysis.json", moving_host_target, repeat=[2, 2, 3],
               preset="porcelain", width=800, height=650, edge_radius=0.13, node_scale=0.18)
    moving_host = read_json(moving_host_target)
    moving_host_path = write_json(output / "diffusion-host.scene.json", moving_host)
    diffusion = output / "11-pore-diffusion.scene.json"
    diffusion_scene(moving_host_path, guest, diffusion,
                    [[length * 0.5, length * 0.5, z * length] for z in [0.05, 0.65, 1.3, 1.95]],
                    frames=36, fps=12)
    entries.append({"id": "11-pore-diffusion", "title": "CO₂ · 孔道内扩散示意", "scene": str(diffusion),
                    "description": "优化后的 CO₂ 刚体沿指定路径移动；36 帧，不对应 MD 时间或扩散系数。",
                    "animation": True})

    surface = new_scene(np.eye(3), "porcelain", width=900, height=650)
    for layer in range(2):
        for i in range(5):
            for j in range(4):
                p = [(i - 2) * 1.4 + (j % 2) * 0.7 + layer * 0.35,
                     (j - 1.5) * 1.21 + layer * 0.3, -layer * 1.05]
                sphere(surface, p, 0.64, "#93A4B4" if layer == 0 else "#687D93", "support")
    sphere(surface, [0, 0, 0.65], 0.43, "#D5A458", "illustrative_active_site")
    surface["camera"]["direction"] = [0.8, -1.8, 1.6]
    surface["provenance"] = {"type": "idealized generic support", "not_a_specific_catalyst": True}
    surface_path = write_json(output / "surface.scene.json", surface)
    snapshots = []
    for frame, label, positions, bonds in [
        (1, "CO approach + adsorbed O", [[-2.2, 0, 3.8], [-2.2, 0, 4.95], [0.8, 0, 1.5]], [[0, 1]]),
        (12, "CO at interface", [[-0.7, 0, 2.1], [-0.7, 0, 3.25], [0.8, 0, 1.5]], [[0, 1]]),
        (24, "CO2 formation (illustrative)", [[0.0, 0, 2.4], [-1.16, 0, 2.4], [1.16, 0, 2.4]], [[0, 1], [0, 2]]),
        (36, "product departure", [[1.4, 0, 4.4], [0.24, 0, 4.4], [2.56, 0, 4.4]], [[0, 1], [0, 2]]),
    ]:
        snapshots.append({"frame": frame, "label": label,
                          "atoms": [{"id": k, "element": e, "position": p}
                                    for k, (e, p) in enumerate(zip(["C", "O", "O"], positions))],
                          "bonds": bonds})
    reaction = output / "12-interface-reaction.scene.json"
    reaction_scene(surface_path, reaction, snapshots, frames=36, fps=12)
    entries.append({"id": "12-interface-reaction", "title": "界面反应 · 接近—成键—离开", "scene": str(reaction),
                    "description": "通用表面上的 CO + O → CO₂ 分镜；原子守恒，步骤为示意，不是机理或过渡态证据。",
                    "animation": True})
    # A second camera recipe demonstrates a geometry-preserving change without reanalysis.
    change_view(host, output / "mof5-along-c.scene.json", instruction="沿c轴看")
    entries.extend(prepare_layers(output))
    entries.extend(prepare_gate_open(output))
    write_json(output / "gallery-plan.json", entries)
    return entries


def prepare_layers(output):
    entries = []
    configurations = [
        ("13-graphene-top", "石墨烯 · 单层蜂窝俯视", 1, "ball-stick", "paper", [0, 0, 1],
         "ASE 理想石墨烯，a=2.46 Å；周期模型与单层俯视。"),
        ("14-graphene-oblique", "石墨烯 · 单层倾斜视角", 1, "sticks", "midnight", [0.65, -1.5, 1.8],
         "深色背景与细杆蜂窝结构；改变相机，不改变碳骨架。"),
        ("15-graphene-bilayer", "石墨烯 · AB 双层堆叠", 2, "ball-stick", "paper", [0.35, -1.7, 1.0],
         "AB 错位、3.35 Å 模型层间距；分层配色展示堆叠，未做结构弛豫。"),
    ]
    for slug, title, count, rep, preset, direction, description in configurations:
        base = output / f"{slug}-base.scene.json"
        target = output / f"{slug}.scene.json"
        layer_scene(base, layers=count, repeat=[8, 8, 1], representation=rep, preset=preset,
                    width=1200, height=900)
        change_view(base, target, direction=direction, kind="cartesian")
        entries.append({"id": slug, "title": title, "scene": str(target),
                        "description": description, "animation": False})
    return entries


def prepare_gate_open(output):
    guest = output / "methane-guest.scene.json"
    molecule_scene(guest, smiles="C", preset="paper")
    scene = output / "16-gate-opening.scene.json"
    gate_open_scene(guest, scene, frames=48, fps=12, width=1000, height=800)
    return [{"id": "16-gate-opening", "title": "柔性 MOF · 分子诱导开门", "scene": str(scene),
             "description": "RDKit 优化甲烷进入金色菱形孔；夹角 24°→90°，框架杆长不变。理想化 gate-opening 示意，非具体 MOF 机理。",
             "animation": True}]


def render_all(output, entries, samples, animations):
    results = []
    for entry in entries:
        target = output / entry["id"]
        if (target / "manifest.json").exists():
            print(f"Already rendered: {entry['id']}", flush=True)
            result = {"image": str(target / "render.png"), "blend": str(target / "scene.blend"),
                      "manifest": str(target / "manifest.json"),
                      "animation": str(target / "animation.gif") if (target / "animation.gif").exists() else None}
        else:
            print(f"Rendering: {entry['id']}", flush=True)
            result = render_scene(entry["scene"], target, samples=32 if entry["animation"] else samples,
                                  animate=animations and entry["animation"], timeout=1800)
        results.append({**entry, **result})
    target = output / "gallery-results.json"
    if not target.exists():
        write_json(target, results)
    from make_gallery import build_gallery
    build_gallery(output, results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--animations", action="store_true")
    parser.add_argument("--samples", type=int, default=64)
    args = parser.parse_args()
    output = args.output.resolve()
    entries = read_json(output / "gallery-plan.json") if args.resume else prepare(output)
    if args.render:
        render_all(output, entries, args.samples, args.animations)
    print(json.dumps({"gallery": str(output), "examples": len(entries)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
