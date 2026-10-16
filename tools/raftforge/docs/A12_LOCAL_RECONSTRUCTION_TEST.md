# RAFTFORGE A12 — Measured CPU Test Evidence (2026-10-16)

**Status:** Local geometry QA PASS; actual pretrained neural Image-to-3D inference **BLOCKED** (no CUDA / weights); visual production acceptance **NEEDS_FIX**.

## What was genuinely tested

- `python -m unittest discover -s tests -v`: **18/18 PASS** after adding the vertex-color regression test.
- Three real procedural exports: raft tile **2,596 triangles**, storage chest **5,040**, compact grill **3,508**; actual offscreen VTK contact-sheet render and glTF round-trip. **Not** neural generation.
- Four different-seed raft variants built and validated.
- Experimental **CPU-only multiview visual-hull reconstruction** using six *synthetic* orthographic silhouette captures from an existing GLB; source geometry was not available to reconstruction.
- Projected a **120³ voxel grid** into six reference silhouettes, extracted mesh by Marching Cubes (**143,892 faces**), reduced to **22,000 faces** via VTK quadric decimation, and transferred image-derived per-vertex RGB color.
- Result exported as GLB with `COLOR_0`, **573,028 bytes**; `trimesh` reimport confirmed finite geometry and watertight mesh.
- Held-out 7th oblique camera silhouette Intersection-over-Union (IoU): **0.9649**. Training-view silhouette IoU: front/rear **0.9828**, left/right **0.9704**, top/bottom **0.9865**.
- Color recovery coverage: **73.62%** vertices received nontrivial image-projected color; texture UV bake not yet implemented.

## How to interpret the numbers

This is a **controlled synthetic shape-from-silhouette experiment**, *not AI inference*, *not generic image-to-3D from one photo* and *not a user-image benchmark*. A high 2D silhouette IoU does **not** measure complete 3D accuracy. The output visibly loses concavities, detailed straps and sharp metal parts. Its triangle count is over four times that of the source chest (22,000 vs 5,040) even after decimation. **Visual result: NEEDS_FIX.**

## Preview correctness fix

Found a reproducible QA bug: the optional VTK screenshot renderer ignored glTF `COLOR_0` on vertex-colored meshes. This made recovered color look monochromatic despite GLB containing vertex colors. The PR adds point-data direct RGB rendering and a unit test showing that a red GLB renders red, so visual evidence reflects its contents.

## Neural inference blocker

Host has `torch 2.10.0+cpu`, `torch.cuda.is_available()==False`, no installed TripoSR/InstantMesh model backend or weights. The existing `test_triposr_command_and_successful_stub_e2e` test exercises only a **mocked backend command** and cannot support a claim of model quality.

## Reproduce

Run RAFTFORGE Python unit tests as usual; reproducible experimental script `visual_hull_trial.py`, sample GLBs, front/rear/top/held-out screenshots, colored output GLB, machine JSON report and local test logs are packaged in the conversation's **RAFTFORGE_A12_REAL_TEST_EVIDENCE.zip** artifact. Requires free `vtk` and `scikit-image` alongside existing Python deps:

```bash
PYTHONPATH=./tools/raftforge python visual_hull_trial.py --source storage_chest_art.glb --out visual-hull --grid 120
```

The next meaningful AI acceptance test needs actual downloaded model weights and appropriate GPU hardware. For TripoSR the project README states approximately **6 GB VRAM** for standard single-image inference. Avoid treating mock-backend tests as pretrained inference.

**Evidence limitations:** VTK software offscreen render is not Blender or Three.js GPU acceptance; camera/lighting for synthetic images are known; no unknown-camera photo reconstruction or learned texture synthesis was tested.
