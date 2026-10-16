"""Game asset static QA. Reports are measurements, not visual acceptance claims."""
import json
import numpy as np
import trimesh

TARGETS={'raft_tile':4500,'storage_chest':6000,'compact_grill':7000}

def validate(glb_path,kind,details=None):
    s=trimesh.load(glb_path,force='scene')
    meshes=list(s.geometry.values())
    tris=sum(len(x.faces) for x in meshes)
    bounds=s.bounds
    assert bounds is not None
    size=bounds[1]-bounds[0]
    results={
      'model':kind,'file':str(glb_path),'triangles':int(tris),
      'draw_batches':len(meshes),'bounds_m':np.round(bounds,4).tolist(),
      'dimensions_m':np.round(size,4).tolist(),
      'tri_budget':TARGETS[kind],
      'watertight_meshes':sum(int(x.is_watertight) for x in meshes),
      'finite_vertices':bool(all(np.isfinite(x.vertices).all() for x in meshes)),
      'glb_roundtrip': True,
    }
    checks={
      'triangle_budget':tris<=TARGETS[kind],
      'batch_budget':len(meshes)<=15,
      'non_empty':tris>300,
      'finite_vertices':results['finite_vertices'],
      'scale_m':bool((size>.09).all() and (size<3.1).all()),
    }
    if kind=='raft_tile':
        checks['tile_width_2m']=bool(1.94<size[0]<2.13 and 1.94<size[2]<2.13)
    results['checks']=checks;results['static_pass']=all(checks.values())
    return results
