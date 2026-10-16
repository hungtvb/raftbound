# RAFTBOUND A09 — Three.js Migration (parallel preview)

This is a **playable migration preview**, not a replacement for the validated A08 WebGL2 game. The original remains in `../game/` unchanged.

## Run

```bash
cd web
npm install
npm run dev
# Open the Vite URL, usually http://localhost:5173
```

Build: `npm run build`. Test A08 rules: `npm --prefix ../game test`.

## Architecture

- **TypeScript + Vite:** modular game bootstrap, Vite build.
- **Three.js:** renderer, scene graph, physically-based glTF materials, ocean shader, orbit camera and meshes.
- **Rapier:** initialized 3D physics world with fixed raft colliders and a kinematic player body. A08's deterministic `onRaft` movement constraint stays authoritative during migration.
- **Existing GLB assets:** reused from `../game/assets`, exposed at `/glb/` by Vite's `publicDir`. No duplicate binary assets in the repo.
- **Legacy gameplay invariants:** imports A08 `survival-rules.js` and `cast-motion.js` as-is. Saves remain `raftbound.save.v1` and are validated by A08 before loading.

## Supported in this preview

Movement on modular raft, ocean/waves, floating loot, cast timing/collision, resource inventory, crafting, raft expansion, purifier/cooking/planter production, hunger/thirst, shark damage, save/load, three camera modes, screenshots and F3 performance overlay.

## Known gaps before replacing A08

- Character animation is basic procedural bone posing, **not** full authored AnimationMixer clips.
- Rendering, physics feel and performance still require GPU browser acceptance; passing automated tests is insufficient.
- Rapier is currently used for colliders/kinematic body; interaction tests still rely on proven A08 deterministic geometry rules.
- Assets have basic fallback meshes if GLBs cannot load; release-quality art and collision hulls remain work in progress.

Run the existing version independently via `cd game && python3 -m http.server 8000`.
