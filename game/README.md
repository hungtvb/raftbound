# RAFTBOUND A08 browser game

Run this directory with a local HTTP server:

```bash
python3 -m http.server 8000
```

Then open <http://localhost:8000> in a desktop browser with WebGL2.

From the repository root, run tests with `npm --prefix game test`.

Game controls: WASD move, Space throw net, right-drag orbit, Q craft, 1/2 eat/drink, V camera, G switch imported/legacy meshes, P screenshot, F3 diagnostics, F4 render scale.

See [`../README.md`](../README.md) and [`../docs/QA_REPORT_A08.md`](../docs/QA_REPORT_A08.md) for details and actual validation status.
