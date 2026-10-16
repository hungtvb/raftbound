# RAFTFORGE A13 — Character Art Lab

**Fixes the bad process, not just the polygon count.** Current A07 model is art quality **NEEDS_FIX**, even though its GLB is parseable, skinned and numerically valid.

## Why this exists

The old process optimized mesh/rig tests and renamed many versions without checking whether the sailor looked like a convincing character. The new process requires *real* multi-angle renders, rig preservation, consistent human visual review and a comparison to a locked baseline before an asset may be used.

## Run (offline, no paid APIs)

```bash
pip install trimesh numpy Pillow vtk
python -m character_lab audit input/survivor_sailor_skinned_A07.glb --report output/baseline.json
python -m character_lab compare input/survivor_sailor_skinned_A07.glb --out output/baseline-board.png
python -m character_lab fit input/survivor_sailor_skinned_A07.glb --out output/fitted-character.glb --height 1.8
python -m unittest discover -s tests -v
```

### Import a professional CC0 base (not another procedurally sculpted head)

- Quaternius [Universal Base Characters](https://quaternius.com/packs/universalbasecharacters.html) **Standard** download is free/name-your-price, 6 humanoid body shapes, glTF, rigged/retarget-friendly topology, ~13k tris, licensed CC0. 
- Use its GLB if supplied. Standard ZIP often supplies `.gltf` + `.bin` + textures; for that, use **Blender** (`File > Import > glTF 2.0` then `File > Export > glTF 2.0 > GLB`) first. The source `.blend` may be in a separately priced Source package; **do not depend on it**.
- Or use a legally cleared, similarly well-authored rigged base. Never download undisclosed proprietary 3D model files.
- Input a properly rigged `.glb` as a **new candidate** and audit it.
- Fitting wraps model under a scaled root. **Original skeletal nodes, animation channels, binary geometry and skin weight buffers remain unchanged**. It does not magically retarget custom A07 cast animations; validate actual action clips in Three.js before swapping.

```bash
python -m character_lab audit /path/to/approved-base.glb
python -m character_lab fit /path/to/approved-base.glb --out output/base-1p8m.glb --height 1.8 --yaw 180
python -m character_lab compare output/base-1p8m.glb --reference input/survivor_sailor_skinned_A07.glb --out output/compare.png
```

## Hard art gates

The six artistic qualities **silhouette, face, hands, clothing, game-distance readability, animation deformation** each must score **at least 4/5**. Review is from real renders, at playable distance, plus actual animation. A visual **human judgment is required**; a geometry parser is not a beauty model.

```json
{
  "silhouette": 4,
  "face": 4,
  "hands": 4,
  "clothing": 4,
  "in_game_readability": 4,
  "animation_deformation": 4,
  "reviewer_notes": "I reviewed orthographic and 3/4 turnarounds plus idle/walk/cast deforming in Three.js."
}
```

```bash
python -m character_lab review output/base-1p8m.glb --scores approved-human-review.json --out output/acceptance.json
```

Only after successful visual review and runtime animation testing may the asset replace the current sailor. The generated board is a static QA aid; it does **not** animate weighted skin or simulate real gameplay in the VTK renderer. Never call a static render proof of animation correctness.

## Time-saving release policy

1. **Pick a strong pre-rigged silhouette first** from licensed CC0 asset packs; avoid code-modeled heads and fingers.
2. Generate one small candidate set (up to 3), *not* A04, A05, A06, etc. without art decisions.
3. Make same-view A/B boards. Reject bad silhouette, face or hands *before* adding surface detail/rig cycles.
4. Preserve scene normalization and bone contract; test retargeted animation before game integration.
5. Change one measurable issue per pass, maintain baseline; do not use milestone labels as quality evidence.
6. Sign off at 1080p and ~120px-tall in-game avatars, as well as multi-angle renders. Technical and art gates are **separate**.

**Orientation:** RAFTBOUND uses -Z forward. Source bases facing +Z need `--yaw 180`; this rotates only the scene parent, preserving original skin and animation node IDs.

**Out of scope:** the kit does not create an artist-quality human from primitives. It optimizes selection, rig-safe fitting, reviews, and iterations using legitimately sourced rigged meshes. 
