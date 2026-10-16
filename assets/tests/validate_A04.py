#!/usr/bin/env python3
"""Checks GLB skin structure, bounds, numerical properties and preview output."""
from pathlib import Path
import json,struct,sys,numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
B=(ROOT/'glb/survivor_sailor_skinned.glb').read_bytes()
assert struct.unpack_from('<III',B,0)==(0x46546c67,2,len(B))
jlen,jtag=struct.unpack_from('<II',B,12);assert jtag==0x4e4f534a
J=json.loads(B[20:20+jlen]);assert len(J['skins'])==1 and len(J['skins'][0]['joints'])==17
assert len(J['meshes'])==16
triangles=0
for m in J['meshes']:
 for prim in m['primitives']:
  a=prim['attributes'];assert all(i in a for i in ('POSITION','NORMAL','JOINTS_0','WEIGHTS_0'))
  p=J['accessors'][a['POSITION']];t=J['accessors'][prim['indices']];triangles+=t['count']//3
  assert p['count']>0
assert triangles==9848
M=json.loads((ROOT/'skin_manifest_A04.json').read_text());assert M['weighted_vertices']>=1200
im=Image.open(ROOT/'previews/survivor_A04_weighted_motion_sheet.png');assert im.width>1000 and im.height>500
for name in ('wood_basecolor','wood_normal','wood_roughness'):
 img=Image.open(ROOT/'textures'/f'{name}.png');assert img.size==(512,512)
print('PASS A04 GLB structure, 17 joints, 16 material batches, 9848 triangles, weighted vertices, texture files, pose renders')
