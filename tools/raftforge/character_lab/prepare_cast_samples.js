/* Capture the REAL RAFTBOUND net-cast timeline as reproducible Blender inputs.
 * No hand-copied curves: this imports game/cast-motion.js on every CI run.
 */
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const cast=require(path.resolve(__dirname,'../../../game/cast-motion.js'));
const fps=24;
const end=cast.CAST.end;
const samples=Array.from({length:Math.ceil(end*fps)+1},(_,i)=>{
 const time=Math.min(i/fps,end);
 const s=cast.state(time);
 return {time,throwArm:s.throwArm,throwElbow:s.throwElbow,
         spineLean:s.spineLean,phase:s.phase};
});
const out=process.argv[2];
if(!out)throw Error('Usage: node prepare_cast_samples.js OUTPUT.json');
for(const p of samples){
 for(const key of ['throwArm','throwElbow','spineLean'])
  if(!Number.isFinite(p[key]))throw Error('Non-finite cast state '+key);
}
fs.mkdirSync(path.dirname(path.resolve(out)),{recursive:true});
fs.writeFileSync(out,JSON.stringify({source:'game/cast-motion.js',fps,end,samples},null,2));
console.log('Source-linked gameplay cast timeline:',samples.length,'samples,',end,'seconds');
