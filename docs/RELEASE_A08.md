# A08 release summary

**Release scope:** gameplay correctness, stability, save recovery, performance controls and automated testing. **No new artist-approved meshes are claimed.**

## Changes

- New `game/survival-rules.js`: validated state and pure methods for debris aiming, cast-hit detection and safe connected raft extensions.
- Cast catches verify a target still lies near the net's impact location; targets drifting off the landing position are not automatically collected.
- Expanded raft tiles must remain connected and unique. Material consumption is blocked if expansion is impossible.
- Loaded saves are validated and normalized, including resource inventory, player standing position, unique foundation and occupied cells, building IDs and survival stats.
- F4 changes internal canvas render resolution among 90%, 70% and 100%; F3 reports it. This is a performance *control*, not proof of better measured FPS.
- Added pure-function, mocked-WebGL gameplay and 1,200-second simulated endurance tests.

## Test result

- Automated Node/asset tests: **PASS** (`qa/test_results_A08.txt`).
- 20 source/GLB/texture files present: **PASS** (`qa/http_results.json`).
- Real loopback HTTP: **BLOCKED** (socket refused).
- Real Chromium WebGL2: **BLOCKED** (`ERR_BLOCKED_BY_ADMINISTRATOR`, see `qa/browser_results/report.json`).
- Real Blender render: **NOT EXECUTED** (Blender binary absent).
- Final aesthetic acceptance: **NEEDS FIX / NOT VERIFIED**.

Release verdict: **technical progression only — not ready to mark production-approved**.
