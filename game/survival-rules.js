/* RAFTBOUND A08: pure gameplay rules shared by the browser and deterministic tests. */
(function(root){
 'use strict';
 const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
 const finite=(v)=>typeof v==='number'&&Number.isFinite(v);
 const MAX_TILES=400;
 const ITEMS=['wood','plastic','leaf','metal','seed','fish','meal','fresh'];
 const BUILDINGS=['purifier','grill','planter','storage'];
 const posKey=([x,z])=>x+','+z;
 function connectedTiles(tiles){
  if(!Array.isArray(tiles)||!tiles.length||tiles.length>MAX_TILES)return false;
  const present=new Set();
  for(const t of tiles){if(!Array.isArray(t)||t.length!==2||!t.every(v=>Number.isInteger(v)&&Math.abs(v)<=200))return false;const k=posKey(t);if(present.has(k))return false;present.add(k);}
  const seen=new Set([posKey(tiles[0])]),queue=[tiles[0]];
  for(let i=0;i<queue.length;i++)for(const [dx,dz] of [[1,0],[-1,0],[0,1],[0,-1]]){
   const k=posKey([queue[i][0]+dx,queue[i][1]+dz]);if(present.has(k)&&!seen.has(k)){seen.add(k);queue.push(k.split(',').map(Number));}
  }
  return seen.size===tiles.length;
 }
 function onRaft(x,z,tiles,tileSize=2){return tiles.some(([tx,tz])=>Math.abs(x-(tx+.5)*tileSize)<tileSize*.51&&Math.abs(z-(tz+.5)*tileSize)<tileSize*.51);}
 function expandRaft(tiles,yaw){
  if(!connectedTiles(tiles)||tiles.length>=MAX_TILES||!finite(yaw))return null;
  const occupied=new Set(tiles.map(posKey));
  const dirs=[[0,-1],[1,0],[-1,0],[0,1]],forward=[-Math.sin(yaw),-Math.cos(yaw)];
  const options=[];const added=new Set();
  for(const [x,z] of tiles)for(const [dx,dz] of dirs){const t=[x+dx,z+dz],key=posKey(t);if(Math.abs(t[0])>200||Math.abs(t[1])>200||occupied.has(key)||added.has(key))continue;
   added.add(key);options.push({tile:t,alignment:dx*forward[0]+dz*forward[1],dist:Math.abs(t[0])+Math.abs(t[1])});}
  options.sort((a,b)=>b.alignment-a.alignment||a.dist-b.dist||a.tile[0]-b.tile[0]||a.tile[1]-b.tile[1]);
  return options[0]?.tile||null;
 }
 function selectDebris(debris,player,yaw,maxDist=11.6){
  if(!finite(player?.x)||!finite(player?.z)||!finite(yaw))return null;
  const forward=[-Math.sin(yaw),-Math.cos(yaw)];let best=null,bestScore=Infinity;
  for(const d of debris){const dx=d.x-player.x,dz=d.z-player.z,dist=Math.hypot(dx,dz);if(dist>maxDist||dist<.4)continue;
   const dot=(dx*forward[0]+dz*forward[1])/dist;
   // Target selection stays inside a 95-degree forward cone.
   if(dot<.675)continue;
   const score=dist*.14+(1-dot)*8;
   if(score<bestScore){best=d;bestScore=score;}}
  return best;
 }
 function castHit(object,from,to,activeDebris,radius=1.05){
  if(!object||!activeDebris.includes(object))return false;
  if(![object.x,object.z,from.x,from.z,to.x,to.z].every(finite))return false;
  const travel=Math.hypot(to.x-from.x,to.z-from.z);
  return travel<=12.2&&Math.hypot(object.x-to.x,object.z-to.z)<=radius;
 }
 function readSave(raw){
  if(!raw||typeof raw!=='object'||raw.version!==1||!raw.game)return null;
  const g=raw.game;
  if(!connectedTiles(g.tiles))return null;
  if(!finite(raw.elapsed)||raw.elapsed<0||raw.elapsed>1e8)return null;
  if(!g.player||!finite(g.player.x)||!finite(g.player.z)||!onRaft(g.player.x,g.player.z,g.tiles))return null;
  const inv={};for(const key of ITEMS){const n=g.inv?.[key];if(!Number.isSafeInteger(n)||n<0||n>1e6)return null;inv[key]=n;}
  const buildings=[];const slots=new Set();
  if(!Array.isArray(g.buildings)||g.buildings.length>g.tiles.length)return null;
  const tileKeys=new Set(g.tiles.map(posKey));
  for(const b of g.buildings){const key=b?.x+','+b?.z;if(!BUILDINGS.includes(b?.id)||!Number.isInteger(b.x)||!Number.isInteger(b.z)||!tileKeys.has(key)||slots.has(key))return null;slots.add(key);buildings.push({id:b.id,x:b.x,z:b.z});}
  for(const k of ['hp','food','water'])if(!finite(g[k])||g[k]<0||g[k]>100)return null;
  for(const k of ['collected','crafts','sharkHits'])if(!Number.isSafeInteger(g[k])||g[k]<0||g[k]>1e8)return null;
  const seconds=finite(g.seconds)&&g.seconds>=0?g.seconds:raw.elapsed;
  const timers={};for(const k of ['waterTimer','cookTimer','growTimer'])timers[k]=finite(g[k])&&g[k]>=0&&g[k]<1e5?g[k]:0;
  const quest=Number.isInteger(g.quest)?clamp(g.quest,0,6):0;
  return {game:{hp:g.hp,food:g.food,water:g.water,day:1+Math.floor(raw.elapsed/200),seconds,
   player:{x:g.player.x,z:g.player.z},inv,tiles:g.tiles.map(t=>[...t]),buildings,
   collected:g.collected,quest,crafts:g.crafts,hasSpear:g.hasSpear===true,sharkHits:g.sharkHits,...timers},elapsed:raw.elapsed};
 }
 const api={connectedTiles,onRaft,expandRaft,selectDebris,castHit,readSave,MAX_TILES};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 root.RaftRules=api;
})(typeof window==='undefined'?globalThis:window);
