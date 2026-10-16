const assert=require('node:assert/strict');
const rules=require('../survival-rules.js');
const initial=[[-1,-1],[-1,0],[0,-1],[0,0]];
assert(rules.connectedTiles(initial));
for(const tiles of [[[-1,0],[-1,0]],[[0,0],[2,0]],[[0.4,0]],[[201,0]]])assert(!rules.connectedTiles(tiles));
for(const yaw of [-Math.PI,-Math.PI/2,0,Math.PI/2]){
 const tiles=initial.map(t=>[...t]);
 for(let i=0;i<95;i++){
  const placed=rules.expandRaft(tiles,yaw);assert(placed,'no valid expansion at '+i);
  tiles.push(placed);
  assert(rules.connectedTiles(tiles),'raft disconnected after expansion '+i);
  assert.equal(new Set(tiles.map(t=>t.join(','))).size,tiles.length);
 }
}
const debris=[{type:'wood',x:0,z:-8},{type:'plastic',x:7,z:-8},{type:'fish',x:0,z:4}];
assert.equal(rules.selectDebris(debris,{x:0,z:0},0),debris[0]);
assert.equal(rules.selectDebris(debris,{x:0,z:0},Math.PI),debris[2]);
assert.equal(rules.selectDebris(debris,{x:0,z:0},0,3),null);
const target={type:'wood',x:0,z:-8};
assert(rules.castHit(target,{x:0,z:0},{x:0,z:-8},[target]));
assert(!rules.castHit({...target},{x:0,z:0},{x:0,z:-8},[target]));
target.x=2.4;assert(!rules.castHit(target,{x:0,z:0},{x:0,z:-8},[target]));
target.x=0;assert(!rules.castHit(target,{x:0,z:0},{x:0,z:-13},[target]));
const saved={version:1,elapsed:210,game:{tiles:initial,player:{x:0,z:0},inv:{wood:8,plastic:2,leaf:0,metal:1,seed:0,fish:0,meal:2,fresh:1},buildings:[{id:'grill',x:0,z:0}],hp:94,food:54,water:52,collected:8,crafts:2,sharkHits:0,quest:2,hasSpear:false,seconds:210,waterTimer:2,cookTimer:3,growTimer:0}};
const parsed=rules.readSave(saved);assert(parsed);assert.equal(parsed.game.day,2);assert.equal(parsed.game.buildings.length,1);
function corrupt(mutator){const bad=JSON.parse(JSON.stringify(saved));mutator(bad);assert.equal(rules.readSave(bad),null);}
corrupt(g=>g.game.inv.wood=-5);corrupt(g=>g.game.inv.wood='100000');corrupt(g=>g.game.tiles.push([0,0]));
corrupt(g=>g.game.tiles.push([5,5]));corrupt(g=>g.game.player.x=1234);
corrupt(g=>g.game.buildings.push({id:'grill',x:0,z:0}));
corrupt(g=>g.game.buildings[0].id='hacked');corrupt(g=>g.version=900);corrupt(g=>g.elapsed=-2);
assert.equal(rules.readSave(null),null);
console.log('PASS A08: 380 connected expansions, directional targeting, contact-based catch, corrupted-save rejection');
