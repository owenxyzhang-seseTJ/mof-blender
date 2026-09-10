"""Local HTML gallery and contact sheet built only from actual Blender outputs."""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def build_gallery(output, entries):
    output = Path(output)
    cards = []
    for entry in entries:
        slug = entry["id"]
        animation = entry.get("animation")
        media = f"{slug}/animation.gif" if isinstance(animation, str) else f"{slug}/render.png"
        cards.append(f'''<article data-category="{'motion' if animation else 'still'}">
        <a class="image" href="{media}"><img src="{media}" alt="{html.escape(entry['title'])}" loading="lazy"></a>
        <div class="body"><small>{'MOTION / 示意动画' if animation else 'STRUCTURE / 结构绘图'}</small>
        <h2>{html.escape(entry['title'])}</h2><p>{html.escape(entry['description'])}</p>
        <nav><a href="{slug}/render.png">PNG</a><a href="{slug}/scene.blend">Blender 源文件</a>
        <a href="{slug}/scene.json">场景参数</a><a href="{slug}/manifest.json">验证记录</a></nav></div></article>''')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>MOF Blender · 示例画廊</title><style>
    *{box-sizing:border-box}body{margin:0;background:#f1f3f3;color:#20313d;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    header{max-width:1440px;margin:auto;padding:70px 40px 30px}.eyebrow{letter-spacing:.2em;font-size:12px;color:#4b7f85;font-weight:700}
    h1{font-size:clamp(30px,5vw,62px);font-weight:650;letter-spacing:-.05em;margin:14px 0 18px}.intro{max-width:840px;line-height:1.9;color:#647781;font-size:16px}
    .filters{display:flex;gap:10px;padding:15px 0 25px}button{background:#fff;border:1px solid #cbd6d8;border-radius:25px;padding:10px 24px;cursor:pointer;color:#47646e}button.active{background:#285e68;color:white;border-color:#285e68}
    main{max-width:1440px;margin:auto;padding:0 40px 70px;display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
    article{background:#fff;border:1px solid #e0e7e8;border-radius:16px;overflow:hidden;box-shadow:0 8px 30px #243e4b06;transition:transform .2s}article:hover{transform:translateY(-3px)}
    .image{display:block;aspect-ratio:4/3;background:#fff;overflow:hidden}.image img{width:100%;height:100%;object-fit:contain}.body{padding:24px}small{font-size:10px;letter-spacing:.12em;color:#5c9098}h2{font-size:20px;font-weight:600;margin:10px 0}p{line-height:1.7;font-size:13px;color:#657781;min-height:48px}nav{display:flex;gap:12px;flex-wrap:wrap;padding-top:12px;border-top:1px solid #eef1f2}a{color:#35727c;font-size:12px;text-decoration:none}a:hover{text-decoration:underline}footer{padding:0 40px 40px;max-width:1440px;margin:auto;color:#70818b;font-size:12px;line-height:1.8}
    @media(max-width:1000px){main{grid-template-columns:repeat(2,1fr)}}@media(max-width:620px){main{grid-template-columns:1fr;padding:0 20px 40px}header{padding:40px 20px 20px}}
    </style><header><div class="eyebrow">MOF BLENDER / 01</div><h1>从原子结构到框架与动态示意</h1>
    <div class="intro">真实 Blender 输出，覆盖分子、三维框架、二维 COF、石墨烯、拓扑多面体和动态分镜。三套原创材质与光照预设，全部保留可编辑场景、参数和来源记录。点击图片可查看原图或动画。</div>
    <div class="filters"><button class="active" onclick="filterCards('all',this)">全部示例</button><button onclick="filterCards('still',this)">结构与材质</button><button onclick="filterCards('motion',this)">扩散、反应与开门</button></div></header><main>'''
    page += "\n".join(cards)
    page += '''</main><footer>框架为 AuToGraFS 生成模型，拓扑名称为其分析候选；小分子经 RDKit 力场优化。扩散路径、反应步骤与开门过程为示意分镜，不代表实验轨迹、分子动力学结果或机理证明。<br>独立实现；ChemBlender 2.0 用于架构和功能参考，未复制其源码、节点资产或默认渲染设置。</footer>
    <script>function filterCards(category,button){document.querySelectorAll('article').forEach(e=>e.style.display=category==='all'||e.dataset.category===category?'':'none');document.querySelectorAll('button').forEach(e=>e.classList.toggle('active',e===button))}</script></html>'''
    (output / "index.html").write_text(page, encoding="utf-8")
    tile_w, tile_h, gap = 560, 470, 24
    columns, rows = 3, math.ceil(len(entries) / 3)
    canvas = Image.new("RGB", (columns * tile_w + gap * 4, rows * tile_h + gap * (rows + 1) + 95), "#EDF1F2")
    draw = ImageDraw.Draw(canvas)
    font_paths = ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
                  "/System/Library/Fonts/Supplemental/Songti.ttc", "/System/Library/Fonts/Helvetica.ttc",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    font = next((p for p in font_paths if Path(p).exists()), None)
    title_font = ImageFont.truetype(font, 30) if font else ImageFont.load_default()
    label_font = ImageFont.truetype(font, 21) if font else ImageFont.load_default()
    draw.text((gap, 24), f"MOF BLENDER / {len(entries)} EXAMPLES", fill="#213F4B", font=title_font)
    for index, entry in enumerate(entries):
        x = gap + (index % columns) * (tile_w + gap)
        y = 95 + gap + (index // columns) * (tile_h + gap)
        draw.rounded_rectangle((x, y, x + tile_w, y + tile_h), radius=14, fill="white")
        with Image.open(entry["image"]) as im:
            background = Image.new("RGB", im.size, "white")
            background.paste(im, mask=im.getchannel("A") if "A" in im.getbands() else None)
            thumb = ImageOps.contain(background, (tile_w, 395))
            canvas.paste(thumb, (x + (tile_w - thumb.width) // 2, y + (395 - thumb.height) // 2))
        draw.text((x + 22, y + 410), entry["title"].replace("₂", "2"), fill="#284B58", font=label_font)
    canvas.save(output / "contact-sheet.png")


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1])
    build_gallery(root, json.loads((root / "gallery-results.json").read_text()))
