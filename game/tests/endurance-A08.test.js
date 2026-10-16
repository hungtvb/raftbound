const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),nodes={},raf=[];
class Element{constructor(){this.handlers={};this.classList={s:new Set(),add(k){this.s.add(k)},remove(k){this.s.delete(k)},contains(k){return this.s.has(k)},toggle(k,v){if(v===undefined)v=!this.s.has(k);v?this.add(k):this.remove(k)}};this.style={};this.dataset={};this.width=800;this.height=600;this.innerHTML='';this.textContent='';this.disabled=false;}addEventListener(k,cb){(this.handlers[k]??=[]).push(cb)}getContext(){return gl}setPointerCapture(){}trigger(k){for(const f of this.handlers[k]||[])f({})}}
const gl=new Proxy({getShaderParameter:()=>true,getProgramParameter:()=>true,createShader:()=>({}),createProgram:()=>({}),createVertexArray:()=>({}),createBuffer:()=>({}),getUniformLocation:()=>({})},{get(o,k){return k in o?o[k]:()=>{}}});
const doc={querySelector:q=>(nodes[q]??=new Element()),querySelectorAll:()=>[]};const win=new Element();win.devicePixelRatio=1;
const store={};const ctx={document:doc,window:win,innerWidth:800,innerHeight:600,performance:{now:()=>100},requestAnimationFrame:cb=>raf.push(cb),localStorage:{getItem:k=>store[k]??null,setItem:(k,v)=>store[k]=v},JSON,Math,Float32Array,Uint32Array,console,parseInt,confirm:()=>true};
vm.createContext(ctx);win.RaftCastMotion=require('../cast-motion.js');win.RaftRules=require('../survival-rules.js');
let script=fs.readFileSync(path.join(root,'game.js'),'utf8');
script=script.replace(/\}\)\(\);\s*$/,`window.__QA={getGame:()=>game,craft,simulate,save,consume};})();`);
vm.runInContext(script,ctx);nodes['#startBtn'].trigger('click');
const qa=win.__QA,game=qa.getGame();
for(const item of ['wood','plastic','leaf','metal','seed','fish'])game.inv[item]=80;
for(let i=0;i<8;i++)qa.craft('raft');
for(const id of ['purifier','grill','planter','storage','spear'])qa.craft(id);
assert.equal(game.tiles.length,12);assert.equal(game.buildings.length,4);assert(game.hasSpear);
const freshBefore=game.inv.fresh,mealBefore=game.inv.meal;
const start=Date.now();
for(let s=0;s<1200;s++){
 qa.simulate(1);
 // Collect resource production from buildings before the survival needs deplete.
 if(s%80===0){if(game.inv.fresh>0)qa.consume('drink');if(game.inv.meal>0)qa.consume('eat')}
 assert(Number.isFinite(game.hp)&&Number.isFinite(game.food)&&Number.isFinite(game.water));
 assert(game.hp>=0&&game.hp<=100&&game.food>=0&&game.food<=100&&game.water>=0&&game.water<=100);
}
assert(game.day>=7);assert(game.sharkHits>=20);assert(game.crafts>=13);
assert(game.inv.fresh>freshBefore,'purifier did not produce drinking water');
assert(game.inv.meal>mealBefore,'grill or planter did not produce food');
qa.save();assert(win.RaftRules.readSave(JSON.parse(store['raftbound.save.v1'])));
console.log(`PASS A08: 1200s simulation, 8 raft expansions, 5 crafting recipes, cooking, filtration, crops, sharks, save (${Date.now()-start}ms)`);
