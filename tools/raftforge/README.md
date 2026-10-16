# RAFTFORGE A11 — Local Asset Factory for RAFTBOUND

A working **free, offline** procedural 3D prop generator for a stylized ocean survival game. Outputs glTF 2.0 GLB meshes, PBR-ready per-material metallic/roughness parameters, supplementary procedural wood albedo/roughness/normal maps, deterministic JSON QA, and optional **actual VTK offscreen renders** in 3 camera angles.

> Scope: hard-surface **props**. Not an AI text-to-3D service and **not yet** a high-quality character creator. Real Blender retopology, rigging and animation are a separate pipeline. Blender finishing script is provided but not verified here.

## Installation (no paid services)

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
# Optional preview render: pip install vtk
```

## Build three art-directed GLB assets

```bash
python -m raftforge batch --presets presets --out output
python -m raftforge batch --presets presets --out output --render  # optional VTK installed
python -m raftforge build --recipe presets/raft_tile.json --out output
python -m raftforge validate output/foundation_2m_art.glb --type raft_tile
python -m raftforge variants --recipe presets/raft_tile.json --count 4 --out output/variants
python -m unittest discover -s tests -v
```

Modify the preset JSON, regenerate. Example: `{"type":"raft_tile","seed":812,"planks":8,"weathering":0.73,"detail":3}`. Different seeds generate unique consistent variants; repeatable per seed.

### Models included

| ID | What it creates | Art direction | Budget |
| --- | --- | --- | --- |
| `raft_tile` | 2×2-m modular raft floor | offset planks, nails, lashings, beams, wear | 4,500 tris |
| `storage_chest` | raised wood chest | arched planked lid, iron bands, brass latch, handles | 6,000 tris |
| `compact_grill` | freestanding cooking grill | tapered steel bowl, legs, grill grid, embers, handles | 7,000 tris |

Materials batch by palette: 7 draw groups per model. The models are **not** automatically copied into the game; use a deliberate import / asset approval pass to avoid replacing existing assets before visual evaluation. For preview evidence, `output/contact-sheet.png` is a real rendering of exported GLBs (VTK CPU/offscreen, **not Blender or WebGL**).

### Quality gates / limitations

- Verified locally: GLB round-trip, finite geometry, size, triangle and draw-batch caps, reproducible asset seeds, procedural wood map creation.
- Not yet verified: PBR texture UV assignment inside GLB (wood image maps are generated **separately**), in-game lighting, gameplay collider parity, Blender .blend generation, real GPU performance, rigging or AAA-level asset art.
- Uses `trimesh`, `numpy`, `scipy`, `Pillow`; optional `vtk` for preview and Blender (free) for finishing. **No online API, model hosting, token, subscription or per-generation credits.** Running on hardware still uses compute resources and electricity.
- License: this project's **new tool source** is MIT. It does not change the license of any existing RAFTBOUND project or third-party models.

### Optional Blender finishing

```bash
blender -b --python blender/finish_assets.py -- --input output/storage_chest_art.glb --output output/blender_finished --render
```

This writes editable `.blend` and a Cycles render. Run in an environment with Blender installed; this step has not been validated in this environment.

## What a full no-fee asset pipeline needs next

1. Shared UV atlas and baked PBR textures (currently only wood maps are generated); visual QA and topology cleanup in Blender.
2. A curated shape/component library with reusable materials and sockets, more preset families (purifier, planter, shark cage, raft rail, anchor).
3. Separate **character** pipeline: reference sheets → Blender modeling / optional locally-run open models (GPU- and license-dependent) → retopology → rig and deformation QA. Procedural primitives by themselves are not an adequate replacement for sculpting high-quality anatomy.
4. Turntable render, visual QA and live Three.js integration before promoting replacements into the game.

See [`output/contact-sheet.png`](output/contact-sheet.png) for the current models.
