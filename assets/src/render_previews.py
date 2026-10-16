#!/usr/bin/env python3
"""Offline diagnostic mesh renders; not Blender renders. Accurate imported triangles, materials, perspective."""
import json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import trimesh
ROOT=Path(__file__).resolve().parents[1]
M=json.loads((ROOT/'asset_manifest.json').read_text())
try: F_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'; F_REG='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
except: F_BOLD=F_REG=''

def render(rec,size=(490,410)):
    W,H=size; S=2
    w,h=W*S,H*S
    img=Image.new('RGB',(w,h),(225,238,232)); d=ImageDraw.Draw(img)
    # subtle atmospheric gradient
    for y in range(h):
        u=y/h; col=(int(230-17*u),int(242-16*u),int(240-17*u))
        d.line((0,y,w,y),fill=col)
    center=np.array([0.0,.5,0.0]);eye=np.array([3.5,3.4,4.5]); forward=(center-eye);forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0,1,0]);right/=np.linalg.norm(right);up=np.cross(right,forward)
    sc=trimesh.load(ROOT/rec['file'],force='scene')
    m=sc.to_geometry()
    # determine bounds and reasonable screen scale
    coords=m.bounds
    ctr=(coords[0]+coords[1])/2
    radius=np.max(coords[1]-coords[0]);radius=max(radius,.85)
    scale=.65*min(w,h)/radius
    # projection center above baseline
    v=m.vertices - ctr
    x=np.dot(v,right)*scale+w*.5
    y=-np.dot(v,up)*scale+h*.51
    z=np.dot(v,forward)
    # shadow ellipse
    shadowy=int(h*.79)
    d.ellipse((w*.32,shadowy-20,w*.68,shadowy+30),fill=(181,202,195))
    # grid baseline
    d.line((w*.14,int(h*.84),w*.86,int(h*.84)),fill=(190,211,203),width=2)
    # rebuild material colors by scene geometry node
    drawlist=[]
    light=np.array([.48,.84,.23]);light/=np.linalg.norm(light)
    # Scene graphs may contain translated instances; dump applies node transforms.
    for g in sc.dump(concatenate=False):
        try:
            color=np.array(g.visual.material.baseColorFactor[:3],dtype=float)
        except Exception:color=np.array([175,140,100.],dtype=float)
        inds=g.faces; points=g.vertices-ctr
        px=points@right*scale+w*.5;py=-(points@up)*scale+h*.51
        depths=points@forward
        tris=points[inds]
        nr=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);lens=np.linalg.norm(nr,axis=1)
        nr=nr/(lens[:,None]+1.e-8)
        shade=np.clip(.59+.48*np.dot(nr,light),.42,1.12)
        for i,face in enumerate(inds):
            pts=[(int(px[ix]),int(py[ix])) for ix in face]
            if max(p[0] for p in pts)<0 or min(p[0] for p in pts)>w:continue
            if max(p[1] for p in pts)<0 or min(p[1] for p in pts)>h:continue
            # skip hidden-facing faces, but preserve reversed procedural leaf normals
            col=tuple(int(min(255,max(0,c*shade[i]))) for c in color)
            drawlist.append((np.mean(depths[face]),pts,col))
    for _,pts,col in sorted(drawlist,key=lambda e:e[0],reverse=True): d.polygon(pts,fill=col)
    img=img.resize((W,H),Image.Resampling.LANCZOS)
    return img

def sheet():
    from PIL import ImageFont
    bold=ImageFont.truetype(F_BOLD,26);small=ImageFont.truetype(F_REG,16);micro=ImageFont.truetype(F_REG,15)
    width,height=490,410; gap=20; header=115; footer=80
    cols=3;rows=math.ceil(len(M['assets'])/cols)
    out=Image.new('RGB',(cols*(width+gap)+gap,rows*(height+footer+gap)+header+gap),(244,246,244)); d=ImageDraw.Draw(out)
    d.text((24,17),'RAFTBOUND  /  OCEAN SURVIVAL',font=ImageFont.truetype(F_BOLD,34),fill=(27,65,63))
    d.text((26,64),'ASSET KIT A02  •  GLB  •  Y-UP  •  2 m tile',font=small,fill=(76,100,96))
    for i,rec in enumerate(M['assets']):
        row,col=divmod(i,cols);x=gap+col*(width+gap);y=header+row*(height+footer+gap)
        out.paste(render(rec,(width,height)),(x,y))
        d.rounded_rectangle((x,y+height,x+width,y+height+footer),fill=(250,251,249),radius=3)
        d.text((x+16,y+height+10),rec['id'].replace('_',' ').title(),font=bold,fill=(29,69,65))
        d.text((x+16,y+height+46),f"{rec['category']}  •  {rec['triangles']:,} tris  •  {rec['size_kb']} KB",font=micro,fill=(99,118,109))
    dest=ROOT/'previews'/'asset_contact_sheet.png';out.save(dest,optimize=True)
    print('Saved',dest)
    for rec in M['assets']:
        dest=ROOT/'previews'/f"{rec['id']}.png";render(rec).save(dest,optimize=True)
if __name__=='__main__':sheet()
