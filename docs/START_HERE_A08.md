# RAFTBOUND A08 — gameplay QA & reliability

This is an **incremental build on A07**, not a new art/Blender model release. The 11 original imported GLBs and Blender preparation scripts are included unmodified.

## Run

```bash
cd game
python3 -m http.server 8000
```

Open `http://localhost:8000` in a browser with WebGL2. Do not double-click `index.html`: imported GLB / texture fetches require an HTTP origin.

Controls: WASD movement, right-mouse drag to orbit camera, Space cast net, Q craft, 1 eat, 2 drink, V camera, G imported/legacy mesh toggle, P screenshot, F3 performance HUD, **F4 renderer scale 90% → 70% → 100%**.

## Implemented since A07

1. Deterministic net aiming: pick only targets inside a forward-facing 95-degree cone; successful pickup requires the target to remain within 1.05 metres of the cast impact position. No pickups through off-target objects.
2. Safe raft expansion: only add a unique, adjacent tile, and do not deduct resources if the raft cannot expand (hard cap 400 tiles).
3. Validated game saves: reject corrupted, non-finite, negative, disconnected or duplicated save data rather than using invalid gameplay state. Existing valid A07 `raftbound.save.v1` data is compatible.
4. New resolution scaling option (F4) and readout (F3) to help performance evaluation.
5. A deterministic, simulated 20-minute gameplay endurance scenario plus dedicated aiming, casting, resource, crafting, save and continuity tests.

## QA

Run locally:

```bash
bash qa/run_automated_tests.sh
```

HTTP resource test: `python3 qa/serve_acceptance.py` (in this environment local file existence passes but loopback socket requests are blocked).

Real browser acceptance: serve on port 8000, then run:

```bash
python3 qa/browser_acceptance.py
```

Blender scene: `blender --background --python assets/blender/finish_A07.py` (follow script's arguments and dependencies in its header).

**Acceptance status:** Automated code/asset tests PASS. True Blender render, visual art acceptance and actual WebGL2/FPS acceptance **NOT VERIFIED** in this environment. A production-ready verdict requires manual inspection and browser metrics from a machine permitted to render WebGL2.
