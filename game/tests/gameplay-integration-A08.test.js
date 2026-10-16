const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');const rules=require('../survival-rules.js');
const nodes={};let frames=[],lastNow=100;
class Element{constructor(){this.handlers={};this.style={};this.width=960;this.height=600;this.innerHTML='';this.textContent='';this.dataset={};this.disabled=false;this.classList={_set:new Set(),add(k){this._set.add(k)},remove(k){this._set.delete(k)},toggle(k,on){on===undefined?on=!this._set.has(k):on;on?this.add(k):this.remove(k)},contains(k){return this._set.has(k)}}}
 addEventListener(t,fn){(this.handlers[t]??=[]).push(fn)}trigger(t,e={}){for(const fn of this.handlers[t]||[])fn(e)}getContext(){return gl}setPointerCapture(){}
}
const gl=new Proxy({getShaderParameter:()=>true,getProgramParameter:()=>true,getShaderInfoLog:()=>'',getProgramInfoLog:()=>'',createProgram:()=>({}),createShader:()=>({}),createBuffer:()=>({}),createVertexArray:()=>({}),getUniformLocation:()=>({})},{get(o,k){if(k in o)return o[k];return ()=>{}}});
const doc={querySelector:q=>(nodes[q]??=new Element()),querySelectorAll:q=>[]};const win=new Element();win.devicePixelRatio=1;
const store={};const ctx={document:doc,window:win,innerWidth:960,innerHeight:600,performance:{now:()=>lastNow},requestAnimationFrame:fn=>frames.push(fn),localStorage:{getItem:k=>store[k]??null,setItem:(k,v)=>store[k]=v},console,JSON,Math,Float32Array,Uint32Array,parseInt,confirm:()=>true};
win.RaftRules=rules;win.RaftCastMotion=require('../cast-motion.js');
vm.createContext(ctx);
const original=fs.readFileSync(path.join(root,'game.js'),'utf8');
// QA-only injection; production source remains free of test APIs.
const exposed=original.replace(/\}\)\(\);\s*$/,`window.__QA={getGame:()=>game,getDebris:()=>debris,setDebris:v=>debris=v,cast,simulate,save,load,craft,getNet:()=>netFx,setYaw:v=>cameraYaw=v};})();`);
assert.notEqual(exposed,original,'QA instrumentation could not be inserted');vm.runInContext(exposed,ctx);
const tick=(time)=>{lastNow=time;assert(frames.length);frames.shift()(time)};
for(let i=0;i<4;i++)tick(120+i*16);
nodes['#startBtn'].trigger('click');
const qa=win.__QA;assert(qa.getGame().tiles.length===4);
// E2E cast: render-facing cast and contact must use the same target.
qa.setYaw(0);const target={type:'wood',x:0,z:-7,speed:0,sway:0,phase:0,rot:0};qa.setDebris([target]);
const old=qa.getGame().inv.wood;qa.cast();qa.simulate(.7);
assert.equal(qa.getGame().inv.wood,old+1,'hit was not collected');assert.equal(qa.getDebris().length,0);
qa.simulate(1);
// Moving an item outside the net contact radius must not reward it.
const miss={type:'wood',x:0,z:-7,speed:0,sway:0,phase:0,rot:0};qa.setDebris([miss]);qa.cast();miss.x=7;
qa.simulate(.7);assert.equal(qa.getGame().inv.wood,old+1,'invalid hit was rewarded');assert(qa.getDebris().includes(miss),'missed target was incorrectly removed');
qa.simulate(1);
// Raft expansion uses resource accounting and an actual adjacent tile.
qa.getGame().inv.wood=20;qa.getGame().inv.plastic=10;
qa.craft('raft');assert(qa.getGame().tiles.length===5);assert.equal(qa.getGame().inv.wood,16);assert(rules.connectedTiles(qa.getGame().tiles));
qa.save();const before=JSON.parse(store['raftbound.save.v1']);assert.equal(before.game.tiles.length,5);
qa.getGame().inv.wood=0;assert(qa.load());assert.equal(qa.getGame().inv.wood,16);
store['raftbound.save.v1']='{"version":1,"game":{"tiles":[[999,999]]}}';assert.equal(qa.load(),false,'corrupt save unexpectedly accepted');
// Diagnostic render scaling is user-selectable and exposes the value in F3.
win.trigger('keydown',{key:'F3',repeat:false,preventDefault(){}});
win.trigger('keydown',{key:'F4',repeat:false,preventDefault(){}});
tick(9000);assert(nodes['#perfOverlay'].textContent.includes('Render 70%'));
console.log('PASS A08: real game-loop catch+miss, build resources, save+restore, corrupt rejection, render-scale HUD');
