"""Physical GLB, scene-node hierarchy and texture source checks."""
from pathlib import Path
import json,math,sys
import numpy as np,trimesh
from PIL import Image
BASE=Path(__file__).resolve().parents[1]
rec=json.loads((BASE/'character_manifest.json').read_text())
path=BASE/rec['file']
scene=trimesh.load(path,force='scene')
assert len(scene.geometry)>=35,f'Insufficient materials/mesh groups: {len(scene.geometry)}'
assert all(np.isfinite(g.vertices).all() for g in scene.geometry.values())
actual=sum(len(m.faces) for m in scene.geometry.values())
assert actual==rec['triangles'],(actual,rec['triangles'])
ymin,ymax=scene.bounds[:,1]
assert -.05<=ymin<=.08 and 1.7<=ymax<=2.0,(ymin,ymax)
assert max(scene.bounds[1]-scene.bounds[0])<2.05
nodes=set(scene.graph.nodes)
for name in rec['joint_names']:
 assert name in nodes, name
 assert scene.graph.transforms.parents.get(name),name
for name in ('basecolor','normal','roughness','height'):
 img=Image.open(BASE/'textures'/f'wood_{name}.png')
 assert img.size==(512,512),name
 print('PASS PBR map',name,img.mode)
print('PASS character rig',len(scene.geometry),'mesh groups,',actual,'triangles, height',round(ymax-ymin,3),'m,',len(rec['joint_names']),'joints')
