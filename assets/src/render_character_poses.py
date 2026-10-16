#!/usr/bin/env python3
"""Diagnostic triangle renders from real GLB, not Blender output."""
import math,sys,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import trimesh
BASE=Path(__file__).resolve().parents[1];OUT=BASE/'previews';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(Path(__file__).parent))
import render_previews
render_previews.ROOT=BASE
source=BASE/'glb/survivor_sailor_rig.glb'
# Use eye in front of survivor, not behind backpack. This affects only preview generator.
import inspect
src=inspect.getsource(render_previews.render).replace('eye=np.array([3.5,3.4,4.5])','eye=np.array([3.5,2.65,-6.0])').replace('scale=.65*min(w,h)/radius','scale=.96*min(w,h)/radius')
exec(src,vars(render_previews),locals_dict:={})
render_front=locals_dict['render']

def poseGLB(name,angles):
 scene=trimesh.load(source,force='scene')
 for joint,angle in angles.items():
  found=[(a,b,d) for a,b,d in scene.graph.to_edgelist() if b==joint]
  if not found:raise ValueError('No joint '+joint)
  parent,_,data=found[0]
  original=np.array(data['matrix'])
  rx=trimesh.transformations.rotation_matrix(angle,[1,0,0])
  scene.graph.update(frame_to=joint,frame_from=parent,matrix=original@rx)
 out=OUT/f'survivor_{name}_POSE_DIAGNOSTIC.glb'
 out.write_bytes(scene.export(file_type='glb'))
 return {'file':str(out.relative_to(BASE))}

poses=[('IDLE',{}),('WALK',{'L_Hip':.43,'R_Hip':-.43,'L_Shoulder':-.31,'R_Shoulder':.31,'R_Knee':.20}),('CAST',{'R_Shoulder':1.55,'R_Elbow':.22,'Spine':.09})]
W,H=560,700
canvas=Image.new('RGB',(3*W+4*28,H+155),'#f4f6f3');d=ImageDraw.Draw(canvas)
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
namef=ImageFont.truetype(bold,25);titlef=ImageFont.truetype(bold,30);smallf=ImageFont.truetype(font,16)
d.text((30,12),'RAFTBOUND  /  A03 SURVIVOR MOTION STUDY',font=titlef,fill='#1b4e56')
d.text((30,58),'Actual posed GLB meshes • rigid-joint hierarchy • diagnostic offline render, not Blender',font=smallf,fill='#577278')
for i,(name,angles) in enumerate(poses):
 rec=poseGLB(name.lower(),angles)
 img=render_front(rec,(W,H))
 x=28+i*(W+28);canvas.paste(img,(x,104))
 d.text((x+18,H+117),name,font=namef,fill='#193d47')
 d.text((x+18,H+150),('Relaxed neutral pose','Alternating leg + arm swing','Shoulder swing and follow-through')[i],font=smallf,fill='#617b78')
out=OUT/'survivor_motion_sheet.png';canvas.save(out,optimize=True)
print('Saved',out)
