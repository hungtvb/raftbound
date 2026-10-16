/* RAFTBOUND GLB2 loader: static + weighted-skin primitives (JOINTS_0/WEIGHTS_0).
   Supports accessors, hierarchical nodes, glTF inverse bind matrices and PBR factors.
   Explicitly rejects unsupported required extensions/sparse accessors. */
(function (root) {
 'use strict';
 const MAT_ID=()=>[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
 function matMul(a,b){const c=new Array(16);for(let j=0;j<4;j++)for(let i=0;i<4;i++)c[j*4+i]=a[i]*b[j*4]+a[i+4]*b[j*4+1]+a[i+8]*b[j*4+2]+a[i+12]*b[j*4+3];return c;}
 function trs(n){
  if(n.matrix)return n.matrix;
  const [x,y,z,w]=n.rotation||[0,0,0,1], [sx,sy,sz]=n.scale||[1,1,1], [tx,ty,tz]=n.translation||[0,0,0];
  return [(1-2*(y*y+z*z))*sx,2*(x*y+z*w)*sx,2*(x*z-y*w)*sx,0,
   2*(x*y-z*w)*sy,(1-2*(x*x+z*z))*sy,2*(y*z+x*w)*sy,0,
   2*(x*z+y*w)*sz,2*(y*z-x*w)*sz,(1-2*(x*x+y*y))*sz,0,tx,ty,tz,1];
 }
 const components={5120:{size:1,read:'getInt8'},5121:{size:1,read:'getUint8'},5122:{size:2,read:'getInt16'},5123:{size:2,read:'getUint16'},5125:{size:4,read:'getUint32'},5126:{size:4,read:'getFloat32'}};
 const dims={SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT4:16};
 function decodeGLB(arrayBuffer){
  const view=new DataView(arrayBuffer);
  if(arrayBuffer.byteLength<20||view.getUint32(0,true)!==0x46546c67||view.getUint32(4,true)!==2||view.getUint32(8,true)!==arrayBuffer.byteLength)throw Error('Not a GLB 2.0 file');
  let off=12,json,bin,binSize=0;
  while(off<arrayBuffer.byteLength){
   const len=view.getUint32(off,true),tag=view.getUint32(off+4,true);off+=8;
   if(off+len>arrayBuffer.byteLength)throw Error('GLB chunk exceeds file size');
   if(tag===0x4e4f534a)json=JSON.parse(new TextDecoder().decode(new Uint8Array(arrayBuffer,off,len)));
   if(tag===0x004e4942){bin=off;binSize=len;}off+=len;
  }
  if(!json||bin===undefined)throw Error('GLB lacks JSON or BIN chunk');
  if(json.extensionsRequired?.length)throw Error('Unsupported required glTF extensions: '+json.extensionsRequired.join(','));
  function accessor(id){
   const a=json.accessors?.[id];if(!a||a.sparse||a.bufferView===undefined)throw Error('Sparse or invalid glTF accessor');
   const bv=json.bufferViews[a.bufferView],c=components[a.componentType],d=dims[a.type];
   if(!bv||!c||!d)throw Error('Unsupported glTF accessor');
   const size=c.size*d,stride=bv.byteStride||size,start=(bv.byteOffset||0)+(a.byteOffset||0);
   if(stride<size||start+stride*(a.count-1)+size>binSize||a.count<=0)throw Error('Accessor exceeds BIN bounds');
   const result=new Array(a.count*d);
   for(let i=0;i<a.count;i++)for(let k=0;k<d;k++){
    const v=view[c.read](bin+start+i*stride+k*c.size,true);
    result[i*d+k]=a.normalized&&a.componentType!==5126?(a.componentType===5121?v/255:a.componentType===5123?v/65535:v):v;
   }
   return result;
  }
  function normals(positions,indices){const out=new Array(positions.length).fill(0);
   for(let i=0;i<indices.length;i+=3){const a=indices[i]*3,b=indices[i+1]*3,c=indices[i+2]*3;
    const ux=positions[b]-positions[a],uy=positions[b+1]-positions[a+1],uz=positions[b+2]-positions[a+2];
    const vx=positions[c]-positions[a],vy=positions[c+1]-positions[a+1],vz=positions[c+2]-positions[a+2];
    const n=[uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx];for(const t of [a,b,c])for(let k=0;k<3;k++)out[t+k]+=n[k];
   }for(let i=0;i<out.length;i+=3){const l=Math.hypot(...out.slice(i,i+3))||1;for(let k=0;k<3;k++)out[i+k]/=l;}return out;
  }
  const parents=new Map();for(let i=0;i<(json.nodes||[]).length;i++)for(const child of json.nodes[i].children||[])parents.set(child,i);
  function pathTo(i){let list=[],seen=new Set();while(i!==undefined){if(seen.has(i))throw Error('Cycle in glTF nodes');seen.add(i);const n=json.nodes[i];list.unshift({name:n.name||`node_${i}`,transform:trs(n)});i=parents.get(i);}return list;}
  function skinData(i){const skin=json.skins?.[i];if(!skin)throw Error('Invalid glTF skin');
   if(skin.joints.length>32)throw Error('Skin exceeds maximum of 32 joints');
   const bind=accessor(skin.inverseBindMatrices);
   if(bind.length!==skin.joints.length*16)throw Error('Invalid inverseBindMatrices');
   return {joints:skin.joints.map((index,k)=>({name:json.nodes[index].name||`joint_${k}`,path:pathTo(index),inverseBind:bind.slice(k*16,k*16+16)}))};
  }
  const results=[];
  function visit(id,parent,depth,path){
   if(depth>40)throw Error('glTF scene graph is too deep');const node=json.nodes[id];if(!node)throw Error('Invalid glTF node');
   const local=trs(node),m=matMul(parent,local),ownPath=[...path,{name:node.name||`node_${id}`,transform:local}];
   if(node.mesh!==undefined)for(const p of json.meshes[node.mesh].primitives){
    if(p.mode!==undefined&&p.mode!==4)throw Error('Only TRIANGLES supported');
    const positions=accessor(p.attributes.POSITION),indices=p.indices===undefined?Array.from({length:positions.length/3},(_,i)=>i):accessor(p.indices);
    const nn=p.attributes.NORMAL===undefined?normals(positions,indices):accessor(p.attributes.NORMAL);
    const colors=p.attributes.COLOR_0===undefined?null:accessor(p.attributes.COLOR_0);
    if(colors&&colors.length!==positions.length)throw Error('Invalid COLOR_0 attribute (requires VEC3)');
    const skinned=node.skin!==undefined;
    const joints=skinned?accessor(p.attributes.JOINTS_0):null,weights=skinned?accessor(p.attributes.WEIGHTS_0):null;
    if(skinned&&(!joints||!weights||joints.length!==positions.length/3*4||weights.length!==joints.length))throw Error('Invalid weighted skin vertices');
    const material=json.materials?.[p.material||0];const factors=material?.pbrMetallicRoughness||{};
    results.push({positions,normals:nn,indices,joints,weights,colors,skin:skinned?skinData(node.skin):null,
     transform:m,path:ownPath,materialName:material?.name||'',color:(factors.baseColorFactor||[1,1,1,1]).slice(0,3),
     metallic:factors.metallicFactor??0,roughness:factors.roughnessFactor??1});
   }
   for(const child of node.children||[])visit(child,m,depth+1,ownPath);
  }
  const scene=json.scenes?.[json.scene??0];if(!scene)throw Error('GLB has no scene');
  for(const id of scene.nodes)visit(id,MAT_ID(),0,[]);
  return results;
 }
 async function fetchAsset(url,createMesh){
  const response=await fetch(url);if(!response.ok)throw Error(url+': HTTP '+response.status);
  return decodeGLB(await response.arrayBuffer()).map(p=>({...p,mesh:createMesh(p.positions,p.normals,p.indices,p.joints,p.weights,p.colors)}));
 }
 function skinPalette(part,overrides={}){
  if(!part.skin)return null;
  return part.skin.joints.flatMap(j=>{
   let m=MAT_ID();for(const n of j.path)m=matMul(m,matMul(n.transform,overrides[n.name]||MAT_ID()));
   return matMul(m,j.inverseBind);
  });
 }
 function posedTransform(part,overrides={}){
  if(!part.path)return part.transform;
  let m=MAT_ID();for(const n of part.path)m=matMul(m,matMul(n.transform,overrides[n.name]||MAT_ID()));return m;
 }
 function findJointTransform(part,name,overrides={}){
  const joint=part.skin?.joints.find(j=>j.name===name);
  const path=joint?.path||part.path;if(!path)return null;
  let m=MAT_ID();for(const n of path){m=matMul(m,matMul(n.transform,overrides[n.name]||MAT_ID()));if(n.name===name)return m;}return null;
 }
 root.RaftGLB={decodeGLB,fetchAsset,matMul,skinPalette,posedTransform,findJointTransform};
})(typeof window==='undefined'?globalThis:window);
