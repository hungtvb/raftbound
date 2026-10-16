#!/usr/bin/env python3
"""Convert A06's articulated survivor into a glTF 2.0 weighted skinned mesh.
The mesh is packed per material, shares a 17-joint skeleton, and exports
JOINTS_0 / WEIGHTS_0 / inverseBindMatrices. All coordinates are Y-up metres.
Deterministic; no Blender dependency. Blender can import/edit resulting skin.
"""
import json, struct
from collections import defaultdict
from pathlib import Path
import numpy as np

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE/'glb/survivor_sailor_rig.glb'
DEST = BASE/'glb/survivor_sailor_skinned.glb'
JOINT_NAMES = ['RB_Root','Hips','Spine','Neck','Head','L_Hip','L_Knee','L_Ankle','R_Hip','R_Knee','R_Ankle','L_Shoulder','L_Elbow','L_Wrist','R_Shoulder','R_Elbow','R_Wrist']

b=SOURCE.read_bytes()
assert struct.unpack_from('<III', b, 0)==(0x46546c67,2,len(b))
length,kind=struct.unpack_from('<II',b,12)
assert kind==0x4e4f534a
src=json.loads(b[20:20+length]); offset=20+length
blen,bkind=struct.unpack_from('<II',b,offset)
assert bkind==0x004e4942
blob=b[offset+8:offset+8+blen]
COMP={5121:('u1',1),5123:('<u2',2),5125:('<u4',4),5126:('<f4',4)}
DIMS={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def get_acc(i):
 a=src['accessors'][i];v=src['bufferViews'][a['bufferView']];dtype,sz=COMP[a['componentType']];w=DIMS[a['type']]
 start=v.get('byteOffset',0)+a.get('byteOffset',0); stride=v.get('byteStride',sz*w)
 if stride==sz*w: return np.frombuffer(blob,dtype=dtype,count=a['count']*w,offset=start).copy().reshape(-1,w)
 return np.stack([np.frombuffer(blob,dtype=dtype,count=w,offset=start+n*stride) for n in range(a['count'])])
def matrix(node):
 if 'matrix' in node: return np.asarray(node['matrix'],np.float64).reshape((4,4),order='F')
 t=np.asarray(node.get('translation',[0,0,0]),np.float64);s=np.asarray(node.get('scale',[1,1,1]),np.float64)
 x,y,z,w=node.get('rotation',[0,0,0,1]);r=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]],dtype=np.float64)
 out=np.eye(4);out[:3,:3]=r*s;out[:3,3]=t;return out
parent={}
for i,n in enumerate(src['nodes']):
 for child in n.get('children',[]):parent[child]=i
world={}
def full(i):
 if i in world:return world[i]
 M=matrix(src['nodes'][i]);world[i]=full(parent[i])@M if i in parent else M
 return world[i]
for i in range(len(src['nodes'])):full(i)
name_id={n.get('name'):i for i,n in enumerate(src['nodes'])}
for n in JOINT_NAMES:assert n in name_id,n
idx_joint={name:k for k,name in enumerate(JOINT_NAMES)}
rest={name:world[name_id[name]] for name in JOINT_NAMES}
mat_prims=defaultdict(lambda:{'positions':[],'normals':[],'weights':[],'joints':[],'indices':[],'count':0})

# Blending around hips/knees and shoulders/elbows avoids the rigid limb motion of A03.
# Original A03 headgear and small accessories remain rigid weighted geometry.
def influences(name,local):
 """Continuous influence falloff across garment and elbow/knee seams.
 Max 3 meaningful bones per vertex: original anchor, distal and proximal.
 Geometry rests in bone-aligned local coordinates; use glTF 4-weight slots.
 """
 y=local[:,1];N=len(y)
 distal=None;proximal=None
 dst=np.zeros(N);prox=np.zeros(N)
 if name in ('L_Hip','R_Hip'):
  distal=name.replace('Hip','Knee');proximal='Hips'
  dst=np.clip((-y-.29)/.37,0,.48)
  prox=np.clip((y+.16)/.22,0,.23)
 elif name in ('L_Shoulder','R_Shoulder'):
  distal=name.replace('Shoulder','Elbow');proximal='Spine'
  dst=np.clip((-y-.25)/.32,0,.48)
  prox=np.clip((y+.16)/.25,0,.27)
 elif name in ('L_Knee','R_Knee','L_Elbow','R_Elbow'):
  distal=name.replace('Knee','Ankle').replace('Elbow','Wrist')
  dst=np.clip((-y-.14)/.32,0,.50)
 elif name=='Spine':
  proximal='Hips';prox=np.clip((.28-y)/.31,0,.28)
 elif name=='Neck':
  proximal='Spine';prox=np.clip((.04-y)/.15,0,.24)
 j=np.zeros((N,4),dtype=np.uint8);w=np.zeros((N,4),dtype=np.float32)
 j[:,0]=idx_joint[name];w[:,0]=1-dst-prox
 if distal is not None:j[:,1]=idx_joint[distal];w[:,1]=dst
 if proximal is not None:j[:,2]=idx_joint[proximal];w[:,2]=prox
 return j,w

for ni,node in enumerate(src['nodes']):
 if 'mesh' not in node:continue
 k=ni;attached='RB_Root'
 while k in parent:
  k=parent[k];name=src['nodes'][k].get('name')
  if name in idx_joint:attached=name;break
 M=world[ni];origin=np.linalg.inv(rest[attached]); normal_mat=np.linalg.inv(M[:3,:3]).T
 for prim in src['meshes'][node['mesh']]['primitives']:
  if prim.get('mode',4)!=4:raise ValueError('Triangles required')
  ps=get_acc(prim['attributes']['POSITION']).astype('f8')
  coords=(M@np.c_[ps,np.ones(len(ps))].T).T[:,:3]
  local=(origin@np.c_[coords,np.ones(len(coords))].T).T[:,:3]
  if 'NORMAL' in prim['attributes']:
   ns=get_acc(prim['attributes']['NORMAL']).astype('f8')@normal_mat.T
   ns/=np.maximum(np.linalg.norm(ns,axis=1,keepdims=True),1e-7)
  else:
   ns=np.zeros_like(coords)
  ids=get_acc(prim['indices']).reshape(-1).astype('u4') if 'indices' in prim else np.arange(len(coords),dtype='u4')
  if 'NORMAL' not in prim['attributes']:
   for aa,bb,cc in ids.reshape(-1,3):
    face=np.cross(coords[bb]-coords[aa],coords[cc]-coords[aa]);ns[[aa,bb,cc]]+=face
   ns/=np.maximum(np.linalg.norm(ns,axis=1,keepdims=True),1e-7)
  j,w=influences(attached,local)
  acc=mat_prims[prim.get('material',0)];start=acc['count'];acc['count']+=len(ps)
  for key,arr in [('positions',coords.astype('f4')),('normals',ns.astype('f4')),('joints',j),('weights',w),('indices',ids+start)]:acc[key].append(arr)

outbin=bytearray();views=[];accessors=[]
def add_acc(values,comp,atype,target=None,with_bounds=False):
 arr=np.asarray(values)
 while len(outbin)%4:outbin.append(0)
 at=len(outbin);outbin.extend(arr.tobytes(order='C'))
 bv={'buffer':0,'byteOffset':at,'byteLength':arr.nbytes}
 if target is not None:bv['target']=target
 vi=len(views);views.append(bv)
 ac={'bufferView':vi,'componentType':comp,'count':len(arr),'type':atype}
 if with_bounds:
  ac['min']=arr.min(axis=0).astype(float).tolist();ac['max']=arr.max(axis=0).astype(float).tolist()
 ai=len(accessors);accessors.append(ac);return ai
newmeshes=[]
for mat,data in sorted(mat_prims.items()):
 p=np.concatenate(data['positions']);n=np.concatenate(data['normals']);j=np.concatenate(data['joints']);w=np.concatenate(data['weights']);idx=np.concatenate(data['indices'])
 assert np.allclose(w.sum(axis=1),1.) and j.max()<len(JOINT_NAMES)
 pp=add_acc(p,5126,'VEC3',34962,True);nn=add_acc(n,5126,'VEC3',34962);jj=add_acc(j,5121,'VEC4',34962);ww=add_acc(w,5126,'VEC4',34962);ii=add_acc(idx,5125,'SCALAR',34963)
 newmeshes.append({'name':f'SkinMaterial_{mat}','primitives':[{'attributes':{'POSITION':pp,'NORMAL':nn,'JOINTS_0':jj,'WEIGHTS_0':ww},'indices':ii,'material':mat,'mode':4}]})
# The skeleton is only 17 joints; keep the original joint local transforms and ancestry.
newnodes=[{'name':'RaftboundScene','children':[]}]
node_for={n:i+1 for i,n in enumerate(JOINT_NAMES)}
for n in JOINT_NAMES:
 original=src['nodes'][name_id[n]];node={'name':n}
 for prop in ('matrix','rotation','translation','scale'):
  if prop in original:node[prop]=original[prop]
 newnodes.append(node)
# Parent bone transforms only, not part-mesh transforms.
for n in JOINT_NAMES:
 current=name_id[n];par=parent.get(current)
 while par is not None and src['nodes'][par].get('name') not in node_for:par=parent.get(par)
 if par is None:newnodes[0]['children'].append(node_for[n])
 else:newnodes[node_for[src['nodes'][par]['name']]].setdefault('children',[]).append(node_for[n])
# Put a root scene bone in identity-space: original RB_Root already has its .57 scale.
ib=np.stack([np.linalg.inv(rest[n]).T.reshape(-1) for n in JOINT_NAMES]).astype('<f4')
ibacc=add_acc(ib,5126,'MAT4')
mesh_id=len(newnodes)
for i,m in enumerate(newmeshes):
 newnodes.append({'name':m['name'],'mesh':i,'skin':0})
 newnodes[0]['children'].append(mesh_id+i)
new={'asset':{'version':'2.0','generator':'RAFTBOUND A06 smooth skin converter'},'scene':0,'scenes':[{'nodes':[0]}],
 'nodes':newnodes,'meshes':newmeshes,'skins':[{'name':'SurvivorWeightedRig','joints':[node_for[n] for n in JOINT_NAMES],'inverseBindMatrices':ibacc,'skeleton':node_for['RB_Root']}],
 'materials':src['materials'],'bufferViews':views,'accessors':accessors,'buffers':[{'byteLength':len(outbin)}]}
jbytes=json.dumps(new,separators=(',',':'),ensure_ascii=False).encode();jbytes+=b' ' *((-len(jbytes))%4)
while len(outbin)%4:outbin.append(0)
total=12+8+len(jbytes)+8+len(outbin)
DEST.write_bytes(struct.pack('<III',0x46546c67,2,total)+struct.pack('<II',len(jbytes),0x4e4f534a)+jbytes+struct.pack('<II',len(outbin),0x004e4942)+bytes(outbin))
report={'file':DEST.name,'bytes':DEST.stat().st_size,'joints':len(JOINT_NAMES),'material_primitives':len(newmeshes),'triangles':sum(len(np.concatenate(p['indices']))//3 for p in mat_prims.values()),'vertices':sum(p['count'] for p in mat_prims.values()),'weighted_vertices':sum(int(np.sum(np.count_nonzero(np.concatenate(p['weights'])>.001,axis=1)>1)) for p in mat_prims.values())}
(BASE/'skin_manifest_A06.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
