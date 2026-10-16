# RAFTBOUND — Art Direction & 3D Model Architecture v0.1

## 1. Visual target

**Stylized semi-realistic, readable from a third-person camera.** The visual mood follows the attractive approachable aesthetic of ocean survival games such as Raft: saturated turquoise sea, warm lumber, slightly exaggerated silhouette, painterly weathered surfaces. Original art only; don't trace or rip Raft assets.

- Geometry: medium-poly, bevelled edges, visible wood thickness, readable silhouettes; no hyperreal micro detail on pickup items.
- Materials: metallic-roughness PBR with high roughness for wood/rope, moderate roughness for used metal. Prefer restrained varied colors and wood grain details; textures in next pass.
- Palette: honey wood `#BE8550`, light timber `#D4A46F`, weathered dark wood `#68452C`, hemp `#D5B27B`, steel `#8C9B9D`, oxidized teal `#73C7CF`, young leaves `#83B660`, ocean `#3DAFBF`.
- Lighting: bright sun + soft cool sky, clear shadows, depth fog, careful water specular. Target readability at 1080p.

## 2. Scale, coordinate and asset contract

- Game: **1 unit = 1 meter**, right-handed **Y up**, **-Z forward** glTF/Three.js.
- Blender authoring uses native Z-up, glTF import/export converts to/from Y-up.
- Floor tile logical size **2 m × 2 m**, snap socket increments exactly `2.0 m` on X/Z.
- Floor walkable top at approx. **Y=0.075 m**, with bottom timbers below datum for raft flotation.
- Pivot: tiles near upper surface center; stations at center of their ground footprint; pickup debris at visible center; hand-held net at grip end of handle.
- Structural collisions are game primitives (AABB/capsule/cylinder), not render triangle-mesh colliders. Water physics independent from mesh geometry.
- Separate IDs for gameplay and visual variations: `foundation_2m`, `compact_grill` etc. No name-dependent mesh lookup within a GLB.

## 3. Category architecture

| Category | Model family | Scope | Current A02 | Next A02/A03 |
|---|---|---|---|---|
| Modular raft | floor, damaged floor, reinforced floor, railing, half-wall, stairs, roof, anchor | 2-m grid and construction ghosts | floor | railing, wall, anchor |
| Player/equipment | stylized survivor body, hands, backpack, net, fishing rod, spear, hammer, paddle | Rigged humanoid with shared skeleton, separate tool sockets | net | survivor + rig/animations |
| Floating resources | plank, branches, leaves, plastic, barrel, scrap, rope, seaweed | Instancing, buoyancy, orientation variants | 6 resources | scrap metal, rope, fish |
| Production | grill, purifier, planter, research bench, smelter, battery, water tank | 1–2 tile footprints; animated subassemblies | grill/purifier/planter | research/smelter |
| Storage/decoration | wooden chest, crates, flags, buoy, lanterns, sail | LOD and optional animation | chest/buoy | lantern/sail |
| Wildlife | shark, small fish, gull, turtle | skeleton/shape keys, swim cycles, AI sockets | none | shark rig + swim |
| World | floating island, reef, submerged wreck, weather props | streaming chunks, fog LOD | none | island blockout |

## 4. Packaging & game data

```text
asset_pack/
  glb/foundation_2m.glb
  glb/salvage_net_tool.glb
  glb/compact_grill.glb
  ...
  asset_manifest.json
  asset_contract.json
  blender/build_scene.py
  src/build_meshes.py
  previews/
```

**Mesh object names:** `RB_<category>_<asset>_<variant>_<lod>`, e.g. `RB_BUILD_FOUNDATION_A_LOD0`. Assets are loaded individually; materials are combined by name, and geometries are batched by material before GLB export to reduce draw calls. Avoid multiple unique copies of shared material data once integration is ready.

**Scene structure:** `RB_ASSET_PACK_A02` root collection with one `RB_<ASSET>` collection per item; naming also supports library Asset Browser tags when finalized.

## 5. Production pipeline

1. **Spec/model card:** purpose, silhouette, dimensions, collision proxy, attach points, triangle budget.
2. **Blender blockout:** build correct 1:1 geometry, place origin and node pivots, check all major gameplay views.
3. **Blender detail pass:** beveled edges, custom wood profiles, minor damage, straps/rivets/knots, manifold checking.
4. **UV/PBR:** pack 0–1 UVs, texture set/atlas at 1K or 2K (albedo, roughness, normal; ORM as needed).
5. **Rig/animation:** only animated props/creatures; avoid unnecessary bones in static assets.
6. **Export:** `.blend` master -> `.glb`, apply rotation/scale carefully, optimize using glTF Transform/meshopt/KTX2 where available.
7. **Visual QA:** 360° render, front/side/top, material lighting stress test, in-game silhouette at real camera distance.
8. **Runtime QA:** collision, snap, cast shadow, sizes, loading, draw calls, FPS, no glTF warnings; screenshot regression.

## 6. Triangle budgets (LOD0 targets)

| Asset family | Target tris LOD0 | LOD1 / far target | Texture |
|---|---:|---:|---|
| Standard tile | 3,500 | 900 | shared 1K atlas |
| Floating debris | 2,500 max | 300 | shared 1K atlas |
| Station (grill/purifier/planter) | 6,000 max | 1,300 | shared 1K/2K atlas |
| Rigged survivor | 18,000–25,000 | 6,000–10,000 | 2K character |
| Shark | 8,000–14,000 | 2,000–4,000 | 1K/2K creature |
| Island hero chunk | variable | streamed LOD / instancing | multi atlas |

A02 individually meets tile/resource/station model targets based on triangles in `asset_manifest.json`. This does **not** establish game-wide performance; GPU tests are required. Estimated first-load targets: compressed gameplay asset set < 15 MB on initial approach and responsive gameplay on mainstream desktops after integration.

## 7. Animation contracts

- Survivor: `idle`, `walk`, `run`, `cast_start`, `cast_loop`, `cast_end`, `craft`, `eat`, `drink`, `hit`, `swim`, `climb`, `death`; forward -Z and root grounded.
- Net tool: parent socket `hand.R` or `ToolSocket_R`, net target chain including head and catcher; visual net spring animation independent from trajectory simulation.
- Stations: `grill_on`, `grill_off`, `water_pour`, `crop_grow`, `chest_open`; animations ideally separate clips/actions.
- Wildlife: shark `swim_loop`, `turn`, `approach`, `bite`, `retreat` with mouth jaw bone.

## 8. Acceptance checklist — each model

- [ ] Recognizable silhouette at normal camera distance and final game FOV.
- [ ] 1:1 meters and correct pivot; floor snap without overlaps/gaps.
- [ ] Geometry normals/faces valid and within triangle budget.
- [ ] PBR material values plausible; no missing texture references.
- [ ] No accidental collision between interaction shape and player movement.
- [ ] Export/import through Blender retains visuals, materials, transforms, orientation.
- [ ] Model renders correctly under both sunny noon and sunset lights.
- [ ] Production assets have organized source `.blend` and GLB, naming/version stable.
- [ ] Runtime load, shadows, draw calls, and screenshots tested.

## 9. Milestones

**A02 — done:** initial 12 GLB meshes, one assembled scene, metadata, contact-sheet QA, Blender finishing script. Source `.blend` *pending running Blender*.

**A02 — quality pass:** refine individual silhouettes, author UV atlas and PBR texture maps in Blender, real Blender Cycles turnaround renders, foundation seamless tiling variants, additional modular construction parts, item animations, integrate assets into Three.js.

**A03 — characters and wildlife:** survivor rig + cast/retrieve motions, shark rig + bite states, fish/gulls, basic interaction animations, ocean shader upgrade.

**A04 — environments and release validation:** islands, wrecks, weather, camera/LOD optimization, asset streaming, comprehensive visual/gameplay QA.
