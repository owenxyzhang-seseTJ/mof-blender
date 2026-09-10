"""Publish compact previews and path-free verification metadata from a rendered gallery."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

TITLES = [
    "Ethanol / optimized ball-and-stick", "Caffeine / space filling",
    "MOF-5 / atomic pore view", "pcu / six-connected polyhedra",
    "pcu / dark node-and-edge net", "2D COF / atomic monolayer",
    "hcb / three-connected polygons", "dia / four-connected tetrahedra",
    "fcu / twelve-connected polyhedra", "MOF-5 / atoms and topology",
    "CO2 / schematic pore diffusion", "Interface / authored reaction",
    "Graphene / monolayer top view", "Graphene / inclined monolayer",
    "Graphene / AB bilayer", "Flexible MOF / schematic gate opening",
]

CAPTIONS = [
    "ETKDG conformers optimized with MMFF94s; soft lighting on a white background.",
    "An optimized caffeine conformer shown with van der Waals spheres and a matte finish.",
    "AuToGraFS-generated MOF-5, viewed along a, with a 2 × 2 × 2 display supercell.",
    "Octahedral hulls follow the six physical connection directions; thin rods represent linkers.",
    "A dark-blue pcu network with teal nodes and warm rods, using the midnight preset.",
    "A generated boroxine COF monolayer with an hcb candidate net, viewed along c.",
    "Three-connected planar nodes remain triangles; no fictitious pyramid apex is added.",
    "A generated organic dia framework with tetrahedral connection-direction hulls.",
    "A generated Zr-cluster fcu framework; convex hulls follow twelve connection directions.",
    "Transparent node polyhedra overlay atoms to show the relation between both representations.",
    "Rigid optimized CO2 moves along authored pore waypoints; no MD time or diffusivity is implied.",
    "An authored CO + O to CO2 sequence on a generic support, conserving atom identities.",
    "Ideal graphene with a = 2.46 angstrom, shown as a periodic monolayer model.",
    "An inclined camera and pale-blue carbon sticks reveal the honeycomb lattice on a dark background.",
    "An AB bilayer with a chosen 3.35 angstrom separation and per-layer colors; no slab relaxation.",
    "An optimized methane guest enters a front-facing ideal hinged pore as the angle changes 24° to 90°.",
]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rgb_image(path):
    with Image.open(path) as image:
        result = Image.new("RGB", image.size, "white")
        result.paste(image, mask=image.getchannel("A") if "A" in image.getbands() else None)
    return result


def triptych(frames, target, labels):
    indices = [0, len(frames) // 2, len(frames) - 1]
    tile_w, tile_h = 600, 520
    canvas = Image.new("RGB", (tile_w * 3, tile_h), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=21)
    for panel, (index, label) in enumerate(zip(indices, labels)):
        image = ImageOps.contain(rgb_image(frames[index]), (tile_w, tile_h - 45))
        canvas.paste(image, (panel * tile_w + (tile_w - image.width) // 2, 0))
        draw.text((panel * tile_w + 25, tile_h - 35), label, font=font, fill="#315268")
    canvas.save(target, quality=92)


def export_gallery(source, docs):
    source, docs = Path(source), Path(docs)
    assets = docs / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    entries = json.loads((source / "gallery-results.json").read_text())
    summary, sections = [], []
    for entry in entries:
        slug = re.sub(r"-r\d+$", "", entry["id"])
        index = int(slug.split("-")[0]) - 1
        title = TITLES[index]
        manifest = json.loads(Path(entry["manifest"]).read_text())
        assert manifest["status"] == "complete", slug
        for artifact in manifest["artifacts"]:
            assert sha256(artifact["path"]) == artifact["sha256"], artifact["path"]
        target = assets / f"{slug}.jpg"
        ImageOps.contain(rgb_image(entry["image"]), (1200, 900)).save(target, quality=90)
        record = {"id": slug, "title": title, "source_scene_sha256": manifest["source_scene_sha256"],
                  "geometry_sha256": manifest["geometry_sha256"], "audit": manifest["audit"],
                  "preview": target.name, "preview_sha256": sha256(target)}
        media = f"assets/{slug}.jpg"
        if entry.get("animation"):
            frames = sorted((Path(entry["image"]).parent / "frames").glob("frame_*.png"))
            scene = json.loads(Path(entry["scene"]).read_text())
            assert len(frames) == scene["animation"]["frames"], slug
            images = [ImageOps.contain(rgb_image(p), (800, 650)) for p in frames]
            fps = scene["animation"]["fps"]
            # GIF has centisecond timing. Distribute rounding to preserve total duration.
            durations = [10 * (round((i + 1) * 100 / fps) - round(i * 100 / fps))
                         for i in range(len(images))]
            target = assets / f"{slug}.gif"
            images[0].save(target, save_all=True, append_images=images[1:], duration=durations,
                           loop=0, disposal=2, optimize=True)
            with Image.open(target) as gif:
                duration = 0
                for frame in range(gif.n_frames):
                    gif.seek(frame)
                    duration += gif.info.get("duration", 0)
                record.update(png_frames=len(frames), gif_frames=gif.n_frames,
                              duration_ms=duration, fps=fps, animation=target.name,
                              animation_sha256=sha256(target))
            media = f"assets/{slug}.gif"
            if slug == "16-gate-opening":
                triptych(frames, assets / "gate-opening-stages.jpg",
                         ["Closed pore / approach", "Guest entry / opening", "Open pore / guest inside"])
        sections.append(f"## {title}\n\n**{entry['title']}**\n\n{CAPTIONS[index]}\n\n{entry['description']}\n\n"
                        f"![{title}]({media})\n")
        summary.append(record)
    ImageOps.contain(rgb_image(source / "contact-sheet.png"), (1776, 3200)).save(
        assets / "contact-sheet.jpg", quality=90)
    (assets / "render-verification.json").write_text(json.dumps(summary, indent=2) + "\n")
    text = """# Rendered examples / 渲染示例

[English README](../README.md) · [中文说明](../README.zh-CN.md) · [Validation / 验证](validation.md)

These are actual Blender Cycles renders. All 16 scenes are reproduced by
`scripts/create_examples.py --output output/new-gallery --render --animations`.
The local gallery also contains editable `.blend`, scene JSON, original PNG frames and manifests.
Public previews are resized copies; [render verification](assets/render-verification.json)
records their hashes, original render settings and animation durations without local file paths.

全部为实际 Blender 输出，共 16 个示例，含 3 个动画。四组框架是 AuToGraFS 生成的演示模型，
不是实验精修结果；石墨烯是理想化模型。拓扑名称保留为分析候选。小分子使用 RDKit 优化。
扩散、反应、开门动画均为示意，不是动力学轨迹或机理证明。

The three presets are **paper**, **porcelain**, and **midnight**. Gate opening uses a
front-on pore view: +z points toward the camera, +y points upward, and the guest approaches
from the upper left before entering the aperture. The hinge changes 24° → 90° while
framework strut lengths and molecular internal distances remain constant.

![Gate-opening stages / 开门过程](assets/gate-opening-stages.jpg)

"""
    (docs / "gallery.md").write_text(text + "\n".join(sections), encoding="utf-8")
    print(json.dumps({"examples": len(summary), "animations": sum("animation" in x for x in summary),
                      "assets": str(assets)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--docs", type=Path, default=Path("docs"))
    args = parser.parse_args()
    export_gallery(args.source, args.docs)
