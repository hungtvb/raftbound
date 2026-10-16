#!/usr/bin/env python3
"""Non-visual QA for model contracts. Not a substitute for Blender/runtime render review."""
import sys,json
from pathlib import Path
import numpy as np
import trimesh
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'asset_manifest.json').read_text())
contract=json.loads((ROOT/'asset_contract.json').read_text())
assert len(m['assets'])==12
assert m['up_axis']=='Y' and m['tile_size_m']==2
for a in m['assets']:
    fn=ROOT/a['file'];assert fn.exists(),fn
    s=trimesh.load(fn,force='scene');assert len(s.geometry)>0
    n=sum(len(x.faces) for x in s.geometry.values())
    assert n==a['triangles'],(fn,n,a['triangles'])
    for obj in s.geometry.values():
        assert obj.is_empty is False
        assert np.isfinite(obj.vertices).all()
        assert hasattr(obj.visual,'material')
    bounds=s.bounds
    assert np.allclose(bounds,np.array(a['bounds_m']),atol=.002),a['id']
    assert len(fn.read_bytes())/1048576<2
    assert a['size_kb']>0
    if a['category']=='resource': assert n<=2500,(a['id'],n)
    if a['category']=='craft_station': assert n<=6000,(a['id'],n)
    if a['id']=='foundation_2m':
        ext=bounds[1]-bounds[0]
        assert 1.8<ext[0]<2.01 and 1.8<ext[2]<2.01
        assert n<5000
    print('PASS',a['id'],n,'tri')
assert (ROOT/'starter_raft_scene.glb').exists()
scene=trimesh.load(ROOT/'starter_raft_scene.glb',force='scene')
assert len(scene.geometry)>=20
assert (ROOT/'blender'/'build_scene.py').exists()
assert (ROOT/'previews'/'asset_contact_sheet.png').exists()
print('PASS A02 manifest, model budgets, coordinates, PBR material references, demo scene')
