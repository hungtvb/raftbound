---
name: raftforge-blueprint-first
description: Blueprint-first Blender 3D production skill: single-source geometry, real four-angle reference boards, specialist review, and strict before/after artistic acceptance for RAFTBOUND characters, props and environments.
---

# RAFTFORGE blueprint-first Blender production

Follow this skill whenever building, repairing, improving or reviewing character,
prop or architectural-environment meshes for RAFTBOUND. It formalizes the
**Stage 00–05** production pattern and prevents fake progress from repeatedly
renaming unsatisfactory model variants.

## 0. Identify the artifact and lock the source of truth

- Define **one** exact editable 3D source (Blender scene or IFC/CAD/BIM contract)
  and a versioned JSON blueprint with dimensions, orientation, known licenses,
  proportions, target silhouette, materials, expected animation and budgets.
- For architecture, use BIM/IFC units and level markers, CAD dimensions, CSG
  solids and section locations. For characters, use actual mesh, rest skeleton,
  vertex weights and rigged accessories, *not just a root scale*.
- Record baseline GLB SHA-256 and requested alterations. Do not treat AI image
  generation as real mesh editing or a source of dimensional truth.
- Do not start iterative sculpting until the art-direction or target reference
  is unambiguous enough to evaluate.

## 1. Build/prove the editable geometry

- Use Blender and legally cleared source topology or OpenBIM/CAD if appropriate.
- Keep geometry, rig, units, UVs and PBR materials consistent. Export real
  GLB, reload and audit. Preserve source identity, joints and scene origin.
- If an external AI image-to-3D generator is suggested, test actual pretrained
  inference and license before claiming it works; mock commands are not proof.
- Reject nonmanifold catastrophic errors, degenerate bones, missing skinning,
  wrong world axes, geometry outside bounds and visibly floating attachments.

## 2. Four-tile reference contact sheet

- Render FRONT / THREE-QUARTER / BACK / TOP from the **actual exported GLB**.
- Lock lighting, camera location, focal target and camera framing for baseline
  and candidate **together**. Individual auto-zoom can hide body-scale regressions.
- Create 2×2 contact sheet for each plus a direct before/after matrix.
- For gameplay, show a separate small third-person game-distance sample.
  Do not label an offline VTK shot as a live screenshot from the game.
- ImageGen/Nano Banana may produce optional labeled concept art, but it cannot
  establish whether an exported mesh/rig exists or is good.

## 3. Four specialists and an independent master reviewer

Roles, not provider requirements:
1. **Blueprint + silhouette:** proportions, anatomy/style, 4-view references.
2. **Geometry + rig:** Blender topology, seams, clothing/props and skinning.
3. **Surface/PBR:** UV atlas, shader response, material contrast and licenses.
4. **Motion + runtime:** real walk/idle/action curves, attachments and device FPS.

The reviewer owns the contract and merge decision, but not all implementation.
When connected specialist agents exist, work may proceed in parallel **only
on disjoint files/outputs**. Without parallel agents, execute the four reviews
sequentially; never pretend that four external Gemini workers were started.
Never require a specific proprietary model version from an example prompt.

## 4. Real showcase and cutaways

- Render equal-exposure, equal-distance images. For buildings: measure scale,
  section A-A, roof/structural joints and world Z datums; only assert sections
  built if Blender actually produced them.
- For characters: render front/3/4/back/top AND skinned idle/walk/action tests.
  Ensure correctly positioned hands, attached gear and no obvious clipping.
- A physical-distance test is not a signed triangle-collision test; record
  limitations. No passing GLB parse test grants artistic approval.

## 5. Before/after matrix and RELEASE GATE

Required artifacts:
- editable authoritative source or pinned input identifier + SHA-256;
- blueprint JSON revision;
- before GLB, after GLB, consistent 4-tile renders;
- progress matrix and machine-readable metric report;
- 120px-ish game-readability evidence / section cuts as applicable;
- rig/animation and real runtime QA for any player character;
- human six-axis art review (silhouette, face, hands, clothing,
  in-game readability, animation deformation) for characters.

If a character has fewer than **4/5** in any art dimension, verdict
**NEEDS_ART_REWORK**, regardless of tests. Architectural thresholds should be
separately specified in the blueprint (accuracy to dimensions, structural
realism, UV density, environment composition, camera consistency).

At most **three** candidates per iteration. Explicitly record whether each
candidate improves the user-visible defect; do not create A15, A16, A17 just
because code changed. If no candidate improves the silhouette, reconsider
the base mesh/art direction before polishing PBR or animation.

## Repo-specific commands

```bash
# Source-locked compact-sailor example:
PYTHONPATH=tools/raftforge xvfb-run -a python -m character_lab.reference_lock \
  --baseline qa-character-a14/sailor-costume-game-oriented.glb \
  --candidate qa-character-a14/sailor-compact-game-oriented.glb \
  --proportions qa-character-a14/proportions.json \
  --blueprint tools/raftforge/character_lab/compact_sailor_blueprint.json \
  --out qa-character-a14/reference-lock
```

The canonical full process, architectural variants, technical gate details,
source licensing and review role matrix are in
`tools/raftforge/docs/BLENDER_BLUEPRINT_FIRST_ART_PIPELINE.md`.

**Current blockers:** RAFTBOUND's main WebGL2 shader is limited to 17 bones;
A14 uses 65 and has been tested only in an independent Three.js animation
viewer. No live-game acceptance and no art signoff exist yet.
