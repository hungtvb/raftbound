# RAFTBOUND — Ocean Survival (A08)

A **3D web-based ocean survival prototype**: survive on a raft, cast a salvage net to collect floating resources, expand the raft, and craft a grill, water purifier, planters, and storage. Includes shark interactions, hunger/thirst, inventory, and local save/load.

> **Status:** A08 technical prototype. Automated gameplay and GLB tests pass; real browser WebGL2 rendering, GPU FPS, Blender output, and production-level character art **have not been signed off**.

## Tech stack (as implemented)

| Layer | Implementation |
| --- | --- |
| Game | Vanilla JavaScript (ES6+) |
| 3D rendering | Custom WebGL2 and GLSL shaders |
| UI | HTML and CSS |
| Physics / gameplay | Custom JavaScript rules |
| 3D assets | glTF 2.0 GLB, Blender-compatible scripts, Python mesh tools |
| Saving | Browser LocalStorage |
| Tests | Node.js built-in assertion-based tests |

**Planned, not implemented:** migrate incrementally to TypeScript + Three.js + Rapier + Vite once the current baseline is published and regression-tested. This repository does **not** yet use that stack.

## Run locally

Requirements: Python 3 and a desktop browser with WebGL2.

```bash
cd game
python3 -m http.server 8000
```

Open **http://localhost:8000** in the browser. GLB assets are loaded using HTTP; do not open `index.html` through `file://`.

### Controls

| Key | Action |
| --- | --- |
| WASD | Move |
| Space | Throw salvage net |
| Right mouse drag | Orbit camera |
| Q | Crafting menu |
| 1 / 2 | Eat / drink |
| V | Camera preset |
| G | Toggle legacy / GLB meshes |
| P | Take screenshot |
| F3 | FPS / draw call diagnostic HUD |
| F4 | Rendering resolution scale |

## Test

```bash
npm --prefix game test
```

The test suite exercises GLB loading, skeletal animation, vertex colors, cast timing/collisions, crafting, raft expansion, save validation, and a deterministic 1,200-second survival simulation. These tests use a mocked renderer and **do not establish GPU visual fidelity**.

A GitHub Actions workflow runs the Node.js suite on pushes to `main` and on pull requests. Additional tests and reports are under [`qa/`](qa/) and [`docs/`](docs/).

## Layout

- [`game/`](game/) — playable WebGL2 prototype, assets required at runtime, Node.js tests.
- [`assets/`](assets/) — GLB models, source generators, Blender scripts, PBR textures, diagnostics.
- [`qa/`](qa/) — extra acceptance scripts (actual WebGL requires browser/GPU access).
- [`docs/`](docs/) — QA report, release notes and detailed start guide.

## Asset / art acceptance

The game contains Blender-ready scripts and GLB assets but no Blender `.blend` has been verified here. Character silhouette, joint deformation, lighting, shadows and runtime FPS need testing on a graphics-capable environment before a production release.

## Migration roadmap

1. Snapshot A08 as baseline and keep all regression tests green.
2. Add a Vite/TypeScript entry point and glTF/Three.js scene (without deleting the current prototype).
3. Move camera, world and ocean renderer; verify GLB skinning/animation parity.
4. Add Rapier for collision/physics while keeping the deterministic gameplay model.
5. Run side-by-side browser visual and performance acceptance; remove the legacy renderer only after passing.

Original game design: [`game/GAME_DESIGN.md`](game/GAME_DESIGN.md). Technical acceptance: [`docs/QA_REPORT_A08.md`](docs/QA_REPORT_A08.md).
