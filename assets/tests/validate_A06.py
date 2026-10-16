#!/usr/bin/env python3
"""Asset structural QA; does not certify browser GPU rendering or Blender."""
import json,struct,sys
from pathlib import Path
import numpy as np
from PIL import Image
import trimesh
R=Path(__file__).resolve().parents[1];path=R/'glb/survivor_sailor_skinned.glb'
data=path.read_bytes();assert struct.unpack_from('<III',data)==(0x46546c67,2,len(data))
jlen,tag=struct.unpack_from('<II',data,12);assert tag==0x4e4f534a
J=json.loads(data[20:20+jlen]);off=20+jlen;blen,bintag=struct.unpack_from('<II',data,off);assert bintag==0x004e4942
blob=data[off+8:off+8+blen]
assert J['asset']['version']=='2.0' and len(J['skins'])==1
assert len(J['skins'][0]['joints'])==17
assert len(J['meshes'])==2, 'A07 requires two vertex-color material batches'
component={5121:'u1',5123:'<u2',5125:'<u4',5126:'<f4'};width={'SCALAR':1,'VEC3':3,'VEC4':4,'MAT4':16}
def read(i):
 a=J['accessors'][i];v=J['bufferViews'][a['bufferView']]
 start=v.get('byteOffset',0)+a.get('byteOffset',0)
 return np.frombuffer(blob,dtype=component[a['componentType']],count=a['count']*width[a['type']],offset=start).reshape(-1,width[a['type']])
tris=verts=blended=0
for mesh in J['meshes']:
 for p in mesh['primitives']:
  a=p['attributes'];assert {'POSITION','NORMAL','JOINTS_0','WEIGHTS_0','COLOR_0'}<=set(a)
  pos=read(a['POSITION']);norm=read(a['NORMAL']);ji=read(a['JOINTS_0']);w=read(a['WEIGHTS_0']);indices=read(p['indices'])
  assert len(pos)==len(norm)==len(ji)==len(w)==len(read(a['COLOR_0']))
  assert np.isfinite(pos).all() and np.isfinite(norm).all() and np.isfinite(w).all()
  assert (ji<17).all() and (w>=0).all() and (w<=1).all()
  assert np.allclose(w.sum(axis=1),1.0,atol=1e-5)
  assert (indices<len(pos)).all()
  assert len(indices)%3==0
  tris+=len(indices)//3;verts+=len(pos)
  blended+=int(np.sum((w>.001).sum(axis=1)>1))
assert 12000<=tris<=25000,(tris,verts)
assert blended>=1350,blended
binds=read(J['skins'][0]['inverseBindMatrices']);assert binds.shape==(17,16)
assert np.isfinite(binds).all()
source=trimesh.load(R/'glb/survivor_sailor_rig.glb',force='scene')
assert len(source.geometry)>=95
height=source.bounds[1,1]-source.bounds[0,1]
assert 1.80<height<1.94,height
for pose in ['idle','walk','cast','collect','craft']:
 fn=R/'previews'/f'A06_{pose}_weighted_pose_diagnostic.glb';assert fn.exists(),fn
assert Image.open(R/'previews/survivor_A06_motion_sheet.png').size[0]>1000
manifest=json.loads((R/'skin_manifest_A07.json').read_text())
assert manifest['triangles']==tris and manifest['vertices']==verts and manifest['weighted_vertices']==blended
import py_compile
py_compile.compile(str(R/'blender/finish_A06.py'),doraise=True)
print(f'PASS A07 structural (A06 pose compatibility): {tris} triangles; {verts} vertices; {blended} blended vertices; 17 joints; 5 CPU poses; Blender script syntax')
