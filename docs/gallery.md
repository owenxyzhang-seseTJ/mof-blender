# Rendered examples / 渲染示例

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

## Ethanol / optimized ball-and-stick

**乙醇 · 优化球棍模型**

ETKDG conformers optimized with MMFF94s; soft lighting on a white background.

RDKit ETKDG 多构象 + MMFF94s；白底与柔和高光。

![Ethanol / optimized ball-and-stick](assets/01-ethanol.jpg)

## Caffeine / space filling

**咖啡因 · 空间填充模型**

An optimized caffeine conformer shown with van der Waals spheres and a matte finish.

RDKit 优化构象；范德华球面与哑光材质。

![Caffeine / space filling](assets/02-caffeine.jpg)

## MOF-5 / atomic pore view

**MOF-5 · 晶体球棍**

AuToGraFS-generated MOF-5, viewed along a, with a 2 × 2 × 2 display supercell.

AuToGraFS 生成模型；沿 a 轴观察孔道，2×2×2 超胞。

![MOF-5 / atomic pore view](assets/03-mof5-atoms.jpg)

## pcu / six-connected polyhedra

**pcu · 六连接节点多面体**

Octahedral hulls follow the six physical connection directions; thin rods represent linkers.

由实际连接方向构建八面体，连接子抽象为细杆。

![pcu / six-connected polyhedra](assets/04-mof5-polyhedra.jpg)

## pcu / dark node-and-edge net

**pcu · 深色节点线框**

A dark-blue pcu network with teal nodes and warm rods, using the midnight preset.

深蓝背景、青绿色节点与暖金连接线。

![pcu / dark node-and-edge net](assets/05-mof5-net.jpg)

## 2D COF / atomic monolayer

**二维 COF · 单层原子结构**

A generated boroxine COF monolayer with an hcb candidate net, viewed along c.

硼氧六环 COF 的 hcb 生成模型；单层俯视。

![2D COF / atomic monolayer](assets/06-cof-atoms.jpg)

## hcb / three-connected polygons

**hcb · 三连接平面节点**

Three-connected planar nodes remain triangles; no fictitious pyramid apex is added.

三连接节点保持三角形，不增加虚构的锥顶。

![hcb / three-connected polygons](assets/07-cof-polygons.jpg)

## dia / four-connected tetrahedra

**dia · 四连接三维框架**

A generated organic dia framework with tetrahedral connection-direction hulls.

有机四连接构筑单元生成的 dia 模型；四面体节点。

![dia / four-connected tetrahedra](assets/08-dia-tetrahedra.jpg)

## fcu / twelve-connected polyhedra

**fcu · 十二连接节点**

A generated Zr-cluster fcu framework; convex hulls follow twelve connection directions.

Zr 簇生成模型的连接方向凸包；十二连接几何。

![fcu / twelve-connected polyhedra](assets/09-fcu-polyhedra.jpg)

## MOF-5 / atoms and topology

**MOF-5 · 原子与拓扑叠加**

Transparent node polyhedra overlay atoms to show the relation between both representations.

透明多面体覆盖原子模型，展示抽象节点对应的局部结构。

![MOF-5 / atoms and topology](assets/10-mof5-hybrid.jpg)

## CO2 / schematic pore diffusion

**CO₂ · 孔道内扩散示意**

Rigid optimized CO2 moves along authored pore waypoints; no MD time or diffusivity is implied.

优化后的 CO₂ 刚体沿指定路径移动；36 帧，不对应 MD 时间或扩散系数。

![CO2 / schematic pore diffusion](assets/11-pore-diffusion.gif)

## Interface / authored reaction

**界面反应 · 接近—成键—离开**

An authored CO + O to CO2 sequence on a generic support, conserving atom identities.

通用表面上的 CO + O → CO₂ 分镜；原子守恒，步骤为示意，不是机理或过渡态证据。

![Interface / authored reaction](assets/12-interface-reaction.gif)

## Graphene / monolayer top view

**石墨烯 · 单层蜂窝俯视**

Ideal graphene with a = 2.46 angstrom, shown as a periodic monolayer model.

ASE 理想石墨烯，a=2.46 Å；周期模型与单层俯视。

![Graphene / monolayer top view](assets/13-graphene-top.jpg)

## Graphene / inclined monolayer

**石墨烯 · 单层倾斜视角**

An inclined camera and pale-blue carbon sticks reveal the honeycomb lattice on a dark background.

深色背景与细杆蜂窝结构；改变相机，不改变碳骨架。

![Graphene / inclined monolayer](assets/14-graphene-oblique.jpg)

## Graphene / AB bilayer

**石墨烯 · AB 双层堆叠**

An AB bilayer with a chosen 3.35 angstrom separation and per-layer colors; no slab relaxation.

AB 错位、3.35 Å 模型层间距；分层配色展示堆叠，未做结构弛豫。

![Graphene / AB bilayer](assets/15-graphene-bilayer.jpg)

## Flexible MOF / schematic gate opening

**柔性 MOF · 分子诱导开门**

An optimized methane guest enters a front-facing ideal hinged pore as the angle changes 24° to 90°.

正面孔口：分子从左上方接近，随后进入并撑开菱形孔；框架杆长及客体构型保持不变。理想化示意，非具体 MOF 机理。

![Flexible MOF / schematic gate opening](assets/16-gate-opening.gif)
