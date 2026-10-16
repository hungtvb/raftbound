// A07 mock-GPU contract: COLOR_0 must reach attribute slot 4 and the shader tint uniform.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
(async()=>{
 const root=path.resolve(__dirname,'..');let frames=[],colorSlots=0,tintOn=0,tintOff=0,drawCalls=0;
 const gl=new Proxy({
  getShaderParameter:()=>true,getProgramParameter:()=>true,getShaderInfoLog:()=>'',getProgramInfoLog:()=>'',
  getUniformLocation:(_p,n)=>n,
  uniform1f:(name,value)=>{if(name==='uHasTint')value===1?tintOn++:tintOff++},
  enableVertexAttribArray:slot=>{if(slot===4)colorSlots++},
  drawElements:()=>drawCalls++,createShader:()=>({}),createProgram:()=>({}),createVertexArray:()=>({}),createBuffer:()=>({})
 },{get:(o,k)=> k in o?o[k]:typeof k==='symbol'?undefined:()=>{}});
 const nodes={};
 class Element{
  constructor(){this.handlers={};this.dataset={};this.width=1000;this.height=650;this.style={};this.innerHTML='';this.textContent='';this.disabled=false;this.classList={s:new Set(),add(k){this.s.add(k)},remove(k){this.s.delete(k)},toggle(k,v){v===undefined?v=!this.s.has(k):v;v?this.add(k):this.remove(k)},contains(k){return this.s.has(k)}}}
  addEventListener(k,v){(this.handlers[k]??=[]).push(v)}
  trigger(k,event={}){for(const f of this.handlers[k]||[])f(event)}
  click(){this.trigger('click')}
  getContext(){return gl}
 }
 const document={querySelector:q=>(nodes[q]??=new Element()),querySelectorAll:()=>[]};
 const window=new Element();window.devicePixelRatio=1;
 const fetch=async url=>{const b=fs.readFileSync(path.join(root,url));return {ok:true,arrayBuffer:async()=>b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)}};
 const context={document,window,fetch,TextDecoder,DataView,ArrayBuffer,Uint8Array,Float32Array,Uint32Array,Math,JSON,console,parseInt,performance:{now:()=>100},requestAnimationFrame:cb=>frames.push(cb),localStorage:{getItem:()=>null,setItem:()=>{}},confirm:()=>true,innerWidth:1000,innerHeight:650};
 vm.createContext(context);
 vm.runInContext(fs.readFileSync(path.join(root,'glb-loader.js'),'utf8'),context);
 window.RaftGLB=context.window.RaftGLB;window.RaftRules=require('../survival-rules.js');window.RaftCastMotion=require('../cast-motion.js');
 vm.runInContext(fs.readFileSync(path.join(root,'game.js'),'utf8'),context);
 for(let i=0;i<100&&!nodes['#assetStatus']?.textContent?.includes('11 / 11');i++)await new Promise(r=>setTimeout(r,5));
 assert(nodes['#assetStatus'].textContent.includes('11 / 11'),nodes['#assetStatus'].textContent);
 assert(colorSlots===2,`COLOR_0 attribute not uploaded for BOTH skin batches: ${colorSlots}`);
 nodes['#startBtn'].click();
 for(let i=0;i<10;i++){const f=frames.shift();assert(f);f(300+i*16)}
 assert(tintOn>=2,`skin batches not tinted by vertex color: ${tintOn}`);
 assert(tintOff>0,'legacy/static rendering lacks correct default white tint');
 assert(drawCalls>100,'scene draw calls missing');
 window.trigger('keydown',{key:'F3',repeat:false,preventDefault:()=>{}});
 const frame=frames.shift();frame(500);
 assert(nodes['#perfOverlay'].textContent.includes('Draw calls'),'F3 metrics HUD absent');
 assert(nodes['#perfOverlay'].textContent.includes('Hero batches: 2'),'incorrect batch metric');
 console.log('PASS A07 GPU-mock vertex tint: attribute 4 uploads',colorSlots,'tinted draws',tintOn,'untinted draws',tintOff,'F3 metrics displayed');
})().catch(e=>{console.error(e);process.exitCode=1});
