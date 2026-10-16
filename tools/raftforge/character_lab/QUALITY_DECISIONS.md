# A13 Art direction decision log

## Current A07 / REJECTED for production art

Real A07 3D GLB: 18,628 tris, 17 bones; no embedded clips. Geometry/skin technically valid. Front/three-quarter/back images show oversized cartoon facial features, pipe-like arms, crude fingers and dated clothing blockout. This is **visual failure**, not a polycount problem. More random procedural geometry will not fix the core art direction.

## New process / NO more version churn

- **Keep** original A07 for functional regression and compare only.
- **Source a high-quality CC0 base** (Quaternius Standard, glTF, Humanoid rig and real anatomy), import it to a separate candidate scene.
- **Judge body and face first** with same-camera multiview images at 1.8m Y-up. No costume or rig work while face/hands/silhouette are below 4/5.
- **Art direct a consistent survivor**: warm sea-weathered complexion, human proportion 7–7.5 heads tall, shorter more natural-looking forearms, feet sized for third person, brim hat and layered cloth, warm tan + teal, salt-weathered textiles, no googly eyes. Avoid deforming rig blindly.
- **Only after approval** add hat/vest/belt/bag as separate attached or skinned meshes; bind props using actual bone sockets, don't create a new skeleton from scratch. Rig mapping and idle/walk/cast deformations need Three.js browser QA (screenshots/video).
- Limit iterative candidates to **three** silhouette options, keep one. Before every iteration list one specific failing art criterion and remedy. Do not increment A14/A15 milestone numbers as a substitute for quality.

## Acceptance criteria

1. 3+ true renders (front, 3/4, rear) and an actual 120px-high player on a raft screenshot.
2. 6 reviewed art scores >= 4/5 (silhouette, face, hands, clothing, in-game readability, animation deformation) — scores by a human, not an LLM pretending it tested motion.
3. 2 model families in the project at any time: accepted one plus active candidate; no pileup of nearly-identical exports.
4. Skeleton/animation checked in runtime with idle, walk, cast and grip. Accessory clipping and skin tearing have to be absent in the video.
5. GLB <=25k triangles for LOD0 initially, measured draw calls and stable pivot/scale (asset-specific exceptions documented).

## Evidence caveats

A13 local pass: 7 tests, real rig GLB fit (Y-up) and offscreen VTK renders. This does NOT prove the new character model is good. The new CC0 character is collected by CI, not yet signed off in-game. Missing images, workflow failures or offscreen-model discrepancies are recorded as unresolved rather than silently approved.