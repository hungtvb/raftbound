/* Chromium acceptance test: exercise THREE.AnimationMixer with the real 65-bone
 * imported GLB, capture idle/walk/cast evidence, verify meaningful bone motion.
 */
import {chromium} from 'playwright-core';
import fs from 'node:fs';
import path from 'node:path';
const output=path.resolve(process.argv[2]||'qa-character-a14/three-review');
fs.mkdirSync(output,{recursive:true});
const executablePath=process.env.CHROME_PATH||
  ['/usr/bin/google-chrome','/usr/bin/chromium','/opt/google/chrome/chrome'].find(x=>fs.existsSync(x));
if(!executablePath)throw Error('No system Chromium/Chrome found. Set CHROME_PATH.');
const browser=await chromium.launch({headless:true,executablePath,
  args:['--no-sandbox','--disable-dev-shm-usage','--enable-webgl',
    '--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader',
    '--disable-gpu-sandbox']});
try{
  const page=await browser.newPage({viewport:{width:1250,height:850},
                                    deviceScaleFactor:1});
  const failures=[];
  page.on('pageerror',e=>failures.push(e.message));
  page.on('console',m=>{if(m.type()==='error')failures.push(m.text());});
  const addr='http://127.0.0.1:4173/tools/raftforge/character_lab/three_review/index.html';
  await page.goto(addr+'?asset=/qa-character-a14/sailor-animated.glb',{waitUntil:'networkidle',timeout:45000});
  await page.waitForFunction(()=>window.__raftReview?.ready===true||window.__raftReview?.error,
    null,{timeout:45000});
  const meta=await page.evaluate(()=>({
    ready:window.__raftReview.ready,error:window.__raftReview.error,
    clips:window.__raftReview.clips,bones:window.__raftReview.bones,
    skinnedMeshes:window.__raftReview.skinnedMeshes,
    triangles:window.__raftReview.triangles
  }));
  if(!meta.ready||meta.error)throw Error('GLTF load failed '+JSON.stringify(meta));
  if(meta.bones<60||meta.skinnedMeshes<4||meta.clips.length!==3)
    throw Error('Rig/animation contract mismatch: '+JSON.stringify(meta));
  const states=[];
  for(const [mode,time] of [['idle',0.6],['walk',.28],['cast',.33]]){
    const data=await page.evaluate(({mode,time})=>{
      const obj=window.__raftReview;
      obj.pause();obj.setMotion(mode,time);
      return {name:mode,time,signature:obj.poseSignature(),armDrops:obj.armDrops()};
    },{mode,time});
    await page.screenshot({path:path.join(output,mode+'.png'),animations:'disabled'});
    if(fs.statSync(path.join(output,mode+'.png')).size<25000)
      throw Error('Viewport screenshot suspiciously empty for '+mode);
    states.push(data);
  }
  const distance=(a,b)=>{
    let diffs=0;
    const x=a.signature.filter(v=>typeof v==='number');
    const y=b.signature.filter(v=>typeof v==='number');
    for(let i=0;i<Math.min(x.length,y.length);i++)diffs+=Math.abs(x[i]-y[i]);
    return diffs;
  };
  const idleDrop=states[0].armDrops;
  if(!('l' in idleDrop && 'r' in idleDrop)||
    idleDrop.l<0.15||idleDrop.r<0.15)
    throw Error('Idle character retained an unnatural T-pose: '+JSON.stringify(idleDrop));
  const walkDelta=distance(states[0],states[1]),
        castDelta=distance(states[0],states[2]);
  if(walkDelta<.25||castDelta<.25)throw Error(
    'Three.js joints did not animate: '+JSON.stringify({walkDelta,castDelta}));
  if(failures.length)throw Error('Browser errors: '+JSON.stringify(failures));
  const report={status:'THREE_GLTF_PLAYBACK_PASS',url:addr,
    bones:meta.bones,skinnedMeshes:meta.skinnedMeshes,
    triangles:meta.triangles,clips:meta.clips,walkDelta,castDelta,idleDrop,
    screenshots:states.map(s=>s.name+'.png'),
    limitations:[
      'This is a dedicated Three.js rig review, NOT the shipped 17-bone WebGL2 game.',
      'Clips are derived from the game timeline; they are not pre-existing motion capture.',
      'Visual art and actual gameplay inputs still need live acceptance.'
    ]};
  fs.writeFileSync(path.join(output,'three-report.json'),JSON.stringify(report,null,2));
  console.log('THREE ANIMATED RIG ACCEPTANCE PASS',JSON.stringify(report));
} finally {
  await browser.close();
}
