# RAFTFORGE A11 — Quality Gates

## Automated, reproducible technical acceptance

- All 3 sample JSON recipes generate deterministic valid GLB 2.0 files.
- Every re-imported asset has finite vertices, >300 triangles, <=15 draw groups, appropriate 1:1 meter bounds, and triangle count below its category budget.
- Four distinct raft variants differ by seed and share gameplay tile dimensions.
- Pure CPU preview of each model from three views (hero, rear, top) comes from re-imported GLB; not from a hand-drawn reference.
- 8 Python unit/integration tests pass; Blender render and Three.js runtime parity remain pending.

## Human visual review — NEEDS REVIEW

- [ ] Silhouette readable at the game's actual third-person camera distance.
- [ ] Materials have appropriate wood grain, rust, metal aging, not only solid colors.
- [ ] Model feels hand-authored, with asymmetry and proportion balance.
- [ ] No seams/mesh intersections/floating ornaments under normal play view.
- [ ] Final GLB loads in WebGL with correct shading and no warnings.
- [ ] Collider and transform align with gameplay sockets.
- [ ] Verify GPU draw-call budget / FPS on a target machine.
- [ ] Confirm Blender finishing pass and editability if needed.

**Verdict:** A11 passes automated *geometry* tests; visuals are a first stylized-art pass, **not AAA- or production-approved**.
