#!/usr/bin/env python3
"""Rasterize ACTUAL diagnostic GLB mesh triangles to multiview QA contact sheet.
The images are CPU diagnostics; they are not Blender, WebGL, or offline AI renders.
"""
import math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import trimesh
BASE=Path(__file__).resolve().parents[1]; out=BASE/'previews';out.mkdir(exist_ok=True)
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
REG='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def diagnostic(path, eye, W=470, H=570):
    S=2; w=W*S;h=H*S
    img=Image.new('RGB',(w,h),(230,241,238));d=ImageDraw.Draw(img)
    for y in range(h):
        f=y/h; d.line((0,y,w,y),fill=(int(235-15*f),int(246-18*f),int(243-16*f)))
    scene=trimesh.load(path,force='scene')
    box=scene.bounds;center=(box[0]+box[1])/2
    view=np.array(eye,float);forward=center-view;forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0,1,0]);right/=np.linalg.norm(right);up=np.cross(right,forward)
    radius=float(np.max(box[1]-box[0]));scale=.86*min(w,h)/max(.85,radius)
    light=np.array([.45,.85,-.25]);light/=np.linalg.norm(light)
    groundY=int(h*.89)
    d.ellipse((w*.30,groundY-19,w*.70,groundY+19),fill=(191,215,211))
    d.line((w*.1,groundY+25,w*.9,groundY+25),fill=(194,218,211),width=2)
    items=[]
    for g in scene.dump(concatenate=False):
        try:color=np.asarray(g.visual.material.baseColorFactor[:3],float)
        except Exception:color=np.array([175,140,103.],float)
        pos=g.vertices-center;faces=g.faces
        px=pos@right*scale+w*.5;py=-(pos@up)*scale+h*.50
        depth=pos@forward
        tris=pos[faces];no=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);no/=np.maximum(np.linalg.norm(no,axis=1,keepdims=True),1.e-7)
        shades=np.clip(.62+.45*(no@light),.42,1.15)
        for i,face in enumerate(faces):
            pts=[(int(px[ix]),int(py[ix])) for ix in face]
            if max(p[0] for p in pts)<0 or min(p[0] for p in pts)>w or max(p[1] for p in pts)<0 or min(p[1] for p in pts)>h:continue
            rgb=tuple(int(np.clip(c*shades[i],0,255)) for c in color)
            items.append((depth[face].mean(),pts,rgb))
    for _,pts,color in sorted(items,key=lambda t:t[0],reverse=True):d.polygon(pts,fill=color)
    return img.resize((W,H),Image.Resampling.LANCZOS)

angles=[('FRONT',[0,2.15,-5.8]),('LEFT ¾',[-4,2.25,-5]),('SIDE',[-5.8,2.15,0]),('BACK',[0,2.15,5.8]),('RIGHT ¾',[4,2.25,-5])]
W,H=470,570;gap=20;head=112;foot=65
canvas=Image.new('RGB',(gap+3*(W+gap),head+gap+2*(H+foot+gap)),(243,247,246));d=ImageDraw.Draw(canvas)
title=ImageFont.truetype(BOLD,31);label=ImageFont.truetype(BOLD,21);small=ImageFont.truetype(REG,16)
d.text((24,20),'RAFTBOUND / A06 CHARACTER REVIEW',font=title,fill=(29,70,73))
d.text((24,66),'Actual GLB triangle rasterization  •  front / ¾ / profile / rear / cast  •  NOT Blender or GPU',font=small,fill=(83,113,113))
idle=out/'A06_idle_weighted_pose_diagnostic.glb';cast=out/'A06_cast_weighted_pose_diagnostic.glb'
for i,(name,eye) in enumerate(angles+[('CAST · ¾',[4,2.25,-5])]):
    row,col=divmod(i,3);x=gap+col*(W+gap);y=head+row*(H+foot+gap)
    image=diagnostic(cast if name.startswith('CAST') else idle,eye,W,H)
    canvas.paste(image,(x,y))
    d.rounded_rectangle((x,y+H,x+W,y+H+foot),radius=5,fill=(252,253,250))
    d.text((x+16,y+H+8),name,font=label,fill=(34,80,84))
    desc='Evaluated weighted GLB / throwing pose' if name.startswith('CAST') else 'Evaluated weighted GLB / idle pose'
    d.text((x+16,y+H+37),desc,font=small,fill=(112,133,133))
file=out/'A06_character_multiview_CPU.png';canvas.save(file,optimize=True)
print('Saved',file)
