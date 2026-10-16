# RAFTBOUND A02 — asset QA handoff

## What changed from A01

- `foundation_2m`: six independent chamfered boards with varied height, grain scoring, nail heads, cross-beams, rope lashings, and end-grain trim. 4,384 triangles (A01: 2,176).
- `salvage_net_tool`: tapered shaft, decorative bound grip, reinforced collar and hoop, 16 radial cords, four lateral lashing rings. 4,828 triangles (A01: 3,312).
- Remaining 10 GLB files retained A01 geometry; each re-exported from the procedural generator for a coherent A02 release.
- The starter 3×3 raft scene, asset contact sheet, and individual mesh preview images were regenerated from the exported model geometry.

## Asset constraints

- Coordinates: right-handed, **Y up**, meter units; view forward **-Z**.
- Floor module snap distance: **2.0 m**, local pivot at module center.
- PBR metallic-roughness color material factors; **not textured**.
- Target triangle budgets: ~5k per detailed floor/net model, <=6k per workstation. Geometry must have valid bounding boxes and no non-finite vertices.

## Verification run

- `python tests/validate_assets.py` — PASS for 12 files, their triangle counts, material references, scene, bounds and asset contracts.
- `node ../raftbound-game-A02/tests/glb.test.js` — PASS for 10 runtime GLB files and their binary attribute buffers.
- `node ../raftbound-game-A02/tests/asset-integration.test.js` — PASS for 10 real assets loaded and render calls with a mocked WebGL context.
- **Not complete:** native Blender save/export/render, live GPU visual approval, UV maps, high-resolution PBR textures, authored LODs, collision geometry and animations.

## Blender steps (Blender 4.2+ installed separately)

```bash
python src/build_meshes.py
python src/build_demo.py
python src/render_previews.py
python tests/validate_assets.py
blender --background --python blender/build_scene.py -- --source ./glb --output ./blender-out
```

The Blender script stages imported GLB objects in editable asset collections, adds a studio environment, saves an A02 `.blend` file and triggers a Cycles gallery render. Execution must be verified on a machine with Blender installed; those Blender outputs are **not included** here.
