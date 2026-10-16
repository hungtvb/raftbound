#!/usr/bin/env python3
"""HTTP resource presence check, independent of browser/WebGL permissions."""
import json,subprocess,time,urllib.request,urllib.error,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
req=['/','/game.js','/glb-loader.js','/survival-rules.js','/cast-motion.js','/styles.css']
req += ['/assets/glb/'+n+'.glb' for n in ('foundation_2m','salvage_net_tool','driftwood_plank','plastic_bottle','palm_leaf','compact_grill','solar_purifier','planter_box','storage_chest','survivor_sailor_skinned','salvage_barrel')]
req += ['/assets/textures/'+name+'.png' for name in ('wood_basecolor','wood_normal','wood_roughness')]
server=None
try:
 import socket
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 server=subprocess.Popen([sys.executable,'-m','http.server',str(port),'--bind','127.0.0.1'],cwd=root/'game',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 time.sleep(.45)
 results=[]
 for p in req:
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}{p}',timeout=5) as r:results.append({'file':p,'status':r.status,'length':len(r.read())})
  except Exception as ex:results.append({'file':p,'error':str(ex)})
 asset_check=[{'file':p,'exists':(root/'game'/p.lstrip('/')).is_file(),'size':(root/'game'/p.lstrip('/')).stat().st_size if (root/'game'/p.lstrip('/')).is_file() else 0} for p in req if p!='/']
 local_ok=all(x['exists'] and x['size']>0 for x in asset_check)
 http_ok=all(x.get('status')==200 and x.get('length',0)>0 for x in results)
 blocked=not http_ok and all('Connection refused' in x.get('error','') for x in results)
 report={'test':'A08 local HTTP resource acceptance','status':'PASS' if http_ok else ('BLOCKED' if blocked else 'FAIL'),'local_assets_pass':local_ok,'http_pass':http_ok,'files':results,'local_files':asset_check}
 out=root/'qa'/'http_results.json';out.write_text(json.dumps(report,indent=2)+'\n')
 print('Local assets:', 'PASS' if local_ok else 'FAIL', '| HTTP:',report['status'],'|',len(results),'files; report:',out)
 sys.exit(0 if http_ok else 3 if blocked and local_ok else 1)
finally:
 if server:
  server.terminate()
  try:server.wait(timeout=5)
  except subprocess.TimeoutExpired:server.kill()
