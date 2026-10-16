"""Optional *local* image-to-3D inference adapters with reproducible provenance.

No paid APIs. No automatic checkout/download of third-party repositories or weights.
The model backends are run as isolated subprocesses, not imported by RAFTFORGE.
Inference is never implied to have passed when the host has no suitable GPU/weights.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageOps

BACKENDS = {
    'triposr': {
        'repository': 'https://github.com/VAST-AI-Research/TripoSR',
        'license_note': 'Repository README states MIT for code and pretrained model; verify the downloaded weights.',
        'entrypoint': 'run.py',
        'requires_cuda': False,
        'typical_vram_gb': 6,
        'output': 'GLB with vertex colors (no texture atlas by default)',
    },
    'instantmesh': {
        'repository': 'https://github.com/TencentARC/InstantMesh',
        'license_note': 'Apache-2.0 repository; review individual model/checkpoint dependencies.',
        'entrypoint': 'run.py',
        'requires_cuda': True,
        'typical_vram_gb': None,
        'output': 'OBJ/MTL + texture map, converted to GLB',
    },
}


@dataclass(frozen=True)
class Image3DOptions:
    backend: str
    backend_dir: Path
    input_image: Path
    output_dir: Path
    target_max_dim_m: float = 1.8
    source_up: str = 'y'
    triangle_budget: int = 30000
    python_executable: str = sys.executable
    timeout_sec: int = 3600
    instantmesh_config: str = 'configs/instant-mesh-large.yaml'
    instantmesh_steps: int = 30
    allow_complex_bg: bool = False
    offline_only: bool = True
    preview: bool = False


def preprocess_image(image: Path, dest: Path, canvas: int = 512,
                     allow_complex_bg: bool = False) -> dict:
    """Deterministic alpha/image canvas stage; doesn't hallucinate missing sides.

    If the input has real transparency, crop to alpha. For a flat background,
    conservative corner-connected RGB flood fill removes it. For textured
    backgrounds, fail unless the user explicitly allows ambiguous backgrounds.
    """
    with Image.open(image) as f:
        original = ImageOps.exif_transpose(f).convert('RGBA')
    a = np.asarray(original, dtype=np.uint8).copy()
    h, w = a.shape[:2]
    if w < 32 or h < 32 or w > 8192 or h > 8192:
        raise ValueError('Input image must be between 32px and 8192px per side')
    transparent = bool(np.min(a[..., 3]) < 220)
    segmentation = 'provided_alpha' if transparent else 'flat_bg_corner_flood'
    if not transparent:
        corners = a[[0, 0, h-1, h-1], [0, w-1, 0, w-1], :3].astype(np.int16)
        med = np.median(corners, axis=0)
        variation = float(np.max(np.linalg.norm(corners - med[None], axis=1)))
        if variation > 32:
            if not allow_complex_bg:
                raise ValueError('Complex background: supply transparent PNG or --allow-complex-bg')
            segmentation = 'complex_bg_unchanged'
        else:
            # Segment only edge-connected background, preserving similarly
            # colored interior surfaces. SciPy is an existing RAFTFORGE dep.
            from scipy.ndimage import binary_propagation
            near = np.linalg.norm(a[..., :3].astype(np.float32) - med[None, None], axis=2) < 28
            seeds = np.zeros((h, w), dtype=bool)
            seeds[[0, 0, h-1, h-1], [0, w-1, 0, w-1]] = True
            bg = binary_propagation(seeds & near, mask=near)
            if np.count_nonzero(bg) > .95 * w*h:
                raise ValueError('Background extraction discarded >95% image; provide alpha PNG')
            a[..., 3][bg] = 0

    alpha = Image.fromarray(a[..., 3], 'L')
    box = alpha.getbbox()
    if not box:
        raise ValueError('Foreground mask is empty')
    rgba = Image.fromarray(a, 'RGBA').crop(box)
    # Preserve aspect ratio and leave ~10% padding, just like public reference pipelines.
    longest = max(rgba.size)
    new_size = tuple(max(1, round(x * canvas * .83 / longest)) for x in rgba.size)
    resized = rgba.resize(new_size, Image.Resampling.LANCZOS)
    normalized = Image.new('RGBA', (canvas, canvas), (128, 128, 128, 255))
    normalized.alpha_composite(resized, ((canvas-new_size[0])//2, (canvas-new_size[1])//2))
    dest.parent.mkdir(parents=True, exist_ok=True)
    normalized.convert('RGB').save(dest)
    return {
        'sha256_input': hashlib.sha256(image.read_bytes()).hexdigest(),
        'preprocessor': segmentation, 'original_resolution': [w,h],
        'cropped_bounds_px': list(map(int,box)), 'normalized_resolution': [canvas,canvas],
        'normalized_sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
    }


def probe_gpu() -> dict:
    try:
        import torch
        return {'cuda_available': bool(torch.cuda.is_available()),
                'cuda_device_count': int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
                'torch_version': str(torch.__version__)}
    except ImportError:
        return {'cuda_available': False, 'cuda_device_count': 0, 'torch_version': None}


def backend_command(opts: Image3DOptions, clean_image: Path, raw_dir: Path) -> tuple[list[str], Path]:
    if opts.backend not in BACKENDS:
        raise ValueError(f'Unknown backend: {opts.backend}. Supported: {", ".join(BACKENDS)}')
    root = opts.backend_dir.resolve(strict=True)
    if not (root / 'run.py').is_file():
        raise FileNotFoundError(f'Missing backend run.py in {root}')
    if opts.backend == 'triposr':
        cmd = [opts.python_executable, 'run.py', str(clean_image.resolve()),
               '--no-remove-bg', '--model-save-format', 'glb',
               '--output-dir', str(raw_dir.resolve()), '--device',
               'cuda:0' if probe_gpu()['cuda_available'] else 'cpu']
        mesh = raw_dir / '0' / 'mesh.glb'
    else:
        config = root / opts.instantmesh_config
        if not config.is_file():
            raise FileNotFoundError(f'InstantMesh config missing: {config}')
        if not (1 <= opts.instantmesh_steps <= 150):
            raise ValueError('InstantMesh steps must be 1..150')
        cmd = [opts.python_executable, 'run.py', opts.instantmesh_config,
               str(clean_image.resolve()), '--output_path', str(raw_dir.resolve()),
               '--diffusion_steps', str(opts.instantmesh_steps), '--no_rembg', '--export_texmap']
        mesh = raw_dir / config.stem / 'meshes' / (clean_image.stem + '.obj')
    return cmd, mesh


def inspect_mesh(glb: Path, budget: int = 30000) -> dict:
    # Intentionally unlike validated hand-authored props, novel AI meshes often
    # have nonmanifold topology. Report topology facts, don't claim art PASS.
    scene = trimesh.load(glb, force='scene', process=False)
    meshes = list(scene.geometry.values())
    if not meshes or scene.bounds is None:
        raise ValueError('Empty generated mesh')
    tris = sum(len(m.faces) for m in meshes)
    size = scene.bounds[1] - scene.bounds[0]
    finite = all(np.isfinite(m.vertices).all() for m in meshes)
    if not finite or not np.isfinite(size).all():
        raise ValueError('Invalid vertices/bounds')
    uv_count = sum(int(getattr(m.visual, 'uv', None) is not None) for m in meshes)
    texture_count = sum(int(getattr(getattr(m.visual, 'material', None), 'baseColorTexture', None) is not None) for m in meshes)
    return {
        'file': str(glb), 'sha256': hashlib.sha256(glb.read_bytes()).hexdigest(),
        'triangles': int(tris), 'triangle_budget': budget,
        'geometry_count': len(meshes), 'uv_geometry_count': uv_count,
        'albedo_texture_geometry_count': texture_count,
        'dimensions_m': size.round(5).tolist(), 'bounds_m': scene.bounds.round(5).tolist(),
        'finite_vertices': finite, 'has_geometry': bool(tris),
        'budget_ok': tris <= budget, 'topology_watertight_count': sum(int(m.is_watertight) for m in meshes),
        'static_pass': bool(0 < tris <= budget and finite and np.max(size) > 0.01),
        'visual_approved': False, 'rigging_approved': False,
    }


def normalize_to_glb(source: Path, destination: Path, target_max_dim_m=1.8,
                     source_up='y') -> dict:
    if not np.isfinite(target_max_dim_m) or not 0.1 <= target_max_dim_m <= 100:
        raise ValueError('target_max_dim_m must be in [0.1,100]')
    if source_up not in ('y','z'):
        raise ValueError('source_up must be y or z')
    if source.suffix.lower() not in ('.glb','.obj','.ply','.gltf'):
        raise ValueError('Unsupported backend output format')
    s = trimesh.load(source, force='scene')
    if not s.geometry or s.bounds is None:
        raise ValueError('Backend produced an empty scene')
    if source_up == 'z':
        s.apply_transform(trimesh.transformations.rotation_matrix(-np.pi/2,[1,0,0]))
    bounds=s.bounds
    longest = float(np.max(bounds[1]-bounds[0]))
    if not np.isfinite(longest) or longest < 1e-6:
        raise ValueError('Degenerate model; cannot normalize')
    scale=target_max_dim_m/longest
    s.apply_scale(scale)
    b=s.bounds
    # Center around raft-placement XZ and place feet/base on Y=0.
    s.apply_translation([-(b[0,0]+b[1,0])/2,-b[0,1],-(b[0,2]+b[1,2])/2])
    destination.parent.mkdir(parents=True,exist_ok=True)
    s.export(destination)
    if not destination.is_file() or destination.read_bytes()[:4] != b'glTF':
        raise RuntimeError('GLB export failed')
    return {'scale_factor': scale, 'source_up': source_up, 'target_max_dim_m': target_max_dim_m}


def run_image3d(opts: Image3DOptions) -> dict:
    if opts.backend not in BACKENDS:
        raise ValueError('Unsupported backend')
    source=opts.input_image.resolve(strict=True)
    if source.suffix.lower() not in ('.jpg','.jpeg','.png','.webp'):
        raise ValueError('Input must be JPG/PNG/WebP')
    if not opts.offline_only:
        raise ValueError('Only offline inference is supported in RAFTFORGE')
    if opts.timeout_sec < 5 or opts.timeout_sec > 24 * 3600:
        raise ValueError('timeout_sec outside 5..86400')
    gpu=probe_gpu()
    if BACKENDS[opts.backend]['requires_cuda'] and not gpu['cuda_available']:
        raise RuntimeError(f'{opts.backend} requires an available CUDA GPU; local GPU not detected')
    out=opts.output_dir.resolve()
    stage=out/'staging'
    raw=out/'raw'
    inp=stage/'input.png'
    start=time.monotonic()
    pre=preprocess_image(source, inp, allow_complex_bg=opts.allow_complex_bg)
    cmd,expected=backend_command(opts,inp,raw)
    raw.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    # Offline inference must not unexpectedly fetch weights or send images.
    env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1',
               HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1')
    result=subprocess.run(cmd,cwd=str(opts.backend_dir.resolve()),env=env,
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                          text=True,timeout=opts.timeout_sec,check=False)
    log=out/'backend.log'
    log.write_text(result.stdout[-100_000:],encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'Backend failed (exit {result.returncode}); inspect {log}. ' 
                           'Check locally cached weights and backend-specific dependencies.')
    if not expected.is_file():
        raise FileNotFoundError(f'Backend completed but expected mesh absent: {expected}')
    final=out/'model.glb'
    transform=normalize_to_glb(expected,final,opts.target_max_dim_m,opts.source_up)
    qa=inspect_mesh(final,opts.triangle_budget)
    evidence={
        'status':'static_pass' if qa['static_pass'] else 'needs_geometry_fix',
        'visual_status':'NOT_VALIDATED',
        'backend':opts.backend,'model_repo':BACKENDS[opts.backend]['repository'],
        'backend_source_path':str(opts.backend_dir.resolve()),
        'backend_command':cmd, 'offline_requested':True,'network_isolation_enforced':False,'gpu':gpu,
        'elapsed_seconds':round(time.monotonic()-start,2),
        'preprocess':pre,'transform':transform,'qa':qa,
        'license_review_required': True,
    }
    if opts.preview:
        try:
            from .preview import render_glb
            for name in ('hero','rear','top'):
                render_glb(final,angle=name,size=(640,520)).save(out/f'{name}.png')
            evidence['preview']='VTK software offscreen (textures may not match web output)'
        except ImportError:
            evidence['preview']='unavailable: install optional vtk'
    (out/'evidence.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False),encoding='utf-8')
    return evidence
