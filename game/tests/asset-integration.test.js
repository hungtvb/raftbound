const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
(async()=>{
const root=path.resolve(__dirname,'..');
const nodes={};let draws=0;
const gl=new Proxy({getShaderParameter:()=>true,getProgramParameter:()=>true,getShaderInfoLog:()=>'',getProgramInfoLog:()=>'',getUniformLocation:()=>({}),drawElements:()=>{draws++;}, createShader:()=>({}),createProgram:()=>({}),createVertexArray:()=>({}),createBuffer:()=>({})}, {get(o,k){if(k in o)return o[k];if(typeof k==='symbol')return undefined;return ()=>{}}});
class Element{
 constructor(){this.handlers={};this.style={};this.dataset={};this.width=960;this.height=600;this.classList={set:new Set(),add(k){this.set.add(k)},remove(k){this.set.delete(k)},toggle(k,on){if(on===undefined)on=!this.set.has(k);on?this.add(k):this.remove(k)},contains(k){return this.set.has(k)}};this.innerHTML='';this.textContent='';this.disabled=false;}
 addEventListener(t,f){(this.handlers[t]??=[]).push(f)}
 click(){this.trigger('click')}
 trigger(t,event={}){for(const f of this.handlers[t]||[])f(event)}
 getContext(){return gl}
 setPointerCapture(){}
}
const document={querySelector:q=>(nodes[q]??=new Element()),querySelectorAll:()=>[]};
const window=new Element();window.devicePixelRatio=1;window.innerWidth=960;window.innerHeight=600;
let frames=[];let fetches=0;
const fetch=async url=>{
 fetches++;
 const file=path.join(root,url);
 try{const b=fs.readFileSync(file);return {ok:true,status:200,arrayBuffer:async()=>b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)}}catch{return {ok:false,status:404}}
};
const store={};const ctx={document,window,fetch,TextDecoder,DataView,ArrayBuffer,Uint8Array,performance:{now:()=>100},requestAnimationFrame:f=>frames.push(f),localStorage:{getItem:k=>store[k],setItem:(k,v)=>store[k]=v},console,Math,JSON,parseInt,Float32Array,Uint32Array,innerWidth:960,innerHeight:600,confirm:()=>true};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(root,'glb-loader.js'),'utf8'),ctx);window.RaftGLB=ctx.window.RaftGLB;
ctx.window.RaftRules=require('../survival-rules.js');window.RaftCastMotion=require('../cast-motion.js');vm.runInContext(fs.readFileSync(path.join(root,'game.js'),'utf8'),ctx);
for(let i=0;i<100&&!(nodes['#assetStatus']?.textContent?.includes('11 / 11'));i++)await new Promise(r=>setTimeout(r,5));
assert(nodes['#assetStatus'].textContent.includes('11 / 11'),nodes['#assetStatus'].textContent);
assert.equal(fetches,11);
for(let i=0;i<8;i++){const cb=frames.shift();assert(cb);cb(200+i*16)}
nodes['#startBtn'].click();for(let i=0;i<12;i++){const cb=frames.shift();assert(cb);cb(500+i*16)}
assert(draws>500,'did not render imported meshes');
assert(nodes['#questTitle'].textContent);
assert(nodes['#inventory'].innerHTML.includes('Gỗ'));
nodes['#assetStatus'].click();assert(nodes['#assetStatus'].textContent.includes('Hình học cũ'));
nodes['#assetStatus'].click();assert(nodes['#assetStatus'].textContent.includes('GLB'));
console.log('PASS: 11 real GLB loaded,',draws,'mesh draw calls, HUD, toggling, player loop');
})().catch(e=>{console.error(e);process.exitCode=1});
