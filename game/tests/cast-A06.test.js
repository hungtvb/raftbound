const assert=require('assert'),fs=require('fs'),path=require('path');
const {CAST,state,flight}=require('../cast-motion.js');
const game=fs.readFileSync(path.resolve(__dirname,'../game.js'),'utf8');
assert(state(0).visibleInHand);
assert(state(CAST.release-.001).visibleInHand);
assert(!state(CAST.release).visibleInHand);
assert(state(CAST.contact).progress===1);
assert(state(CAST.end).phase==='done');
for(let t=0;t<CAST.end;t+=.005){const s=state(t),f=flight(t,{x:1,z:1},{x:10,z:-8});assert(Number.isFinite(f.x)&&Number.isFinite(f.y)&&Number.isFinite(f.z));assert(f.progress>=0&&f.progress<=1);assert(Math.abs(s.progress-f.progress)<1e-9);}
assert(game.includes('netFx.time>=window.RaftCastMotion.CAST.contact'));
assert(game.includes('netFx.time>=window.RaftCastMotion.CAST.end'));
assert(game.includes('window.RaftCastMotion.state(netFx.time).visibleInHand'));
assert(game.includes('window.RaftCastMotion.flight(netFx.time,netFx.from,netFx.to)'));
assert(game.includes("if(k==='v')cycleCamera()"));
assert(game.includes("canvas.addEventListener('wheel'"));
assert(game.includes("if(k==='p')"));
console.log('PASS A06 cast release/contact/return, shared rig-fx timeline, camera and screenshot integration');
