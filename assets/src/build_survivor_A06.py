#!/usr/bin/env python3
"""RAFTBOUND A06 authored procedural hero mesh (Y-up, front -Z).
Keep 17 published A04 bone node names for runtime compatibility. Materials are
palette-based PBR; meshes are independent editable glTF objects in Blender.
This script requires numpy and trimesh and produces a geometric source rig.
"""
from __future__ import annotations
import json, math, random
from pathlib import Path
import numpy as np
import trimesh
from trimesh.visual import TextureVisuals
from trimesh.visual.material import PBRMaterial
BASE=Path(__file__).resolve().parents[1]; OUT=BASE/'glb';OUT.mkdir(exist_ok=True)
scene=trimesh.Scene();rng=random.Random(14)
C={
 'skin':'#CD9670','skin_bright':'#E8B78A','skin_shadow':'#A66B52',
 'shirt':'#E7C691','shirt_dark':'#C29D68','sleeve':'#D8B67C',
 'vest':'#318492','vest_shade':'#205863','vest_light':'#61A6AA','seam':'#EDDBB3',
 'pants':'#3B5968','pants_dark':'#293E4C','pants_seam':'#82969A',
 'boots':'#594238','sole':'#292B2B','boot_trim':'#8A634D',
 'hat':'#D2B275','hat_light':'#E6CC92','hat_dark':'#846A48',
 'hair':'#3A302B','hair_light':'#514139','eye':'#242D2D','eye_white':'#F3EDE1',
 'belt':'#644C37','buckle':'#D4B66E','bag':'#976B4D','bag_dark':'#604837',
 'rope':'#DED09B','necklace':'#B7985B','compass':'#D8C797','cheek':'#D68C71'
}
tri={}; named=set()
def rgba(key):
 h=C[key].strip('#');return [int(h[i:i+2],16) for i in (0,2,4)]+[255]
def mat(name):return PBRMaterial(name=name,baseColorFactor=rgba(name),roughnessFactor=.88 if name not in ('buckle','compass') else .39,metallicFactor=.02 if name not in ('buckle','compass') else .45,doubleSided=True)
def trans(x=0,y=0,z=0):
 a=np.eye(4);a[:3,3]=[x,y,z];return a
def joint(name,parent,x=0,y=0,z=0):scene.graph.update(frame_to=name,frame_from=parent,matrix=trans(x,y,z))
def add(name,parent,mesh,m):
 assert name not in named,name;named.add(name)
 mesh.visual=TextureVisuals(material=mat(m));scene.add_geometry(mesh,node_name=name,parent_node_name=parent);tri[name]=len(mesh.faces)
def sphere(name,parent,center,radii,m,detail=2):
 mesh=trimesh.creation.icosphere(subdivisions=detail);mesh.apply_scale(radii);mesh.apply_translation(center);add(name,parent,mesh,m)
def cube(name,parent,center,ext,m):
 mesh=trimesh.creation.box(extents=ext);mesh.apply_translation(center);add(name,parent,mesh,m)
def loft(name,parent,rings,m,segments=18,cap=True,angle=0):
 """Soft organic tapered garment and limb surface from (y,rx,rz,cx,cz) profiles."""
 verts=[]
 for k,(y,rx,rz,cx,cz) in enumerate(rings):
  for i in range(segments):
   a=2*math.pi*i/segments+angle
   verts.append([cx+rx*math.cos(a),y,cz+rz*math.sin(a)])
 faces=[]
 for j in range(len(rings)-1):
  for i in range(segments):
   a=j*segments+i;b=j*segments+(i+1)%segments;c=(j+1)*segments+i;d=(j+1)*segments+(i+1)%segments
   faces.extend([[a,c,b],[b,c,d]])
 if cap:
  l=len(verts);verts.append(np.mean(verts[:segments],axis=0));verts.append(np.mean(verts[-segments:],axis=0))
  for i in range(segments):
   j=(i+1)%segments;faces.append([l,i,j]);faces.append([l+1,(len(rings)-1)*segments+j,(len(rings)-1)*segments+i])
 obj=trimesh.Trimesh(vertices=np.array(verts),faces=np.array(faces),process=False);add(name,parent,obj,m)
def band(name,parent,p0,p1,r,m,sections=9):
 p0=np.array(p0,float);p1=np.array(p1,float);vec=p1-p0;length=np.linalg.norm(vec)
 mesh=trimesh.creation.cylinder(radius=r,height=length,sections=sections);mesh.apply_transform(trimesh.geometry.align_vectors([0,0,1],vec/length));mesh.apply_translation((p0+p1)/2);add(name,parent,mesh,m)
def hoop(name,parent,center,major,minor,m,segments=40,side=7,orientation='xz'):
 verts=[];faces=[]
 for i in range(segments):
  a=math.tau*i/segments
  for j in range(side):
   b=math.tau*j/side;rad=major+minor*math.cos(b)
   if orientation=='xz':p=[center[0]+rad*math.cos(a),center[1]+minor*math.sin(b),center[2]+rad*math.sin(a)]
   else:p=[center[0]+rad*math.cos(a),center[1]+rad*math.sin(a),center[2]+minor*math.sin(b)]
   verts.append(p)
 for i in range(segments):
  ni=(i+1)%segments
  for j in range(side):
   nj=(j+1)%side;a=i*side+j;b=i*side+nj;c=ni*side+j;d=ni*side+nj;faces.extend([[a,c,b],[b,c,d]])
 add(name,parent,trimesh.Trimesh(vertices=verts,faces=faces,process=False),m)
# Keep A04 root, bone local origins, orientation, scaling. These are animation ABI.
scene.graph.update(frame_to='RB_Root',frame_from='world',matrix=trans(0,.245,0)@np.diag([.57,.57,.57,1]))
joint('Hips','RB_Root',0,.96,0);joint('Spine','Hips',0,.20,0)
joint('Neck','Spine',0,.83,0);joint('Head','Neck',0,.22,0)
for side in (-1,1):
 pre='L' if side==-1 else 'R'
 joint(f'{pre}_Hip','Hips',side*.174,-.105,0)
 joint(f'{pre}_Knee',f'{pre}_Hip',0,-.61,0)
 joint(f'{pre}_Ankle',f'{pre}_Knee',0,-.46,0)
 joint(f'{pre}_Shoulder','Spine',side*.374,.74,0)
 joint(f'{pre}_Elbow',f'{pre}_Shoulder',side*.025,-.52,0)
 joint(f'{pre}_Wrist',f'{pre}_Elbow',0,-.46,0)
# BODY: continuous loft torso garment with chest narrowing to waist, tucked shirt undershirt.
loft('body_undershirt','Spine',[(.0,.29,.20,0,0),(.17,.33,.22,0,0),(.36,.36,.23,0,.005),(.58,.376,.239,0,.009),(.78,.35,.21,0,0),(.88,.19,.16,0,0)],'shirt',24)
loft('collar_rib','Spine',[(.78,.197,.174,0,-.005),(.81,.183,.162,0,-.01),(.875,.143,.145,0,-.007)],'shirt_dark',24)
# Tailored sleeveless vest front as two curved sculpted panels rather than oval blocks.
for side in (-1,1):
 pre='L' if side==-1 else 'R'
 rings=[]
 for y,rx,rz,xx in [(.065,.095,.052,.227),(.16,.102,.065,.223),(.38,.135,.085,.217),(.63,.134,.093,.229),(.77,.098,.067,.235)]:
  rings.append((y,rx,rz,side*xx,-.186))
 loft(f'{pre}_vest_body','Spine',rings,'vest',16)
 # front lapel creates a V-shaped opening at the neck
 band(f'{pre}_lapel','Spine',(side*.075,.43,-.23),(side*.235,.77,-.177),.021,'vest_light',10)
 # curved lower piping and lower pockets
 band(f'{pre}_pocket_top','Spine',(side*.15,.23,-.269),(side*.302,.22,-.25),.014,'seam')
 cube(f'{pre}_vest_tab','Spine',(side*.229,.185,-.264),(.113,.093,.025),'vest_shade')
 sphere(f'{pre}_button','Spine',(side*.108,.32,-.262),(.015,.014,.009),'buckle',1)
# central overshirt placket, small clasp, bandana at collar
band('shirt_front_seam','Spine',(0,.06,-.22),(0,.50,-.254),.011,'shirt_dark')
loft('waist_hips','Hips',[(-.16,.256,.18,0,0),(-.04,.29,.214,0,0),(.12,.302,.218,0,0),(.19,.290,.21,0,0)],'pants',18)
loft('belt_loop','Hips',[(.085,.303,.22,0,0),(.14,.302,.219,0,0)],'belt',18)
cube('brass_belt_buckle','Hips',(0,.109,-.228),(.112,.092,.032),'buckle')
cube('buckle_hole','Hips',(0,.109,-.247),(.066,.053,.015),'belt')
# Rugged compact backpack with a rolled sleeping mat and shoulder straps.
loft('pack_body','Spine',[(.12,.19,.11,0,.26),(.19,.29,.20,0,.31),(.43,.31,.217,0,.325),(.64,.29,.197,0,.302),(.7,.23,.14,0,.27)],'bag',18)
loft('pack_flap','Spine',[(.57,.30,.212,0,.334),(.66,.295,.215,0,.338),(.70,.235,.171,0,.303)],'bag_dark',18)
band('pack_center_strap','Spine',(0,.19,.525),(0,.65,.520),.018,'rope')
cube('pack_clasp','Spine',(0,.46,.538),(.08,.067,.026),'buckle')
for side in (-1,1):
 pre='L' if side==-1 else 'R'
 band(f'{pre}_shoulder_strap','Spine',(side*.28,.73,.01),(side*.255,.28,-.12),.039,'bag_dark')
 band(f'{pre}_shoulder_strap_edge','Spine',(side*.284,.72,-.012),(side*.263,.30,-.147),.011,'rope')
# Rolled blanket visibly strapped across bag upper back.
band('blanket_roll','Spine',(-.285,.70,.386),(.285,.70,.386),.083,'shirt_dark',16)
for ix in (-.19,.19):hoop(f'blanket_rope_{ix}','Spine',(ix,.70,.386),.087,.013,'rope',24,6,orientation='yz')
# NECK + HEAD with stylized face, facial planes, a distinct nose, hair and soft brimmed hat.
loft('neck_geometry','Neck',[(-.09,.104,.104,0,0),(.035,.122,.117,0,0),(.13,.112,.108,0,0)],'skin',16)
sphere('head_cranium','Head',(0,.14,.0),(.261,.296,.235),'skin',3)
sphere('jaw_cheeks','Head',(0,-.007,-.078),(.221,.190,.191),'skin',2)
sphere('chin','Head',(0,-.070,-.134),(.152,.082,.094),'skin_shadow',2)
sphere('nose_bridge','Head',(0,.113,-.241),(.049,.104,.040),'skin_bright',2)
sphere('nose_tip','Head',(0,.043,-.286),(.080,.055,.058),'skin',2)
for side in (-1,1):
 pre='L' if side==-1 else 'R'
 sphere(f'{pre}_ear','Head',(side*.250,.079,-.014),(.070,.104,.063),'skin',2)
 sphere(f'{pre}_ear_inset','Head',(side*.304,.08,-.046),(.016,.043,.027),'skin_shadow',2)
 sphere(f'{pre}_cheek','Head',(side*.128,.009,-.207),(.087,.039,.034),'cheek',2)
 sphere(f'{pre}_eye_white','Head',(side*.104,.162,-.215),(.043,.052,.019),'eye_white',2)
 sphere(f'{pre}_iris','Head',(side*.109,.160,-.233),(.024,.038,.012),'eye',2)
 sphere(f'{pre}_catchlight','Head',(side*.115,.176,-.247),(.009,.010,.006),'eye_white',1)
 band(f'{pre}_brow','Head',(side*.062,.248,-.227),(side*.169,.242,-.198),.020,'hair',10)
# relaxed smile, moustache/dots subtle
band('mouth_smile','Head',(-.068,-.066,-.218),(.068,-.066,-.218),.008,'hair',10)
sphere('hair_cap','Head',(0,.295,.018),(.255,.107,.232),'hair',2)
for side in (-1,1):
 sphere(f'hair_tuft_{side}','Head',(side*.224,.26,-.056),(.08,.075,.095),'hair_light',1)
# woven straw hat crown uses tapered multi-ring surface, brim is smooth flattened ellipsoid/torus
loft('hat_crown','Head',[(.33,.285,.254,0,.0),(.405,.293,.264,0,.012),(.535,.262,.236,0,.014),(.577,.195,.19,0,.011)],'hat',32)
loft('hat_upper_crown','Head',[(.559,.205,.185,0,.012),(.586,.153,.142,0,.010)],'hat_light',32)
loft('hat_headband','Head',[(.375,.297,.273,0,.003),(.427,.296,.273,0,.01)],'hat_dark',32)
# flattened brim made from rings around head to avoid ellipsoidal frisbee shape
rings=[];segments=48;verts=[];faces=[]
for radx,radz,height in [(.270,.248,.351),(.392,.342,.349),(.449,.380,.340),(.467,.382,.348)]:
 for k in range(segments):
  a=math.tau*k/segments;verts.append([radx*math.cos(a),height+.017*math.cos(a*2),radz*math.sin(a)-.018])
for i in range(3):
 for k in range(segments):
  a=i*segments+k;b=i*segments+(k+1)%segments;c=(i+1)*segments+k;d=(i+1)*segments+(k+1)%segments;faces.extend([[a,b,c],[b,d,c]])
add('straw_hat_brim','Head',trimesh.Trimesh(vertices=verts,faces=faces,process=False),'hat_light')
# stitched hat brim stripes
for r in (.394,.435):
 verts=[];faces=[]
 for k in range(48):
  a=math.tau*k/48
  for h in (0,.008):verts.append([r*math.cos(a),.346+h+.013*math.cos(a*2),r*.825*math.sin(a)-.017])
 for k in range(48):
  a=2*k;b=2*((k+1)%48);faces.extend([[a,a+1,b],[a+1,b+1,b]])
 add(f'brim_stitch_{r}','Head',trimesh.Trimesh(vertices=verts,faces=faces,process=False),'hat_dark')
# LEGS, knee seam, boot cuffs and soles. Tapered sections overlap at joints.
for side in (-1,1):
 pre='L' if side==-1 else 'R';hip=f'{pre}_Hip';knee=f'{pre}_Knee';ankle=f'{pre}_Ankle'
 loft(f'{pre}_tailored_thigh',hip,[(.045,.160,.158,0,0),(-.08,.170,.170,0,0),(-.24,.169,.17,side*.008,-.011),(-.40,.148,.154,side*.006,-.012),(-.56,.129,.132,0,-.005),(-.66,.128,.128,0,-.007)],'pants',20)
 loft(f'{pre}_pants_shin',knee,[(.08,.135,.134,0,0),(-.04,.144,.140,0,0),(-.21,.135,.128,0,0),(-.38,.108,.118,0,.007),(-.49,.107,.12,0,.018)],'pants',20)
 loft(f'{pre}_knee_reinforce',knee,[(.00,.143,.143,0,-.006),(-.06,.144,.153,0,-.01),(-.15,.141,.147,0,-.006)],'pants_dark',18)
 band(f'{pre}_knee_patch_stitch',knee,(-.105,-.075,-.151),(.105,-.075,-.151),.009,'pants_seam')
 # top boot, leather with sizeable forward toe and discreet sole
 loft(f'{pre}_boot_cuff',ankle,[(.11,.118,.12,0,.03),(.04,.153,.147,0,.018),(-.095,.157,.145,0,.012)],'boot_trim',18)
 sphere(f'{pre}_boot_upper',ankle,(0,-.103,-.052),(.169,.155,.225),'boots',2)
 sphere(f'{pre}_toe',ankle,(0,-.165,-.190),(.174,.101,.145),'boots',2)
 loft(f'{pre}_boot_sole',ankle,[(-.196,.170,.248,0,-.092),(-.249,.177,.258,0,-.092)],'sole',20)
 band(f'{pre}_boot_trim_top',ankle,(-.105,-.052,-.124),(.105,-.052,-.124),.013,'rope')
 # sleeve, tapered forearm and proper hand with thumb and individually curved fingers
 shoulder=f'{pre}_Shoulder';elbow=f'{pre}_Elbow';wrist=f'{pre}_Wrist'
 sphere(f'{pre}_shoulder_roundcap',shoulder,(0,.008,0),(.150,.139,.148),'sleeve',2)
 loft(f'{pre}_shoulder_sleeve',shoulder,[(.105,.128,.121,0,0),(.050,.152,.145,side*.004,0),(-.055,.166,.157,side*.007,0),(-.16,.164,.153,side*.010,-.002),(-.245,.150,.142,side*.014,-.002),(-.296,.140,.135,side*.015,0)],'sleeve',18)
 loft(f'{pre}_sleeve_cuff',shoulder,[(-.271,.142,.136,side*.014,0),(-.307,.137,.135,side*.014,0)],'shirt_dark',16)
 loft(f'{pre}_upper_arm',shoulder,[(-.270,.138,.125,side*.02,0),(-.356,.135,.125,side*.02,0),(-.46,.116,.113,side*.024,0),(-.555,.105,.112,side*.024,0)],'skin',18)
 sphere(f'{pre}_elbow_soft',elbow,(0,.024,0),(.110,.126,.114),'skin',2)
 loft(f'{pre}_forearm',elbow,[(.095,.107,.106,0,0),(-.080,.118,.116,0,-.001),(-.23,.105,.105,0,-.002),(-.36,.086,.088,0,0),(-.48,.083,.088,0,0)],'skin',18)
 loft(f'{pre}_wrist_wrap',elbow,[(-.377,.096,.098,0,0),(-.420,.092,.092,0,0)],'rope',16)
 sphere(f'{pre}_palm',wrist,(0,-.118,-.007),(.117,.145,.089),'skin',2)
 sphere(f'{pre}_hand_knuckles',wrist,(0,-.204,-.022),(.116,.070,.092),'skin_bright',2)
 # visible fingers with rounded tips, thumb is offset from palm
 for f in range(4):
  fx=(f-1.5)*.056
  length=[.082,.110,.112,.080][f]
  sphere(f'{pre}_finger_{f}',wrist,(fx,-.241-length*.45,-.031),(.025,length*.62,.032),'skin',1)
 sphere(f'{pre}_thumb',wrist,(side*.113,-.159,-.077),(.044,.098,.046),'skin',2)
 # arm motif sewn seam on top of sleeve
 band(f'{pre}_sleeve_stitch',shoulder,(side*.005,-.185,-.155),(side*.016,-.270,-.143),.010,'seam')
# simple survival necklace/small front token
band('neck_chord_left','Spine',(-.104,.785,-.164),(0,.635,-.247),.010,'rope')
band('neck_chord_right','Spine',(.104,.785,-.164),(0,.635,-.247),.010,'rope')
sphere('neck_token','Spine',(0,.629,-.263),(.034,.041,.015),'compass',2)
# Write authored editable node hierarchy and material mesh bounds.
dest=OUT/'survivor_sailor_rig.glb';dest.write_bytes(scene.export(file_type='glb'))
rec={'id':'survivor_sailor_rig','release':'A06','file':'glb/survivor_sailor_rig.glb','rig_type':'hierarchical glTF bone source for skinned conversion','joint_names':['RB_Root','Hips','Spine','Neck','Head','L_Hip','L_Knee','L_Ankle','R_Hip','R_Knee','R_Ankle','L_Shoulder','L_Elbow','L_Wrist','R_Shoulder','R_Elbow','R_Wrist'],'triangles':sum(tri.values()),'bounds_m':scene.bounds.round(3).tolist(),'parts':len(tri),'material_count':len(C),'size_kb':round(dest.stat().st_size/1024,1),'mesh_parts':tri}
(BASE/'character_manifest.json').write_text(json.dumps(rec,indent=2)+'\n');print({k:v for k,v in rec.items() if k!='mesh_parts'})
