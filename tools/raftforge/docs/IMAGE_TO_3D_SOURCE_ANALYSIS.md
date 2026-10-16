# RAFTFORGE A12 — Reverse-engineering Image-to-3D implementations

**Scope:** Read available public-source implementations to learn engineering methods for a free, local RAFTBOUND asset pipeline. **Not** a claim that we reproduced proprietary services, ran pretrained AI inference, or achieved commercial-ready meshes.

## Correct role of REA

REA is an **agent investigation skill**, **not a runtime dependency of RAFTFORGE**. [Its own skill](https://github.com/morluto/rea/blob/main/.agents/skills/reverse-engineer-anything/SKILL.md) says that when a target has a complete public source repository, normal repository analysis should be used; REA tools are for shipped binaries, compiled/bundled JavaScript, browser/runtime Evidence, and unknown behavior beyond the source. Accordingly we inspected implementation files directly. No REA server-side reverse engineering was performed or claimed.

## Source-backed call chains

### TripoSR — fast single-image geometry

- Entry [`run.py`](https://github.com/VAST-AI-Research/TripoSR/blob/main/run.py): `remove_background` → `resize_foreground` → `TSR.from_pretrained` → `model([image], device)` → `extract_mesh` → optional texture baking.
- [`tsr/system.py` lines 87–120](https://github.com/VAST-AI-Research/TripoSR/blob/main/tsr/system.py#L87-L120): image tokens condition a transformer that produces triplane scene codes.
- [`tsr/system.py` lines 163–205](https://github.com/VAST-AI-Research/TripoSR/blob/main/tsr/system.py#L163-L205): query density, Marching Cubes, vertex color sampling, `trimesh.Trimesh`.
- Transfer: quick geometry baseline with adjustable grid resolution; vertex-color preview versus high-quality UV texture path.
- Its README reports ~6 GB GPU memory for default single-image inference; actual runtime can differ.

### InstantMesh — multiview consistency

- [`run.py`](https://github.com/TencentARC/InstantMesh/blob/main/run.py): segment reference image → Zero123++ generates six views → camera-conditioned `forward_planes` → `extract_mesh`.
- [`src/models/lrm_mesh.py`](https://github.com/TencentARC/InstantMesh/blob/main/src/models/lrm_mesh.py): learned SDF/deformation on a volumetric grid; FlexiCubes produces the surface.
- [`src/models/lrm_mesh.py` lines 340–382](https://github.com/TencentARC/InstantMesh/blob/main/src/models/lrm_mesh.py#L340-L382): switch between neural vertex colors and UV atlas texture created by `xatlas_uvmap` plus sampling the neural texture field.
- Transfer: keep a fast preview path separate from a texture-approval path; optional multiview reconstruction for hero props. Its two-GPU demo splits workloads for memory reduction; it does **not** create one combined GPU memory pool.

### Hunyuan3D-2 — geometry and texturing are distinct systems

- Shape: [`hy3dgen/shapegen/pipelines.py`](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/hy3dgen/shapegen/pipelines.py) samples a learned shape representation and exports a mesh.
- Texture: [`hy3dgen/texgen/pipelines.py` lines 189–240](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/hy3dgen/texgen/pipelines.py#L189-L240): image recentering, delight, UV wrapping, render **normal and position maps** from multiple views, condition multiview texture generation, confidence-weighted projection into UV, inpaint missing texels.
- [Lines 128–153](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/hy3dgen/texgen/pipelines.py#L128-L153) expose back-projection, weighted baking and UV inpainting.
- Transfer: this is the clearest model of a proper texture factory. **Legal:** the [community license](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/LICENSE) includes territorial and other restrictions: do not redistribute its weights or choose it as the default without review.

### TRELLIS — staged generation and mesh QA

- [`trellis/pipelines/trellis_image_to_3d.py` lines 254–283](https://github.com/microsoft/TRELLIS/blob/main/trellis/pipelines/trellis_image_to_3d.py#L254-L283): preprocess → condition → sparse structure → structured latent → decode as mesh / Gaussian / radiance field.
- [`trellis/utils/postprocessing_utils.py` lines 200–273](https://github.com/microsoft/TRELLIS/blob/main/trellis/utils/postprocessing_utils.py#L200-L273): mesh decimation, invisible-face cleanup and selected hole treatment, UV `xatlas.parametrize`.
- [Texture baking](https://github.com/microsoft/TRELLIS/blob/main/trellis/utils/postprocessing_utils.py#L276-L360): raster observations into UV, accumulation and inpainting.
- Transfer: topology/visibility clean-up is essential; game mesh acceptance is separate from generative-image quality. Its README asks for **at least 16 GB NVIDIA GPU memory** for reference workflow.

## What RAFTFORGE should actually implement

1. **CPU input preparation**: alpha-aware crop, subject centering, canonical canvas, visible provenance hash; don't assume hidden sides are observed.
2. **Backend adapters**: run locally installed TripoSR (initial baseline) and optionally InstantMesh; never require paid inference endpoints. Model checkpoints need separate installation, license review and compute.
3. **Geometry review**: correct Y-up, meters, pivots; reject invalid/degenerate meshes, inspect components/normals, enforce triangles and draw-batch budgets; separate collision geometry.
4. **Texture factory**: xatlas/Blender unwrap → multi-camera color/normal/position/depth capture → occlusion/confidence-weighted reprojection to UV → blend and inpaint → pack albedo into GLB.
5. **Objective evidence**: 8+ real rendered viewpoints, multiple lights, inspect invisible sides and UV seams, preserve exact model/checkpoint/settings, GLB, metrics and screenshots. Validate in Three.js before approval.
6. **Separate character solution**: realistic topology, anatomy, skin weights and motion remain a dedicated rigging pipeline.

**First engineering priority:** geometry-to-UV texture baking using synthetic known views, followed by a repeatable 8-view GLB QA sheet. Both can be tested without downloading generative model weights. Next use actual pretrained TripoSR inference on available GPU, then compare InstantMesh on *the same reference image*.

## Licenses, costs, limitations

- [TripoSR MIT](https://github.com/VAST-AI-Research/TripoSR/blob/main/LICENSE) (README says code and weights included).
- [InstantMesh Apache-2.0](https://github.com/TencentARC/InstantMesh/blob/main/LICENSE): inspect dependencies and checkpoint terms independently.
- [TRELLIS MIT](https://github.com/microsoft/TRELLIS/blob/main/LICENSE): check exceptions for submodules noted in its README.
- [Hunyuan3D-2 community license](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/LICENSE): restricted, not a default shipping dependency.

**Verified:** source paths, named calls and stage responsibilities.  
**Not verified:** live image-to-3D quality, hardware throughput, all model-weight distribution rights, production-readiness of outputs, behavior of private hosted services.  
**Principle:** a passing GLB parser/test is not proof of an aesthetically successful 3D reconstruction.
