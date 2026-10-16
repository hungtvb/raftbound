#!/usr/bin/env python3
"""Offline raster QA of exported A07 COLOR_0 skinned mesh (NOT Blender/GPU)."""
import math, json, struct, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
BASE=Path(__file__).resolve().parents[1];OUT=BASE/'previews';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(BASE/'tests'))
from validate_A07 import parse,read
J,B=parse((BASE/'glb/survivor_sailor_skinned.glb').read_bytes())
nodes=J['nodes']; parents={c:i for i,n in enumerate(nodes) for c in n.get('children',[])}
skin=J['skins'][0];joints=skin['joints'];inv=np.stack([m.reshape(4,4,order='F') for m in read(J,B,skin['inverseBindMatrices'])]);
mesh_data=[]
for m in J['meshes']:
 p=m['primitives'][0];a=p['attributes']
 mesh_data.append((read(J,B,a['POSITION']).astype('f8'),read(J,B,a['WEIGHTS_0']).astype('f8'),read(J,B,a['JOINTS_0']).astype('i4'),read(J,B,p['indices']).astype('i4').flatten().reshape(-1,3),read(J,B,a['COLOR_0']).astype('f8')))

def matrices(pose):
 cache={}
 def visit(i):
  if i in cache:return cache[i]
  n=nodes[i];v=np.array(n.get('matrix',[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]),float).reshape(4,4,order='F')
  name=n.get('name')
  if name in pose:
   ang=pose[name];c,s=math.cos(ang),math.sin(ang)
   rot=np.array([[1,0,0,0],[0,c,-s,0],[0,s,c,0],[0,0,0,1]])
   v=v@rot
  cache[i]=visit(parents[i])@v if i in parents else v
  return cache[i]
 return [visit(idx)@inv[k] for k,idx in enumerate(joints)]

def geo(pose):
 pal=matrices(pose);result=[]
 for p,w,j,faces,col in mesh_data:
  p4=np.c_[p,np.ones(len(p))];warped=np.zeros((len(p),3))
  for bone in range(len(pal)):
   for slot in range(4):
    mask=(j[:,slot]==bone)&(w[:,slot]>.00001)
    if mask.any():warped[mask]+=(p4[mask]@pal[bone].T)[:,:3]*w[mask,slot,None]
  result.append((warped,faces,col))
 return result

def render(geom,eye, size=(400,495)):
 W,H=size;S=1;w,h=W*S,H*S
 im=Image.new('RGB',(w,h),(218,235,232));draw=ImageDraw.Draw(im)
 for y in range(h):
  t=y/h;draw.line((0,y,w,y),fill=(int(234-24*t),int(246-21*t),int(242-20*t)))
 center=np.array([0,.91,0],float);eye=np.array(eye,float)
 forward=center-eye;forward/=np.linalg.norm(forward)
 right=np.cross(forward,[0,1,0]);right/=np.linalg.norm(right);up=np.cross(right,forward)
 scale=H*.48
 ground=int(H*.91);draw.ellipse((W*.28,ground-10,W*.72,ground+14),fill=(173,198,193))
 light=np.array([.4,.85,-.35]);light/=np.linalg.norm(light)
 tris=[]
 for points,faces,color in geom:
  loc=points-center
  px=loc@right*scale+W*.5;py=-(loc@up)*scale+H*.5;depth=loc@forward
  xyz=loc[faces];nn=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]);nn/=np.maximum(np.linalg.norm(nn,axis=1,keepdims=True),1e-10)
  shades=np.clip(.72+.38*(nn@light),.46,1.15)
  for i,face in enumerate(faces):
   pts=[(round(px[k]),round(py[k])) for k in face]
   if max(x for x,y in pts)<0 or min(x for x,y in pts)>=W or max(y for x,y in pts)<0 or min(y for x,y in pts)>=H:continue
   shade=shades[i];rgb=tuple(int(np.clip(c*255*shade,0,255)) for c in color[face[0]])
   tris.append((float(depth[face].mean()),pts,rgb))
 for _,pts,col in sorted(tris,key=lambda t:t[0],reverse=True):draw.polygon(pts,fill=col)
 return im

bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf';reg='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
fontTitle=ImageFont.truetype(bold,29);fontSubtitle=ImageFont.truetype(reg,15);fontLabel=ImageFont.truetype(bold,18)
labels=[('FRONT',[0,2.35,-5.8],{}),('THREE-QUARTER',[-4,2.3,-5],{}),('PROFILE',[-5.5,2.22,0],{}),('BACK',[0,2.35,5.8],{}),('CAST',[3.9,2.25,-4.8],{'R_Shoulder':1.4,'R_Elbow':.18,'Spine':.12})]
W,H=400,495;gap=18;head=118;footer=52;cols=3;rows=2
sheet=Image.new('RGB',(gap+cols*(W+gap),head+rows*(H+gap+footer)),(246,249,247));d=ImageDraw.Draw(sheet)
d.text((24,19),'RAFTBOUND / A07 SURVIVOR MODEL',fill='#204f53',font=fontTitle)
d.text((24,62),'REAL GLB vertices + COLOR_0 + weighted CPU skinning; offline QA (not Blender/WebGL)',fill='#637b79',font=fontSubtitle)
d.text((24,83),'17 bones  •  18,628 triangles  •  2 material batches  •  30 preserved colors',fill='#637b79',font=fontSubtitle)
rest=geo({})
for i,(name,eye,pose) in enumerate(labels):
 row,col=divmod(i,cols);x=gap+col*(W+gap);y=head+row*(H+gap+footer)
 shot=render(geo(pose) if pose else rest,eye,(W,H));sheet.paste(shot,(x,y))
 d.rounded_rectangle((x,y+H,x+W,y+H+footer-4),radius=5,fill='#ffffff')
 d.text((x+14,y+H+11),name,fill='#275258',font=fontLabel)
path=OUT/'A07_packed_character_multiview_CPU.png';sheet.save(path,optimize=True)
print('SAVED',path,path.stat().st_size)
