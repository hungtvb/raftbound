#!/usr/bin/env python3
"""Generate an articulated rigid-joint survivor GLB. Geometry authored in Y-up metres.
Each pivot is a real glTF node and can be independently animated at runtime.
This is NOT a skinned vertex-weight rig; it uses named rigid body segment joints.
"""
import json,math
from pathlib import Path
import numpy as np
import trimesh
from trimesh.visual import TextureVisuals
from trimesh.visual.material import PBRMaterial

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'glb';OUT.mkdir(exist_ok=True)
S=trimesh.Scene()
COL={
'skin':'#D69567','skin_shadow':'#A86D4B','shirt':'#D6C37D','shirt_dark':'#A9A067',
'vest':'#30707B','vest_dark':'#224E5A','denim':'#384C62','seam':'#D7D1B2',
'boots':'#483B32','boot_trim':'#75634E','hat':'#D8B678','hat_dark':'#8B6B49',
'hair':'#3E312C','eyes':'#292B2E','white':'#F1E6CF','buckles':'#CBA35F',
'bag':'#886A4B','bag_dark':'#564535','rope':'#E2CA94','band':'#B9A47A',
}
TRIS={}

def rgba(key):
 h=COL[key].lstrip('#');return [int(h[i:i+2],16) for i in (0,2,4)]+[255]
def T(x=0,y=0,z=0):
 t=np.eye(4);t[:3,3]=[x,y,z];return t

def joint(name,parent,x=0,y=0,z=0):
 S.graph.update(frame_to=name,frame_from=parent,matrix=T(x,y,z))

def add(name,parent,geo,material,offset=(0,0,0)):
 geo=geo.copy();geo.apply_translation(offset)
 geo.visual=TextureVisuals(material=PBRMaterial(name=material,baseColorFactor=rgba(material),roughnessFactor=.9,metallicFactor=0,doubleSided=True))
 S.add_geometry(geo,node_name=name,parent_node_name=parent)
 TRIS[name]=len(geo.faces)

def ellip(name,parent,radii,mat,loc=(0,0,0),subdiv=2):
 m=trimesh.creation.icosphere(subdivisions=subdiv);m.apply_scale(radii)
 add(name,parent,m,mat,loc)

def box(name,parent,extents,mat,loc=(0,0,0),bevel=0):
 m=trimesh.creation.box(extents=extents)
 if bevel:
  # Use a very small bevel on hero rigid body segments when optional engine available.
  pass
 add(name,parent,m,mat,loc)

def cylinder(name,parent,r,h,mat,loc=(0,0,0),sections=12):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=sections)
 m.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0])) # z -> y
 add(name,parent,m,mat,loc)

def rod(name,parent,a,b,r,mat):
 vec=np.array(b)-a; ln=np.linalg.norm(vec)
 m=trimesh.creation.cylinder(radius=r,height=ln,sections=8)
 m.apply_transform(trimesh.geometry.align_vectors([0,0,1],vec/ln))
 add(name,parent,m,mat,tuple((np.array(a)+np.array(b))/2))

S.graph.update(frame_to='RB_Root',frame_from='world',matrix=T(0,.245,0)@np.diag([.57,.57,.57,1]))
joint('Hips','RB_Root',0,.96,0)
# Gloved / clothed stylized adventurer. Direction forward -Z.
ellip('hips_denim','Hips',(.31,.19,.21),'denim')
box('belt','Hips',(.62,.105,.42),'boots',(0,.12,0))
box('belt_buckle','Hips',(.12,.095,.033),'buckles',(0,.12,-.22))
joint('Spine','Hips',0,.20,0)
ellip('torso_shirt','Spine',(.38,.52,.245),'shirt',(0,.36,0))
ellip('vest_left','Spine',(.16,.40,.09),'vest',(-.20,.36,-.235))
ellip('vest_right','Spine',(.16,.40,.09),'vest',(.20,.36,-.235))
box('vest_lower','Spine',(.73,.11,.45),'vest_dark',(0,.04,0))
for ix,z in enumerate((-.04,-.20)):
 box(f'vest_pocket_{ix}','Spine',(.18,.16,.065),'vest_dark',((-1)**ix*.20,.19,z-.18))
box('stripe','Spine',(.05,.40,.037),'seam',(0,.34,-.275))
# Backpack: visible from behind.
ellip('pack_body','Spine',(.30,.39,.17),'bag',(0,.38,.33))
box('pack_flap','Spine',(.57,.14,.30),'bag_dark',(0,.62,.36))
box('pack_fastener','Spine',(.12,.12,.035),'buckles',(0,.56,.54))
for ix in (-1,1):
 box(f'pack_strap_{ix}','Spine',(.073,.62,.04),'band',(ix*.25,.32,-.09))
# Head and sun hat.
joint('Neck','Spine',0,.83,0)
ellip('neck_skin','Neck',(.135,.15,.13),'skin',(0,.06,0))
joint('Head','Neck',0,.22,0)
ellip('head_skin','Head',(.257,.29,.246),'skin',(0,.12,0))
ellip('nose','Head',(.075,.08,.088),'skin',(0,.095,-.234),subdiv=1)
for side in (-1,1):
 ellip(f'ear_{side}','Head',(.07,.105,.067),'skin',(side*.243,.115,0),subdiv=1)
 ellip(f'eye_{side}','Head',(.025,.035,.015),'eyes',(side*.106,.155,-.234),subdiv=1)
 ellip(f'brow_{side}','Head',(.075,.018,.025),'hair',(side*.105,.224,-.23),subdiv=1)
ellip('hair_cap','Head',(.258,.15,.249),'hair',(0,.33,.025))
ellip('hat_crown','Head',(.294,.18,.298),'hat',(0,.43,0))
ellip('hat_brim','Head',(.410,.038,.385),'hat',(0,.32,-.036),subdiv=2)
ellip('hat_band','Head',(.308,.052,.31),'hat_dark',(0,.355,-.003),subdiv=2)
# Legs, each hip joint pivot at center hips; calf pivots at lower ends.
for side in (-1,1):
 prefix='L' if side==-1 else 'R';x=side*.174
 joint(f'{prefix}_Hip','Hips',x,-.105,0)
 ellip(f'{prefix}_thigh',f'{prefix}_Hip',(.165,.345,.175),'denim',(0,-.31,0))
 box(f'{prefix}_seam',f'{prefix}_Hip',(.03,.29,.034),'seam',(side*.105,-.30,-.166))
 joint(f'{prefix}_Knee',f'{prefix}_Hip',0,-.61,0)
 ellip(f'{prefix}_shin',f'{prefix}_Knee',(.134,.30,.14),'denim',(0,-.23,0))
 joint(f'{prefix}_Ankle',f'{prefix}_Knee',0,-.46,0)
 ellip(f'{prefix}_boot',f'{prefix}_Ankle',(.18,.17,.28),'boots',(0,-.038,-.104))
 ellip(f'{prefix}_boot_sole',f'{prefix}_Ankle',(.187,.044,.286),'boot_trim',(0,-.159,-.11),subdiv=2)
 # arm from shoulder; shoulders pivot near upper torso
 joint(f'{prefix}_Shoulder','Spine',side*.395,.74,0)
 ellip(f'{prefix}_sleeve',f'{prefix}_Shoulder',(.18,.22,.17),'shirt',(side*.018,-.145,0))
 ellip(f'{prefix}_upper_arm',f'{prefix}_Shoulder',(.125,.20,.122),'skin',(side*.025,-.37,0))
 joint(f'{prefix}_Elbow',f'{prefix}_Shoulder',side*.025,-.52,0)
 ellip(f'{prefix}_forearm',f'{prefix}_Elbow',(.122,.235,.12),'skin',(0,-.23,0))
 box(f'{prefix}_wrist_wrap',f'{prefix}_Elbow',(.25,.076,.252),'band',(0,-.38,0))
 joint(f'{prefix}_Wrist',f'{prefix}_Elbow',0,-.46,0)
 ellip(f'{prefix}_hand',f'{prefix}_Wrist',(.125,.15,.12),'skin',(0,-.105,0))
 # 4 visible fingers, simplified stylized shapes
 for fi in range(3):
  ellip(f'{prefix}_finger_{fi}',f'{prefix}_Wrist',(.039,.115,.048),'skin',(fi*.07-.07,-.215,-.013),subdiv=1)

OUTFILE=OUT/'survivor_sailor_rig.glb'
OUTFILE.write_bytes(S.export(file_type='glb'))
rec={'id':'survivor_sailor_rig','file':'glb/survivor_sailor_rig.glb','rig_type':'hierarchical rigid-joint glTF nodes','joint_names':['RB_Root','Hips','Spine','Neck','Head','L_Hip','L_Knee','L_Ankle','R_Hip','R_Knee','R_Ankle','L_Shoulder','L_Elbow','L_Wrist','R_Shoulder','R_Elbow','R_Wrist'], 'triangles':sum(TRIS.values()),'size_kb':round(OUTFILE.stat().st_size/1024,1),'bounds_m':S.bounds.round(3).tolist(),'materials':len(COL),'parts':len(TRIS)}
(BASE/'character_manifest.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(rec,indent=2))
