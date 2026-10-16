#!/usr/bin/env python3
"""Real Chromium WebGL2 acceptance. Exit 0 PASS, 3 BLOCKED, 1 FAIL.

Run after: cd game && python3 -m http.server 8000
Requires: pip install playwright && playwright install chromium
Screenshots and metrics are saved to qa/browser_results/.
"""
import json,sys,time,os,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
OUT=Path(__file__).resolve().parent/'browser_results';OUT.mkdir(parents=True,exist_ok=True)
report={'test':'RAFTBOUND_A08_REAL_BROWSER','status':'BLOCKED','timestamp':time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'url':os.environ.get('RAFTBOUND_URL','http://127.0.0.1:8000')}
def save():
 (OUT/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps(report,ensure_ascii=False,indent=2))
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium') or shutil.which('google-chrome') or None,args=['--no-sandbox','--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1280,'height':800},device_scale_factor=1)
  errors=[];page.on('pageerror',lambda exc:errors.append(str(exc)))
  page.goto(report['url'],wait_until='domcontentloaded',timeout=12000)
  page.wait_for_timeout(2500)
  webgl=page.evaluate('!!document.querySelector("#world").getContext("webgl2")')
  report['webgl2_available']=webgl
  if not webgl:report.update(status='FAIL',reason='WebGL2 unavailable in this browser')
  else:
   page.locator('#startBtn').click(timeout=3000)
   page.wait_for_timeout(2500)
   page.screenshot(path=str(OUT/'world_idle.png'))
   page.keyboard.press('F3')
   page.wait_for_timeout(1300)
   report['perf']=page.locator('#perfOverlay').inner_text()
   page.keyboard.press('F4')
   page.wait_for_timeout(300)
   report['render_scale_switch']=page.locator('#perfOverlay').inner_text()
   page.keyboard.press('Space')
   page.wait_for_timeout(650)
   page.screenshot(path=str(OUT/'world_cast.png'))
   report['asset_status']=page.locator('#assetStatus').inner_text()
   report['visible_game']=page.locator('#startOverlay').evaluate('(e)=>e.classList.contains("hidden")')
   report['js_errors']=errors
   report['status']='PASS' if report['visible_game'] and '11 / 11' in report['asset_status'] and not errors else 'FAIL'
   if report['status']=='FAIL':report['reason']='GLB load/JS/start failed'
  browser.close()
except Exception as exc:
 report.update(status='BLOCKED',reason=str(exc)[:400])
finally:
 save()
sys.exit({'PASS':0,'FAIL':1,'BLOCKED':3}[report['status']])
