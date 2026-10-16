/* A09 actual Chromium WebGL smoke test. No mocked renderer. */
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const root=dirname(dirname(fileURLToPath(import.meta.url)));
const output=join(root,'artifacts');
await mkdir(output,{recursive:true});
const server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173','--strictPort'],{
  cwd:root,stdio:['ignore','pipe','pipe']
});
let outputLog='';for(const stream of [server.stdout,server.stderr])stream.on('data',chunk=>{outputLog+=chunk.toString();});
let browser;
const errors=[];
try {
  let connected=false;
  for(let attempt=0;attempt<60;attempt++){
    try{const response=await fetch('http://127.0.0.1:5173/');if(response.ok){connected=true;break;}}
    catch {/* server still starting */}
    await new Promise(resolve=>setTimeout(resolve,250));
  }
  assert(connected,`Vite did not start: ${outputLog}`);
  browser=await chromium.launch({headless:true,args:[
    '--use-gl=angle','--use-angle=swiftshader','--enable-webgl','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'
  ]});
  const page=await browser.newPage({viewport:{width:1365,height:768},deviceScaleFactor:1});
  page.on('pageerror',err=>errors.push(err.message));
  page.on('console',msg=>{if(msg.type()==='error')errors.push(`console: ${msg.text()}`);});
  await page.goto('http://127.0.0.1:5173/',{waitUntil:'domcontentloaded',timeout:30000});
  await page.waitForFunction(()=>document.querySelector('#assetStatus')?.textContent?.includes('THREE.JS + RAPIER'),null,{timeout:45000});
  const assetStatus=await page.locator('#assetStatus').innerText();
  assert.match(assetStatus,/13\/13 GLB/,`Not all models loaded: ${assetStatus}`);
  await page.screenshot({path:join(output,'a10-main-menu-desktop.png'),animations:'disabled'});
  const webgl=await page.locator('#world').evaluate(canvas=>Boolean(canvas.getContext('webgl2')));
  assert(webgl,'No real WebGL2 context');
  await page.locator('#startBtn').click();
  assert(await page.locator('#startOverlay').evaluate(el=>el.classList.contains('hidden')));
  await page.keyboard.press('F3');
  await page.waitForFunction(()=>{
    const txt=document.querySelector('#perfOverlay')?.textContent??'';
    return Number(txt.match(/Draw calls: (\d+)/)?.[1]??0)>0;
  },null,{timeout:10000});
  await page.keyboard.press('Tab');
  assert(await page.locator('#bagPanel').evaluate(el=>el.classList.contains('open')),'Bag did not open with Tab');
  assert.equal(await page.locator('.bag-item').count(),8,'Bag should have 8 inventory slots');
  await page.screenshot({path:join(output,'a10-backpack-desktop.png'),animations:'disabled'});
  await page.keyboard.press('Escape');
  assert(await page.locator('#bagPanel').evaluate(el=>!el.classList.contains('open')),'ESC must close bag first');
  await page.locator('#craftBtn').click();
  assert.equal(await page.locator('[data-craft]').count(),6,'Crafting recipes unavailable');
  await page.screenshot({path:join(output,'a10-crafting-desktop.png'),animations:'disabled'});
  await page.locator('[data-filter="CÔNG CỤ"]').click();
  assert.equal(await page.locator('[data-craft]').count(),1,'Craft filtering failed');
  await page.locator('[data-filter="TẤT CẢ"]').click();
  assert.equal(await page.locator('[data-craft]').count(),6,'Resetting craft filter failed');
  await page.locator('#closeCraft').click();
  assert(await page.locator('#drawerBackdrop').evaluate(el=>el.classList.contains('hidden')),'Drawer backdrop did not close');
  await page.keyboard.down('KeyW');await page.waitForTimeout(350);await page.keyboard.up('KeyW');
  await page.screenshot({path:join(output,'a10-hud-desktop.png'),animations:'disabled'});
  await page.locator('#pauseBtn').click();
  await page.locator('#pauseTabSettings').click();
  const originalQuality=await page.locator('#qualityBtn').innerText();
  await page.locator('#qualityBtn').click();
  assert.notEqual(await page.locator('#qualityBtn').innerText(),originalQuality,'Settings quality action did not work');
  await page.locator('#pauseTabControls').click();
  assert(await page.locator('#pauseControls').isVisible(),'Controls tab should be visible');
  await page.screenshot({path:join(output,'a10-settings-desktop.png'),animations:'disabled'});
  await page.locator('#pauseTabMenu').click();
  const stored=await page.evaluate(()=>localStorage.getItem('raftbound.save.v1'));
  assert(stored,'Save not written');
  const payload=JSON.parse(stored);assert.equal(payload.version,1);
  assert(payload.game.tiles.length>=4,'Raft state not saved');
  await page.locator('#resumeBtn').click();
  await page.screenshot({path:join(output,'raftbound-a09-webgl.png'),animations:'disabled'});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:join(output,'a10-hud-mobile.png'),animations:'disabled'});
  await page.locator('#bagBtn').click();
  assert(await page.locator('#bagPanel').isVisible(),'Mobile bag cannot open');
  await page.screenshot({path:join(output,'a10-backpack-mobile.png'),animations:'disabled'});
  await page.locator('#closeBag').click();
  await page.reload({waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#loadBtn')?.hasAttribute('disabled')===false,null,{timeout:45000});
  await page.locator('#loadBtn').click();
  assert(await page.locator('#startOverlay').evaluate(el=>el.classList.contains('hidden')),'Save restore failed');
  if(errors.length)throw new Error(errors.join('\n'));
  console.log(`PASS A10 actual Chromium WebGL2 · ${assetStatus} · start menu · inventory · crafting · filters · pause settings · responsive HUD · save/load`);
} catch(error){
  await writeFile(join(output,'browser-errors.txt'),`Error: ${String(error)}\n\n${errors.join('\n')}\n\nVite logs:\n${outputLog}`);
  throw error;
} finally {
  await browser?.close();
  server.kill('SIGTERM');
}
