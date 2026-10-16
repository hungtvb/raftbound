const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..');
const context={TextDecoder,DataView,ArrayBuffer,Uint8Array,console};vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root,'glb-loader.js'),'utf8'),context);
const bytes=fs.readFileSync(path.join(root,'assets/glb/survivor_sailor_skinned.glb'));
const asset=context.RaftGLB.decodeGLB(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength));
const {skinPalette,findJointTransform}=context.RaftGLB;
assert.equal(asset.length,16,'expected 16 packed material primitives');
let vertices=0,weighted=0;
for(const part of asset){
 assert(part.skin,'weighted GLB part missing skin');assert.equal(part.skin.joints.length,17);
 assert.equal(part.joints.length,part.positions.length/3*4);
 assert.equal(part.weights.length,part.joints.length);
 vertices+=part.positions.length/3;
 for(let i=0;i<part.weights.length;i+=4){
  const w=part.weights.slice(i,i+4);
  assert(Math.abs(w.reduce((a,b)=>a+b,0)-1)<1e-5);
  for(let j=0;j<4;j++)assert(part.joints[i+j]>=0&&part.joints[i+j]<17);
  if(w[1]>.001)weighted++;
 }
 const rest=skinPalette(part,{});
 for(let b=0;b<17;b++){
  const a=rest.slice(b*16,b*16+16);
  const ident=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
  for(let i=0;i<16;i++)assert(Math.abs(a[i]-ident[i])<1e-5,'Rest skin is not identity at bone '+b+' entry '+i+': '+a[i]);
 }
}
assert(weighted>1000,'No smooth weighted vertices');
const part=asset.find(p=>p.joints.includes(16));
const xrot=a=>[1,0,0,0,0,Math.cos(a),Math.sin(a),0,0,-Math.sin(a),Math.cos(a),0,0,0,0,1];
const wristA=findJointTransform(part,'R_Wrist',{}),wristB=findJointTransform(part,'R_Wrist',{R_Shoulder:xrot(1.3)});
assert(Math.hypot(wristA[12]-wristB[12],wristA[13]-wristB[13],wristA[14]-wristB[14])>.2);
let change=0;for(const p of asset){
 const neutral=skinPalette(p,{}),moved=skinPalette(p,{R_Shoulder:xrot(1.3)});
 for(let i=0;i<p.joints.length;i+=4){
  const bone=p.joints[i],w=p.weights[i],v=i/4*3;
  if(bone!==14||w<.8)continue;
  const mat=(a)=>{const m=a.slice(bone*16,bone*16+16),x=p.positions[v],y=p.positions[v+1],z=p.positions[v+2];return [m[0]*x+m[4]*y+m[8]*z+m[12],m[1]*x+m[5]*y+m[9]*z+m[13],m[2]*x+m[6]*y+m[10]*z+m[14]]};
  const a=mat(neutral),b=mat(moved);change=Math.max(change,Math.hypot(...a.map((x,k)=>x-b[k])));
 }
}
assert(change>.05,'GPU skin vertex transform is not affected by joint pose');
console.log(`PASS A04 weighted rig: ${vertices} vertices, ${weighted} blended, 17 bones, pose displacement ${change.toFixed(3)} m`);
