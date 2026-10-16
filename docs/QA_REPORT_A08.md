# RAFTBOUND A08 — acceptance report

**Date:** 2026-10-16
**Overall:** TECHNICAL TESTS PASS / PRODUCTION ACCEPTANCE **NOT MET**.

| Gate | Criteria | Evidence | Status |
|---|---|---|---|
| Existing GLB contract | All main models load and preserve weighted animation | `npm test` importer, skinning and vertex color tests | PASS in mocked GL runner |
| Gameplay pickup | Hit near cast impact; miss otherwise | `gameplay-integration-A08.test.js` hit and moving target miss | PASS |
| Raft expansions | Adjacent, unique tiles; no material loss | 380 directional build cases + in-game craft integration | PASS |
| Save recovery | Valid A07 save loads; corrupted state safely rejected | `survival-rules-A08.test.js`, integration save/restore | PASS |
| Production loops | Purifier, grill, planter, shark, hunger, crafts do not fail after extended simulated time | `endurance-A08.test.js`, 1200 simulated seconds | PASS simulated only |
| Adaptive render resolution | F4 changes scale, HUD reports chosen scale | Mock-renderer F3/F4 integration | PASS in mock |
| File assets | Game source, 11 referenced GLBs and 3 PBR textures exist with nonzero size | `qa/serve_acceptance.py` local file checks | PASS |
| Serve assets via HTTP | Local server responds 200 | Local loopback TCP refused by environment policy | BLOCKED |
| True WebGL2 | Real shader compile/link, visual screenshot, browser errors | Chromium blocked by policy; no GPU result | BLOCKED |
| Blender | `.blend` opened and rendered; shoulder, hands and garment quality | Blender executable absent | BLOCKED |
| Production-quality character | Clean rig deformation and pleasing art under real scene lighting | Existing CPU diagnostic not adequate for art sign-off | NEEDS FIX |

**Notes:** Automated mock-GL tests cannot substitute for actual WebGL2 screenshots, visual validation, FPS measurements or Blender viewport evaluation. The included GLB files are retained from A07, so A08 does **not** claim new character artwork or reduced production draw calls beyond A07.
