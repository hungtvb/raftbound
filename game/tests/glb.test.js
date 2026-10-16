const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..');
const ctx={TextDecoder,DataView,ArrayBuffer,Uint8Array,console};vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(root,'glb-loader.js'),'utf8'),ctx);
const names=['foundation_2m','salvage_net_tool','driftwood_plank','plastic_bottle','palm_leaf','compact_grill','solar_purifier','planter_box','storage_chest','salvage_barrel','survivor_sailor_rig'];
let triangles=0;
for(const name of names){
 const buff=fs.readFileSync(path.join(root,'assets/glb',name+'.glb'));
 const array=buff.buffer.slice(buff.byteOffset,buff.byteOffset+buff.byteLength);
 const parts=ctx.RaftGLB.decodeGLB(array);
 assert(parts.length>0,`empty ${name}`);
 for(const p of parts){
  assert.equal(p.positions.length,p.normals.length,name);
  assert(p.indices.every(i=>i*3<p.positions.length),name+' invalid index');
  assert(p.color.every(c=>c>=0&&c<=1),name+' invalid material');
  assert(p.transform.length===16,name+' invalid transform');
  triangles+=p.indices.length/3;
 }
 console.log('PASS GLB parsed:',name,'parts=',parts.length);
}
assert(triangles>10000,`missing detail triangles: ${triangles}`);
console.log('PASS GLB importer: 11 assets',triangles,'triangles');
