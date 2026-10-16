#!/usr/bin/env python3
"""CPU diagnostic poses of exported weighted glTF asset, not a Blender/GPU render."""
import json,struct,math,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import trimesh
from trimesh.visual import TextureVisuals
from trimesh.visual.material import PBRMaterial
BASE=Path(__file__).resolve().parents[1];OUT=BASE/'previews';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(Path(__file__).parent));import render_previews
render_previews.ROOT=BASE
from inspect import getsource
renderfunc=getsource(render_previews.render).replace('eye=np.array([3.5,3.4,4.5])','eye=np.array([3.3,2.4,-6.])').replace('scale=.65*min(w,h)/radius','scale=.95*min(w,h)/radius')
exec(renderfunc,vars(render_previews),scope:={});render=scope['render']
b=(BASE/'glb/survivor_sailor_skinned.glb').read_bytes();jlen=struct.unpack_from('<I',b,12)[0];json_doc=json.loads(b[20:20+jlen]);q=20+jlen
bin_data=b[q+8:q+8+struct.unpack_from('<I',b,q)[0]]
comptypes={5121:'u1',5123:'<u2',5125:'<u4',5126:'<f4'};dims={'SCALAR':1,'VEC3':3,'VEC4':4,'MAT4':16}
def read(i):
 a=json_doc['accessors'][i];v=json_doc['bufferViews'][a['bufferView']];off=v.get('byteOffset',0)+a.get('byteOffset',0)
 return np.frombuffer(bin_data,dtype=comptypes[a['componentType']],count=a['count']*dims[a['type']],offset=off).reshape(a['count'],dims[a['type']]).copy()
def mat(n):return np.asarray(n.get('matrix',[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]),float).reshape(4,4,order='F')
nodes=json_doc['nodes'];parents={c:i for i,n in enumerate(nodes) for c in n.get('children',[])}
skin=json_doc['skins'][0];joints=skin['joints'];inverse=np.asarray([m.reshape(4,4,order='F') for m in read(skin['inverseBindMatrices'])]);joint_name={nodes[i]['name']:k for k,i in enumerate(joints)}

def posed_mats(pose):
 cache={}
 def full(i):
  if i in cache:return cache[i]
  transform=mat(nodes[i]);name=nodes[i].get('name')
  if name in pose:
   a=pose[name];c,s=math.cos(a),math.sin(a)
   r=np.array([[1,0,0,0],[0,c,-s,0],[0,s,c,0],[0,0,0,1]])
   transform=transform@r
  cache[i]=(full(parents[i])@transform) if i in parents else transform
  return cache[i]
 return np.stack([full(i)@inverse[k] for k,i in enumerate(joints)])

def save_pose(name,pose):
 palette=posed_mats(pose)
 scene=trimesh.Scene()
 for meshdesc in json_doc['meshes']:
  prim=meshdesc['primitives'][0];a=prim['attributes'];p=read(a['POSITION']).astype(float)
  weights=read(a['WEIGHTS_0']);indices=read(a['JOINTS_0']);faces=read(prim['indices']).flatten().reshape(-1,3)
  hom=np.c_[p,np.ones(len(p))];warp=np.zeros((len(p),3))
  for j in range(4):
   weights_j=weights[:,j]
   for bone in np.unique(indices[:,j][weights_j>.001]):
    selector=(indices[:,j]==bone)&(weights_j>.001)
    warp[selector]+=(hom[selector]@palette[bone].T)[:,:3]*weights_j[selector,None]
  m=trimesh.Trimesh(vertices=warp,faces=faces,process=False)
  mat_desc=json_doc['materials'][prim['material']];color=np.array(mat_desc['pbrMetallicRoughness']['baseColorFactor']);
  m.visual=TextureVisuals(material=PBRMaterial(name=mat_desc['name'],baseColorFactor=[int(x*255) for x in color]))
  scene.add_geometry(m)
 output=OUT/f'A06_{name}_weighted_pose_diagnostic.glb';output.write_bytes(scene.export(file_type='glb'))
 return {'file':str(output.relative_to(BASE))}
poses=[
 ('IDLE',{},'Relaxed neutral pose'),
 ('WALK',{'L_Hip':.43,'R_Hip':-.43,'L_Shoulder':-.31,'R_Shoulder':.31,'R_Knee':.20},'Alternating arm and leg swing'),
 ('CAST',{'R_Shoulder':1.40,'R_Elbow':.18,'Spine':.12},'Throwing net, shoulder drive'),
 ('COLLECT',{'Spine':.22,'L_Shoulder':.75,'L_Elbow':-.54},'Pickup recovery action'),
 ('CRAFT',{'Spine':.10,'L_Shoulder':.64,'R_Shoulder':.64,'L_Elbow':-.74,'R_Elbow':-.63},'Two-handed crafting motion'),
]
W,H=430,550;gap=18;top=111;foot=67;cols=3;rows=2
canvas=Image.new('RGB',(cols*(W+gap)+gap,top+rows*(H+foot+gap)), '#f2f6f4');dr=ImageDraw.Draw(canvas)
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
title=ImageFont.truetype(bold,28);lab=ImageFont.truetype(bold,23);small=ImageFont.truetype(font,15)
dr.text((24,18),'RAFTBOUND / A06 SURVIVOR — WEIGHTED MESH',font=title,fill='#164951')
dr.text((24,63),'CPU diagnostic of exported GLB: 17 bones, 5 evaluated poses • not a Blender or in-game screenshot',font=small,fill='#53767c')
for i,(name,pose,description) in enumerate(poses):
 r,c=divmod(i,cols);x=gap+c*(W+gap);y=top+r*(H+foot+gap)
 rec=save_pose(name.lower(),pose);im=render(rec,(W,H));canvas.paste(im,(x,y))
 dr.text((x+12,y+H+4),name,font=lab,fill='#193f47')
 dr.text((x+12,y+H+36),description,font=small,fill='#607b7c')
dest=OUT/'survivor_A06_motion_sheet.png';canvas.save(dest,optimize=True)
print(dest)
