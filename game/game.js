/* RAFTBOUND — dependency-free WebGL2 ocean survival game.
 * Renderer, world geometry, gameplay and save data are contained in this file.
 */
(() => {
'use strict';
const $ = s => document.querySelector(s);
const canvas = $('#world');
const rules=window.RaftRules;
const gl = canvas.getContext('webgl2',{antialias:true,alpha:false,powerPreference:'high-performance'});
if(!gl){ $('#startOverlay').innerHTML='<div class="intro-card"><h1>WebGL2 cần được bật</h1><p>Hãy mở bản game bằng phiên bản Chrome, Edge, Safari hoặc Firefox mới hơn có hỗ trợ WebGL2.</p></div>'; return; }
const VERT=`#version 300 es
precision highp float;
layout(location=0) in vec3 aPos;
layout(location=1) in vec3 aNormal;
layout(location=2) in vec4 aJoints;
layout(location=3) in vec4 aWeights;
layout(location=4) in vec3 aTint;
uniform float uHasTint;
out vec3 vTint;
uniform mat4 uMVP;uniform mat4 uModel;
uniform float uSkinning;
uniform mat4 uBones[17];
out vec3 vWorld;out vec3 vNormal;
void main(){
  mat4 s=mat4(1.);
  if(uSkinning>.5){
    s=uBones[int(aJoints.x)]*aWeights.x+uBones[int(aJoints.y)]*aWeights.y+
      uBones[int(aJoints.z)]*aWeights.z+uBones[int(aJoints.w)]*aWeights.w;
  }
  vec4 p=uModel*s*vec4(aPos,1.);
  vWorld=p.xyz;vNormal=normalize(mat3(uModel*s)*aNormal);
  vTint=mix(vec3(1.),aTint,uHasTint);
  gl_Position=uMVP*s*vec4(aPos,1.);
}`;
const FRAG=`#version 300 es
precision highp float;
in vec3 vWorld;in vec3 vNormal;in vec3 vTint;
uniform vec3 uColor;uniform vec3 uEye;uniform vec3 uFog;uniform vec3 uLight;
uniform float uUnlit;uniform float uWoodGrain;
uniform float uRoughness;uniform float uMetallic;
uniform float uUseWoodMap;
uniform sampler2D uWoodColorTex;uniform sampler2D uWoodRoughnessTex;uniform sampler2D uWoodNormalTex;
out vec4 oColor;
const float PI=3.14159265359;
vec3 sampleTri(sampler2D tex,vec3 p,vec3 axis){
  vec3 w=pow(abs(axis),vec3(4.));w/=max(dot(w,vec3(1.)),.0001);
  return texture(tex,p.yz*1.7).rgb*w.x+texture(tex,p.xz*1.7).rgb*w.y+texture(tex,p.xy*1.7).rgb*w.z;
}
void main(){
 vec3 N=normalize(vNormal),base=uColor*vTint;
 float rough=clamp(uRoughness,.08,1.0),metal=clamp(uMetallic,0.,1.);
 if(uUseWoodMap>.5){
  vec3 albedo=sampleTri(uWoodColorTex,vWorld,N);
  base*=mix(vec3(1.),albedo*1.34,.77);
  rough=clamp(mix(rough,sampleTri(uWoodRoughnessTex,vWorld,N).r,.65),.1,1.);
  // Small-scale wood normal detail: tangent-free world-space approximation.
  vec3 grain=sampleTri(uWoodNormalTex,vWorld,N)*2.-1.;
  N=normalize(N+vec3(grain.x,.25*grain.y,grain.z)*.085);
 }else if(uWoodGrain>.5){
  float grain=sin((vWorld.z+sin(vWorld.x*7.)*.04)*34.)*.03;
  base*=1.+grain;
 }
 vec3 L=normalize(uLight),V=normalize(uEye-vWorld),H=normalize(V+L);
 float NdotL=max(dot(N,L),0.),NdotV=max(dot(N,V),.001),NdotH=max(dot(N,H),0.),VdotH=max(dot(V,H),0.);
 float alpha=rough*rough,a2=alpha*alpha;
 float denom=NdotH*NdotH*(a2-1.)+1.;
 float D=a2/(PI*denom*denom+.0001);
 float k=(rough+1.)*(rough+1.)/8.;
 float G=(NdotL/(NdotL*(1.-k)+k))*(NdotV/(NdotV*(1.-k)+k));
 vec3 F0=mix(vec3(.04),base,metal),F=F0+(1.-F0)*pow(1.-VdotH,5.);
 vec3 spec=(D*G*F)/(4.*max(NdotL*NdotV,.001));
 vec3 diffuse=(1.-F)*(1.-metal)*base/PI;
 vec3 rgb=(diffuse+spec)*NdotL*2.0+base*vec3(.30,.36,.39);
 if(uUnlit>.5)rgb=base;
 float distanceToEye=length(vWorld-uEye);
 float fog=uUnlit>.5?0.:clamp((distanceToEye-25.)/145.,0.,.76);
 rgb=mix(rgb,uFog,fog);
 oColor=vec4(rgb,1.);
}`;
const WATER_VERT=`#version 300 es
precision highp float;
layout(location=0) in vec3 aPos;uniform mat4 uMVP;uniform float uTime;
out vec3 vWorld;out float vFoam;
float waves(vec2 p){return .09*sin(p.x*.45+uTime*1.03)+.075*cos(p.y*.38-uTime*.76)+.035*sin((p.x+p.y)*.9+uTime*1.7);}
void main(){vec3 p=aPos;p.y+=waves(p.xz);vFoam=p.y;vWorld=p;gl_Position=uMVP*vec4(p,1.);}`;
const WATER_FRAG=`#version 300 es
precision highp float;
in vec3 vWorld;in float vFoam;uniform float uTime;uniform vec3 uEye;uniform vec3 uFog;out vec4 oColor;
void main(){vec2 uv=vWorld.xz;float n=sin(uv.x*.95+uTime*1.35)*sin(uv.y*.77-uTime*.8);float rip=sin((uv.x+uv.y)*2.2+uTime*2.1)*.5+.5;float shimmer=pow(max(0.,sin(uv.x*1.9+uv.y*.6+uTime*1.8)),20.);vec3 deep=vec3(.035,.35,.46);vec3 turquoise=vec3(.13,.57,.64);vec3 col=mix(deep,turquoise,clamp(.52+vFoam*.72+n*.08,0.,1.));col+=vec3(.13,.19,.14)*shimmer*.25+vec3(.045,.09,.09)*rip*.12;float dist=length(vWorld.xz-uEye.xz);float fog=clamp((dist-38.)/190.,0.,.9);col=mix(col,uFog,fog);oColor=vec4(col,1.);}`;
function shader(type,code){const s=gl.createShader(type);gl.shaderSource(s,code);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;}
function program(v,f){const p=gl.createProgram();gl.attachShader(p,shader(gl.VERTEX_SHADER,v));gl.attachShader(p,shader(gl.FRAGMENT_SHADER,f));gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p));return p;}
let mainP,seaP;try{mainP=program(VERT,FRAG);seaP=program(WATER_VERT,WATER_FRAG)}catch(e){$('#startOverlay').textContent='Lỗi khởi tạo đồ họa: '+e.message;return}
const loc=(p,n)=>gl.getUniformLocation(p,n);
const mainU={mvp:loc(mainP,'uMVP'),model:loc(mainP,'uModel'),color:loc(mainP,'uColor'),eye:loc(mainP,'uEye'),fog:loc(mainP,'uFog'),light:loc(mainP,'uLight'),unlit:loc(mainP,'uUnlit'),wood:loc(mainP,'uWoodGrain'),skin:loc(mainP,'uSkinning'),bones:loc(mainP,'uBones[0]'),rough:loc(mainP,'uRoughness'),metal:loc(mainP,'uMetallic'),tint:loc(mainP,'uHasTint'),woodMap:loc(mainP,'uUseWoodMap'),woodColor:loc(mainP,'uWoodColorTex'),woodRough:loc(mainP,'uWoodRoughnessTex'),woodNormal:loc(mainP,'uWoodNormalTex')};
const seaU={mvp:loc(seaP,'uMVP'),time:loc(seaP,'uTime'),eye:loc(seaP,'uEye'),fog:loc(seaP,'uFog')};
const clamp=(n,a,b)=>Math.min(b,Math.max(a,n)), lerp=(a,b,t)=>a+(b-a)*t, rnd=(a,b)=>a+Math.random()*(b-a);
const hex=h=>{h=h.replace('#','');return [parseInt(h.slice(0,2),16)/255,parseInt(h.slice(2,4),16)/255,parseInt(h.slice(4,6),16)/255]};
const C={wood:hex('#b97d45'),plank:hex('#c58f54'),edge:hex('#775133'),rope:hex('#e2bb78'),skin:hex('#f0b17a'),shirt:hex('#f9db83'),pants:hex('#2d5062'),dark:hex('#183344'),white:hex('#f5efe0'),leaf:hex('#438b5a'),leafLight:hex('#6eae60'),plastic:hex('#a8e6de'),metal:hex('#a2adb1'),stone:hex('#60646d'),water:hex('#64cbd2'),grill:hex('#5a6061'),fire:hex('#ef9f44'),red:hex('#d98470'),yellow:hex('#eed17e'),fin:hex('#526b75'),black:hex('#1c343e')};
const ID=()=>[1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1];
function mul(a,b){let c=new Array(16);for(let j=0;j<4;j++)for(let i=0;i<4;i++)c[j*4+i]=a[i]*b[j*4]+a[4+i]*b[j*4+1]+a[8+i]*b[j*4+2]+a[12+i]*b[j*4+3];return c}
function model(x=0,y=0,z=0,sx=1,sy=1,sz=1,ry=0,rx=0,rz=0){let cy=Math.cos(ry),syy=Math.sin(ry),cx=Math.cos(rx),sxx=Math.sin(rx),cz=Math.cos(rz),szz=Math.sin(rz);const T=ID();T[12]=x;T[13]=y;T[14]=z;const Y=[cy,0,-syy,0,0,1,0,0,syy,0,cy,0,0,0,0,1],X=[1,0,0,0,0,cx,sxx,0,0,-sxx,cx,0,0,0,0,1],Z=[cz,szz,0,0,-szz,cz,0,0,0,0,1,0,0,0,0,1],S=[sx,0,0,0,0,sy,0,0,0,0,sz,0,0,0,0,1];return mul(mul(mul(mul(T,Y),X),Z),S)}
function perspective(fovy,aspect,near,far){let f=1/Math.tan(fovy/2),n=1/(near-far);return [f/aspect,0,0,0,0,f,0,0,0,0,(far+near)*n,-1,0,0,2*far*near*n,0]}
function norm(v){let l=Math.hypot(...v)||1;return v.map(x=>x/l)}function cross(a,b){return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]}function dot(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]}
function look(eye,at){let z=norm(eye.map((v,i)=>v-at[i])),x=norm(cross([0,1,0],z)),y=cross(z,x);return [x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]}
function mesh(pos,normal,idx,joints=null,weights=null,colors=null){
 const vao=gl.createVertexArray();gl.bindVertexArray(vao);
 const attr=(slot,data,width)=>{const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(data),gl.STATIC_DRAW);gl.enableVertexAttribArray(slot);gl.vertexAttribPointer(slot,width,gl.FLOAT,false,0,0);};
 attr(0,pos,3);attr(1,normal,3);
 if(joints&&weights){attr(2,joints,4);attr(3,weights,4);}
 if(colors){attr(4,colors,3);}
 const ib=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint32Array(idx),gl.STATIC_DRAW);
 gl.bindVertexArray(null);return {vao,count:idx.length,skinned:!!joints,hasTint:!!colors};
}
function makeBox(){let p=[],n=[],idx=[];let faces=[[[1,0,0],[[.5,-.5,.5],[.5,-.5,-.5],[.5,.5,-.5],[.5,.5,.5]]],[[-1,0,0],[[-.5,-.5,-.5],[-.5,-.5,.5],[-.5,.5,.5],[-.5,.5,-.5]]],[[0,1,0],[[-.5,.5,.5],[.5,.5,.5],[.5,.5,-.5],[-.5,.5,-.5]]],[[0,-1,0],[[-.5,-.5,-.5],[.5,-.5,-.5],[.5,-.5,.5],[-.5,-.5,.5]]],[[0,0,1],[[-.5,-.5,.5],[.5,-.5,.5],[.5,.5,.5],[-.5,.5,.5]]],[[0,0,-1],[[.5,-.5,-.5],[-.5,-.5,-.5],[-.5,.5,-.5],[.5,.5,-.5]]]];for(let face of faces){let s=p.length/3;for(let v of face[1]){p.push(...v);n.push(...face[0])}idx.push(s,s+1,s+2,s,s+2,s+3)}return mesh(p,n,idx)}
function makeSphere(rings=10,segments=14){let p=[],n=[],idx=[];for(let i=0;i<=rings;i++){let t=Math.PI*i/rings;for(let j=0;j<=segments;j++){let a=2*Math.PI*j/segments,v=[Math.sin(t)*Math.cos(a),Math.cos(t),Math.sin(t)*Math.sin(a)];p.push(...v);n.push(...v)}}for(let i=0;i<rings;i++)for(let j=0;j<segments;j++){let a=i*(segments+1)+j,b=a+segments+1;idx.push(a,a+1,b,b,a+1,b+1)}return mesh(p,n,idx)}
function makeCylinder(segments=12){let p=[],n=[],idx=[];for(let j=0;j<=segments;j++){let a=2*Math.PI*j/segments,x=Math.cos(a),z=Math.sin(a);p.push(x,.5,z,x,-.5,z);n.push(x,0,z,x,0,z)}for(let j=0;j<segments;j++){let i=j*2;idx.push(i,i+2,i+1,i+1,i+2,i+3)}for(let ty of [-.5,.5]){let off=p.length/3;p.push(0,ty,0);n.push(0,Math.sign(ty),0);for(let j=0;j<=segments;j++){let a=2*Math.PI*j/segments;p.push(Math.cos(a),ty,Math.sin(a));n.push(0,Math.sign(ty),0)}for(let j=0;j<segments;j++)if(ty>0)idx.push(off,off+j+2,off+j+1);else idx.push(off,off+j+1,off+j+2)}return mesh(p,n,idx)}
function makeCone(segments=12){let p=[],n=[],idx=[];for(let i=0;i<segments;i++){let a=i*2*Math.PI/segments,b=(i+1)*2*Math.PI/segments,v=[[0,.5,0],[Math.cos(a),-.5,Math.sin(a)],[Math.cos(b),-.5,Math.sin(b)]];let no=norm([Math.cos((a+b)/2),.85,Math.sin((a+b)/2)]),s=p.length/3;v.forEach(q=>{p.push(...q);n.push(...no)});idx.push(s,s+2,s+1)}return mesh(p,n,idx)}
function makeTorus(major=1,minor=.12){let p=[],n=[],idx=[];const A=20,B=6;for(let i=0;i<=A;i++){let a=2*Math.PI*i/A;for(let j=0;j<=B;j++){let b=2*Math.PI*j/B,rr=major+minor*Math.cos(b);p.push(rr*Math.cos(a),minor*Math.sin(b),rr*Math.sin(a));n.push(Math.cos(b)*Math.cos(a),Math.sin(b),Math.cos(b)*Math.sin(a))}}for(let i=0;i<A;i++)for(let j=0;j<B;j++){let a=i*(B+1)+j,b=a+B+1;idx.push(a,a+1,b,b,a+1,b+1)}return mesh(p,n,idx)}
function makeGrid(){let p=[],n=[],idx=[],N=85,S=500;for(let i=0;i<=N;i++)for(let j=0;j<=N;j++){p.push((i/N-.5)*S,0,(j/N-.5)*S);n.push(0,1,0)}for(let i=0;i<N;i++)for(let j=0;j<N;j++){let a=i*(N+1)+j,b=a+N+1;idx.push(a,a+1,b,b,a+1,b+1)}return mesh(p,n,idx)}
const M={box:makeBox(),sphere:makeSphere(),cyl:makeCylinder(),cone:makeCone(),torus:makeTorus(1,.12),sea:makeGrid()};
const assetMap={foundation:'foundation_2m',net:'salvage_net_tool',wood:'driftwood_plank',plastic:'plastic_bottle',leaf:'palm_leaf',barrel:'salvage_barrel',purifier:'solar_purifier',grill:'compact_grill',planter:'planter_box',storage:'storage_chest',survivor:'survivor_sailor_skinned'};
const ASSETS={};let visualMode='legacy';let assetStatus='loading';
// Uses real A03 texture maps at runtime, with procedural wood color fallback.
const woodTextures=[];let woodMapsReady=false;
function loadWoodTextures(){
 if(typeof Image==='undefined')return;
 const files=['wood_basecolor.png','wood_roughness.png','wood_normal.png'];
 let ready=0;
 files.forEach((file,slot)=>{
  const im=new Image();im.onload=()=>{
   const t=gl.createTexture();gl.activeTexture(gl.TEXTURE0+slot);gl.bindTexture(gl.TEXTURE_2D,t);
   gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,0);
   gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,im);
   gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);
   gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.REPEAT);
   gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);
   gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
   gl.generateMipmap(gl.TEXTURE_2D);woodTextures[slot]=t;
   if(++ready===files.length)woodMapsReady=true;
  };
  im.onerror=()=>console.warn('[RAFTBOUND] Unable to load',file);
  im.src='assets/textures/'+file;
 });
}
loadWoodTextures();
async function loadGameAssets(){
  if(!window.RaftGLB){assetStatus='missing';setAssetStatus('Không tìm thấy glb-loader.js');return;}
  const results=await Promise.allSettled(Object.entries(assetMap).map(async ([key,name])=>{
    let parts=await window.RaftGLB.fetchAsset('assets/glb/'+name+'.glb',mesh);
    ASSETS[key]=parts;return key;
  }));
  const success=results.filter(r=>r.status==='fulfilled').length;
  assetStatus=success===Object.keys(assetMap).length?'ready':'partial';
  visualMode=success?'glb':'legacy';
  setAssetStatus(success+' / '+Object.keys(assetMap).length+' GLB đã tải · '+(success?'Phím G đổi đồ họa':'đang dùng model dự phòng'));
  for(const result of results)if(result.status==='rejected')console.warn('[RAFTBOUND GLB]',result.reason);
}
function setAssetStatus(t){let b=$('#assetStatus');if(b)b.textContent=t;}
loadGameAssets().catch(e=>{assetStatus='error';setAssetStatus('GLB không tải được · Đang dùng hình học dự phòng');console.warn(e)});
let running=false,paused=false,elapsed=0,realClock=0,lastFrame=performance.now(),aim=null,netFx=null,noticeTimer=0,spawnTimer=0,sharkTimer=0,uiTimer=0,saveTimer=0,mouseDown=false,cameraYaw=0,cameraPitch=.42,cameraDistance=11,cameraPreset=0,screenshotRequested=false;
let keys={},game={},debris=[],sharkAngle=1.4,sharkDist=15;
let renderScale=.9;let perfVisible=false,perfFrames=0,perfLast=performance.now(),perfFPS=0,perfDrawCalls=0,perfTriangles=0;
const TILE=2.0;const itemDefs={wood:{icon:'🪵',name:'Gỗ',color:C.wood},plastic:{icon:'🧴',name:'Nhựa',color:C.plastic},leaf:{icon:'🌿',name:'Lá',color:C.leaf},metal:{icon:'🔩',name:'Kim loại',color:C.metal},seed:{icon:'🌱',name:'Hạt giống',color:C.leafLight},fish:{icon:'🐟',name:'Cá sống',color:C.white},meal:{icon:'🍲',name:'Thức ăn',color:C.yellow},fresh:{icon:'💧',name:'Nước sạch',color:C.water}};
const recipes=[
 {id:'raft',category:'XÂY DỰNG',icon:'🪵',title:'Mở rộng bè',desc:'Đặt thêm 1 ô sàn theo hướng bạn đang nhìn.',cost:{wood:4,plastic:2}},
 {id:'purifier',category:'THIẾT BỊ SINH TỒN',icon:'💧',title:'Máy lọc nước',desc:'Tự tạo 1 chai nước sạch mỗi 20 giây.',cost:{wood:4,plastic:3,metal:1}},
 {id:'grill',category:'THIẾT BỊ SINH TỒN',icon:'🔥',title:'Bếp nướng',desc:'Tự nướng cá sống thành thức ăn.',cost:{wood:5,metal:2,plastic:1}},
 {id:'planter',category:'TRỒNG TRỌT',icon:'🌱',title:'Khay trồng rau',desc:'Tự thu hoạch 1 khẩu phần mỗi 35 giây.',cost:{wood:4,plastic:2,leaf:2,seed:1}},
 {id:'storage',category:'XÂY DỰNG',icon:'📦',title:'Rương đồ',desc:'Trang trí bè, đánh dấu bước tiến của bạn.',cost:{wood:6,plastic:3}},
 {id:'spear',category:'CÔNG CỤ',icon:'🔱',title:'Giáo chống cá mập',desc:'Giảm thiệt hại mỗi khi cá mập tấn công.',cost:{wood:3,metal:3}}
];
const quests=[
 {name:'Thu gom nguyên liệu',desc:'Bắt 5 vật phẩm trôi nổi bằng vợt.',need:5,progress:g=>Math.min(5,g.collected)},
 {name:'Mở rộng chiếc bè',desc:'Xây thêm ít nhất 1 ô sàn mới.',need:1,progress:g=>Math.max(0,g.tiles.length-4)},
 {name:'Nguồn nước ổn định',desc:'Chế tạo máy lọc nước.',need:1,progress:g=>g.buildings.some(b=>b.id==='purifier')?1:0},
 {name:'Bữa ăn đầu tiên',desc:'Chế tạo bếp nướng.',need:1,progress:g=>g.buildings.some(b=>b.id==='grill')?1:0},
 {name:'Vườn giữa biển',desc:'Chế tạo khay trồng rau.',need:1,progress:g=>g.buildings.some(b=>b.id==='planter')?1:0},
 {name:'Trụ vững qua đêm',desc:'Sống tới ngày thứ 2.',need:1,progress:g=>g.day>=2?1:0}
];
function newGame(){game={hp:100,food:87,water:83,day:1,seconds:0,player:{x:0,z:0},inv:{wood:2,plastic:1,leaf:0,metal:0,seed:0,fish:0,meal:1,fresh:1},tiles:[[-1,-1],[-1,0],[0,-1],[0,0]],buildings:[],collected:0,quest:0,crafts:0,waterTimer:0,cookTimer:0,growTimer:0,sharkHits:0,hasSpear:false};debris=[];spawnTimer=0;sharkAngle=1.4;for(let i=0;i<28;i++)spawnDebris(true);updateUI()}
function save(){if(!running)return;try{localStorage.setItem('raftbound.save.v1',JSON.stringify({game,elapsed,version:1}))}catch(_){}}
function load(){
 try{
  const restored=rules.readSave(JSON.parse(localStorage.getItem('raftbound.save.v1')));
  if(!restored)return false;
  game=restored.game;elapsed=restored.elapsed;debris=[];netFx=null;actionFx=null;
  for(let i=0;i<26;i++)spawnDebris(true);
  updateUI();return true;
 }catch(_){return false}
}
function start(loadSaved=false){if(!loadSaved||!load())newGame();running=true;paused=false;$('#startOverlay').classList.add('hidden');$('#pauseOverlay').classList.add('hidden');$('#loadBtn').disabled=false;tip('Dùng WASD di chuyển. Nhấn SPACE để quăng vợt.');}
function tip(s){const el=$('#notice');el.textContent=s;el.classList.add('show');noticeTimer=2.6}
function togglePause(force){if(!running)return;paused=force===undefined?!paused:force;$('#pauseOverlay').classList.toggle('hidden',!paused);if(paused)save()}
function toggleCraft(force){if(!running||paused)return;let open=force===undefined?!$('#craftPanel').classList.contains('open'):force;$('#craftPanel').classList.toggle('open',open);if(open)renderRecipes()}
function canPay(cost){return Object.entries(cost).every(([r,n])=>(game.inv[r]||0)>=n)}
function pay(cost){for(let [r,n] of Object.entries(cost))game.inv[r]-=n}
function pickEmptyTile(){let used=new Set(game.buildings.map(b=>b.x+','+b.z));return game.tiles.filter(([x,z])=>!used.has(x+','+z)).sort((a,b)=>Math.hypot(a[0],a[1])-Math.hypot(b[0],b[1]))[0]}
function addTile(){const next=rules.expandRaft(game.tiles,cameraYaw);if(!next)return false;game.tiles.push(next);return true;}
let actionFx=null;
function craft(id){const r=recipes.find(x=>x.id===id);if(!r)return;if(!canPay(r.cost)){tip('Chưa đủ nguyên liệu để chế tạo.');return}if(id!=='raft'&&id!=='spear'&&!pickEmptyTile()){tip('Bè đã hết chỗ! Hãy mở rộng bè trước.');return}if(id==='spear'&&game.hasSpear){tip('Bạn đã có giáo phòng thủ rồi.');return}if(id==='raft'&&!rules.expandRaft(game.tiles,cameraYaw)){tip('Đã đạt giới hạn mở rộng bè.');return}pay(r.cost);if(id==='raft'){addTile();tip('Đã thêm một ô sàn! Chiếc bè đang lớn dần.')}else if(id==='spear'){game.hasSpear=true;tip('Đã trang bị giáo phòng thủ tự động!')}else{let [x,z]=pickEmptyTile();game.buildings.push({id,x,z});tip('Đã xây dựng: '+r.title)}game.crafts++;actionFx={kind:'craft',time:0};checkQuests();renderRecipes();updateUI();save()}
function renderRecipes(){const groups=['XÂY DỰNG','THIẾT BỊ SINH TỒN','TRỒNG TRỌT','CÔNG CỤ'];$('#craftRecipes').innerHTML=groups.map(cat=>`<div class="section-title">${cat}</div>`+recipes.filter(r=>r.category===cat).map(r=>{let cost=Object.entries(r.cost).map(([id,n])=>`${itemDefs[id]?.icon||''} ${n}`).join(' · ');let disabled=!canPay(r.cost)||(r.id==='raft'&&!rules.expandRaft(game.tiles,cameraYaw))||(r.id!=='raft'&&r.id!=='spear'&&!pickEmptyTile())||(r.id==='spear'&&game.hasSpear);return `<div class="recipe"><div class="recipe-copy"><strong>${r.icon} ${r.title}</strong><p>${r.desc}</p><div class="cost">${cost}</div></div><button ${disabled?'disabled':''} data-craft="${r.id}">${disabled?'THIẾU ĐỒ':'CHẾ TẠO'}</button></div>`}).join('')).join('');document.querySelectorAll('[data-craft]').forEach(btn=>btn.addEventListener('click',()=>craft(btn.dataset.craft)))}
function consume(kind){const k=kind==='eat'?'meal':'fresh';if(game.inv[k]<=0){tip(kind==='eat'?'Chưa có thức ăn. Chế tạo bếp hoặc khay trồng rau.':'Chưa có nước sạch. Hãy chế tạo máy lọc nước.');return}game.inv[k]--;if(kind==='eat')game.food=clamp(game.food+29,0,100);else game.water=clamp(game.water+37,0,100);tip(kind==='eat'?'Đã ăn. Độ no +29':'Đã uống. Nước uống +37');updateUI();save()}
function checkQuests(){let old=game.quest;while(game.quest<quests.length&&quests[game.quest].progress(game)>=quests[game.quest].need)game.quest++;if(old!==game.quest){if(game.quest===quests.length)tip('Chúc mừng! Bạn đã chinh phục thử thách sinh tồn!');else tip('Hoàn thành mục tiêu! Nhiệm vụ mới đã mở.')}}
function spawnDebris(initial=false){if(debris.length>60)return;const types=['wood','wood','wood','plastic','plastic','leaf','leaf','metal','seed','fish'];let t=types[Math.floor(Math.random()*types.length)];let x=rnd(-11,11),z=initial?rnd(-27,17):rnd(-42,-30);debris.push({type:t,x,z,speed:rnd(.36,.82),sway:rnd(0,Math.PI*2),phase:rnd(0,6.3),rot:rnd(0,6.3)})}
function nearDebris(){return rules.selectDebris(debris,game.player,cameraYaw)}
function cast(){if(!running||paused||netFx)return;aim=nearDebris();let dest=aim?{x:aim.x,z:aim.z}:{x:game.player.x-Math.sin(cameraYaw)*8,z:game.player.z-Math.cos(cameraYaw)*8};netFx={time:0,from:{...game.player},to:dest,object:aim,caught:false};}
function catchDebris(d){let index=debris.indexOf(d);if(index<0)return;debris.splice(index,1);game.inv[d.type]=(game.inv[d.type]||0)+1;game.collected++;actionFx={kind:'collect',time:0};tip('+'+itemDefs[d.type].icon+' '+itemDefs[d.type].name+' đã thu thập');if(Math.random()<.12){game.inv.plastic++;}checkQuests();updateUI()}
function updateUI(){if(!game.inv)return;for(let [key,val] of [['hp',game.hp],['food',game.food],['water',game.water]]){$('#'+key+'Val').textContent=Math.ceil(val);$('#'+key+'Bar').style.width=val+'%'}$('#dayInfo').textContent='☀ NGÀY '+String(game.day).padStart(2,'0');$('#waveInfo').textContent=game.hasSpear?'CÓ PHÒNG THỦ':'BIỂN ÊM';const r=quests[game.quest];$('#questTitle').textContent=r?r.name:'CHINH PHỤC ĐẠI DƯƠNG';$('#questDesc').textContent=r?r.desc:'Hãy tiếp tục phát triển chiếc bè của bạn!';$('#questProgress').style.width=r?100*r.progress(game)/r.need+'%':'100%';let display=['wood','plastic','leaf','metal','seed','fish','meal','fresh'];$('#inventory').innerHTML=display.map(k=>`<div class="inv-item" title="${itemDefs[k].name}"><span class="num">${game.inv[k]||0}</span><span class="emoji">${itemDefs[k].icon}</span><span class="inv-label">${itemDefs[k].name}</span></div>`).join('')}
function safeStanding(x,z){return rules.onRaft(x,z,game.tiles,TILE)}
function simulate(dt){if(actionFx){actionFx.time+=dt;if(actionFx.time>1.25)actionFx=null;}elapsed+=dt;game.seconds+=dt;game.day=1+Math.floor(elapsed/200);game.food=clamp(game.food-dt*.087,0,100);game.water=clamp(game.water-dt*.115,0,100);if(!game.food||!game.water){game.hp=clamp(game.hp-dt*2.1,0,100)}else game.hp=clamp(game.hp+dt*.022,0,100);if(game.hp<=0){game.hp=35;game.food=25;game.water=25;tip('Bạn kiệt sức! Một đợt sóng đẩy bạn trở lại bè.');}
 let mx=(keys.d?1:0)-(keys.a?1:0),mz=(keys.s?1:0)-(keys.w?1:0),l=Math.hypot(mx,mz);if(l){mx/=l;mz/=l;let sin=Math.sin(cameraYaw),cos=Math.cos(cameraYaw),vx=mx*cos+mz*sin,vz=-mx*sin+mz*cos,speed=3.7*dt,newX=game.player.x+vx*speed,newZ=game.player.z+vz*speed;if(safeStanding(newX,newZ)){game.player.x=newX;game.player.z=newZ}else{tipOnce('Không thể đi xuống biển. Hãy mở rộng bè!')}}
 for(let d of debris){d.z+=d.speed*dt;d.x+=Math.sin(elapsed*.23+d.sway)*dt*.12;if(d.z>35){d.z=-38;d.x=rnd(-12,12)}}spawnTimer+=dt;if(spawnTimer>1.8){spawnTimer=0;spawnDebris()}
 if(netFx){netFx.time+=dt;if(netFx.time>=window.RaftCastMotion.CAST.contact&&!netFx.caught){netFx.caught=true;if(rules.castHit(netFx.object,netFx.from,netFx.to,debris))catchDebris(netFx.object);else if(Math.random()<.13){game.inv.fish++;tip('Bạn may mắn vớt được một con cá!');updateUI()}else tip('Vợt không bắt trúng vật phẩm nào.')}if(netFx.time>=window.RaftCastMotion.CAST.end)netFx=null}
 if(game.buildings.some(b=>b.id==='purifier')){game.waterTimer+=dt;if(game.waterTimer>20){game.waterTimer=0;game.inv.fresh++;tip('Máy lọc nước: +1 nước sạch');updateUI()}}
 if(game.buildings.some(b=>b.id==='grill')&&game.inv.fish>0){game.cookTimer+=dt;if(game.cookTimer>11){game.cookTimer=0;game.inv.fish--;game.inv.meal++;tip('Bếp nướng: +1 phần ăn');updateUI()}}
 if(game.buildings.some(b=>b.id==='planter')){game.growTimer+=dt;if(game.growTimer>35){game.growTimer=0;game.inv.meal++;tip('Thu hoạch từ khay trồng: +1 thức ăn');updateUI()}}
 sharkAngle+=dt*.17;sharkTimer+=dt;if(sharkTimer>58){sharkTimer=0;game.sharkHits++;game.hp=clamp(game.hp-(game.hasSpear?3:13),0,100);tip(game.hasSpear?'Cá mập lao tới nhưng giáo đã đẩy lùi nó!':'Cá mập tấn công! Sinh lực -13');}
 aim=nearDebris();$('#aimText').textContent=aim?`${itemDefs[aim.type].icon} ${itemDefs[aim.type].name} · ${Math.hypot(aim.x-game.player.x,aim.z-game.player.z).toFixed(1)}m · SPACE để vớt`:'Quay camera về phía vật phẩm để quăng vợt';
 checkQuests();uiTimer+=dt;saveTimer+=dt;if(uiTimer>.2){uiTimer=0;updateUI();if($('#craftPanel').classList.contains('open'))renderRecipes()}if(saveTimer>10){saveTimer=0;save()}
}
let lastWarning=0;function tipOnce(msg){if(elapsed-lastWarning>3){lastWarning=elapsed;tip(msg)}}
function resize(){const scale=Math.min(window.devicePixelRatio||1,1.7)*renderScale,w=Math.max(1,Math.floor(innerWidth*scale)),h=Math.max(1,Math.floor(innerHeight*scale));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h)}}
const sea=hex('#acdce0');let vp,eye=[8,7,11],fog=[.67,.84,.86];
function renderMesh(meshId,color,mm,unlit=0,wood=0,palette=null,rough=.86,metal=0){
 const m=typeof meshId==='string'?M[meshId]:meshId;
 gl.uniformMatrix4fv(mainU.mvp,false,new Float32Array(mul(vp,mm)));
 gl.uniformMatrix4fv(mainU.model,false,new Float32Array(mm));
 gl.uniform3fv(mainU.color,color);gl.uniform1f(mainU.unlit,unlit);
 gl.uniform1f(mainU.wood,wood);gl.uniform1f(mainU.rough,rough);gl.uniform1f(mainU.metal,metal);
 gl.uniform1f(mainU.woodMap,wood&&woodMapsReady?1:0);
 gl.uniform1f(mainU.skin,palette?1:0);
 gl.uniform1f(mainU.tint,m.hasTint?1:0);
 if(palette)gl.uniformMatrix4fv(mainU.bones,false,new Float32Array(palette));
 gl.bindVertexArray(m.vao);gl.drawElements(gl.TRIANGLES,m.count,gl.UNSIGNED_INT,0);
 perfDrawCalls++;perfTriangles+=m.count/3;
}
function draw(geo,color,x,y,z,sx=1,sy=1,sz=1,ry=0,rx=0,rz=0,unlit=0){renderMesh(geo,color,model(x,y,z,sx,sy,sz,ry,rx,rz),unlit)}
function drawAsset(id,x,y,z,sx=1,sy=1,sz=1,ry=0,rx=0,rz=0){
 const parts=visualMode==='glb'?ASSETS[id]:null;
 if(!parts||!parts.length)return false;
 const parent=model(x,y,z,sx,sy,sz,ry,rx,rz);
 // GLB has double-sided materials; retain both front/back for braided rope and leaf pieces.
 gl.disable(gl.CULL_FACE);
 for(const p of parts)renderMesh(p.mesh,p.color,mul(parent,p.transform),0,/wood|timber/i.test(p.materialName||'')?1:0,null,p.roughness,p.metallic);
 gl.enable(gl.CULL_FACE);
 return true;
}
function tile(x,z){let xx=(x+.5)*TILE,zz=(z+.5)*TILE,bob=Math.sin(realClock*.9)*.075;if(drawAsset('foundation',xx,bob+.28,zz))return;draw('box',C.edge,xx,bob+.05,zz,TILE+.1,.27,TILE+.1);for(let i=0;i<5;i++){let offset=(i-2)*.44;draw('box',i%2===0?C.plank:C.wood,xx+offset,bob+.22,zz,.405,.095,TILE-.07);draw('box',C.rope,xx+offset,bob+.278,zz,.018,.009,TILE-.12)}for(let a of [-1,1])for(let b of [-1,1])draw('cyl',C.edge,xx+a*1.03,bob+.04,zz+b*1.03,.09,.42,.09)}
function segment(col,a,b,rad=.04){let d=[b[0]-a[0],b[1]-a[1],b[2]-a[2]],len=Math.hypot(...d);if(len<.001)return;let y=norm(d),reference=Math.abs(y[1])>.99?[1,0,0]:[0,1,0],x=norm(cross(reference,y)),z=cross(x,y),m=[x[0]*rad,x[1]*rad,x[2]*rad,0,y[0]*len,y[1]*len,y[2]*len,0,z[0]*rad,z[1]*rad,z[2]*rad,0,(a[0]+b[0])/2,(a[1]+b[1])/2,(a[2]+b[2])/2,1];renderMesh('cyl',col,m)}
function objectPart(id,x,y,z){let wave=Math.sin(realClock*.9)*.075;let t=realClock;if(drawAsset(id,x,wave+.32,z))return;switch(id){
case 'purifier':draw('box',C.edge,x,wave+.52,z,1.55,.14,1.45);for(let dx of [-.55,.55])for(let dz of [-.5,.5])draw('cyl',C.wood,x+dx,wave+.33,z+dz,.12,.59,.12);draw('cyl',C.metal,x-.27,wave+1.02,z,.36,.93,.36);draw('cyl',C.plastic,x-.27,wave+1.55,z,.25,.15,.25);draw('cyl',C.water,x+.45,wave+.83,z,.33,.38,.33);draw('torus',C.rope,x-.27,wave+1.6,z,.25,.18,.25);break;
case 'grill':draw('box',C.edge,x,wave+.59,z,1.48,.19,1.38);for(let k of [-.54,.54])draw('box',C.wood,x+k,wave+.33,z,.15,.62,1.1);draw('box',C.grill,x,wave+.75,z,1.22,.24,1.02);draw('box',C.black,x,wave+.89,z,.94,.11,.79);for(let i=-2;i<=2;i++)draw('box',C.metal,x+i*.19,wave+.98,z,.04,.07,.78);draw('sphere',C.fire,x,wave+1.08,z,.19,.18,.19,0,0,0,1);if(Math.sin(t*4)>0)draw('sphere',C.fire,x+.11,wave+1.19,z,.08,.12,.07);break;
case 'planter':draw('box',C.wood,x,wave+.54,z,1.54,.37,1.33);draw('box',C.stone,x,wave+.76,z,1.33,.1,1.12);for(let i=-1;i<=1;i++){let xx=x+i*.38;draw('cyl',C.leaf,xx,wave+1.03,z,.07,.54,.07);draw('sphere',C.leafLight,xx-.13,wave+1.28,z,.19,.10,.11,0,0,-.44);draw('sphere',C.leaf,xx+.12,wave+1.14,z,.18,.1,.1,0,0,.43)}break;
case 'storage':draw('box',C.wood,x,wave+.66,z,1.45,.96,1.26);for(let xx of [-.52,.52])draw('box',C.metal,x+xx,wave+.66,z,.1,1.01,1.3);draw('box',C.edge,x,wave+1.16,z,1.5,.13,1.28);draw('box',C.rope,x,wave+.75,z+.651,.22,.2,.06);break;}}
function floatingDebris(d){let yy=Math.sin(realClock*1.65+d.phase)*.11+.13,ry=d.rot+realClock*.065;
 const id={wood:'wood',plastic:'plastic',leaf:'leaf'}[d.type];
 if(id&&drawAsset(id,d.x,yy+(id==='plastic'?.16:.07),d.z,1,1,1,ry))return;
switch(d.type){case 'wood':draw('cyl',C.wood,d.x,yy,d.z,.25,1.22,.25,ry,0,Math.PI/2);draw('cyl',C.edge,d.x,yy,d.z,.17,1.24,.17,ry,0,Math.PI/2);break;case 'plastic':draw('cyl',C.plastic,d.x,yy,d.z,.20,.78,.20,ry,0,Math.PI/2);draw('cyl',C.white,d.x+.33,yy,d.z,.12,.19,.12,ry,0,Math.PI/2);break;case 'leaf':for(let i=0;i<3;i++)draw('sphere',i===0?C.leaf:C.leafLight,d.x+(i-1)*.2,yy,d.z,.14,.08,.56,ry+(i-1)*.38);break;case 'metal':draw('box',C.metal,d.x,yy,d.z,.7,.27,.62,ry);draw('box',C.dark,d.x,yy+.15,d.z,.35,.08,.28,ry);break;case 'seed':draw('box',C.wood,d.x,yy,d.z,.58,.38,.56,ry);draw('box',C.leafLight,d.x,yy+.19,d.z,.35,.09,.35,ry);break;case 'fish':draw('sphere',C.metal,d.x,yy,d.z,.46,.17,.24,ry);draw('cone',C.plastic,d.x+.38,yy,d.z,.17,.31,.18,ry,0,Math.PI/2);break;}}
function animatedSurvivor(x,dy,z,yaw,walking){
 const parts=visualMode==='glb'?ASSETS.survivor:null;
 if(!parts||!parts.length)return false;
 const stride=walking?Math.sin(realClock*10)*.47:0;
 const swing=walking?Math.sin(realClock*10)*.34:0;
 const breathe=Math.sin(realClock*1.6)*.025;
 // A06: rig, flying tool and gameplay all share one deterministic cast timeline.
 const castPose=netFx?window.RaftCastMotion.state(netFx.time):null;
 const throwArm=castPose?.throwArm||0,throwElbow=castPose?.throwElbow||0,spineLean=castPose?.spineLean||0;
 // Short action clips are triggered by actual successful pickup/crafting events.
 // Smooth envelope avoids snapping in/out of the existing movement pose.
 let collect=0,crafting=0;
 if(actionFx){const q=clamp(actionFx.time/1.25,0,1),env=Math.sin(Math.PI*q);collect=actionFx.kind==='collect'?env:0;crafting=actionFx.kind==='craft'?env:0;}
 const rotation=(rx=0,ry=0,rz=0)=>model(0,0,0,1,1,1,ry,rx,rz);
 const pose={
  Hips:rotation(0,walking?Math.sin(realClock*10)*.045:0,0),
  Spine:rotation(breathe+spineLean+.21*collect+.09*crafting,0,walking?Math.sin(realClock*10)*.04:0),
  Head:rotation(Math.sin(realClock*1.2)*.03),
  L_Hip:rotation(stride),R_Hip:rotation(-stride),
  L_Knee:rotation(Math.max(0,-stride)*.45),R_Knee:rotation(Math.max(0,stride)*.45),
  L_Shoulder:rotation(-swing-.06+.75*collect+.62*crafting,0,-.08),
  R_Shoulder:rotation(swing+throwArm+.62*crafting,0,.08),
  L_Elbow:rotation(-.18-.35*collect-.72*crafting),R_Elbow:rotation(-.22+throwElbow-.63*crafting),
  R_Wrist:rotation(-.08+.15*collect+Math.sin(realClock*16)*.12*crafting),L_Wrist:rotation(-.15*collect-.08*crafting)
 };
 const parent=model(x,dy,z,1,1,1,yaw);
 let handWorld=null;
 gl.disable(gl.CULL_FACE);
 for(const p of parts){
   const palette=window.RaftGLB.skinPalette(p,pose);
   const posed=palette?window.RaftGLB.posedTransform(p,{}):window.RaftGLB.posedTransform(p,pose);
   renderMesh(p.mesh,p.color,mul(parent,posed),0,0,palette,p.roughness,p.metallic);
   if(!handWorld){
     const grip=window.RaftGLB.findJointTransform(p,'R_Wrist',pose);
     if(grip)handWorld=mul(parent,grip);
   }
 }
 gl.enable(gl.CULL_FACE);
 if(handWorld && (!netFx || window.RaftCastMotion.state(netFx.time).visibleInHand)){
  // Attach equipment to actual wrist joint (not an approximated world offset).
  const grip=mul(handWorld,model(0,-.06,-.09,.52,.52,.52,0,-.35,-.23));
  const net=visualMode==='glb'?ASSETS.net:null;
  if(net)for(const p of net)renderMesh(p.mesh,p.color,mul(grip,p.transform),0,/wood/i.test(p.materialName||'')?1:0,null,p.roughness,p.metallic);
 }
 return true;
}
function player(){
 const x=game.player.x,z=game.player.z;
 const dy=Math.sin(realClock*1.1)*.075;
 const walking=Object.values(keys).some(Boolean);
 const step=walking?Math.sin(realClock*12)*.26:0;
 const yaw=cameraYaw;
 if(animatedSurvivor(x,dy,z,yaw,walking))return;
 // Retain legacy player fallback for machines without the GLB asset.
 draw('cyl',C.pants,x-.16,.64+dy,z,.17,.71,.17,yaw,0,step);
 draw('cyl',C.pants,x+.16,.64+dy,z,.17,.71,.17,yaw,0,-step);
 draw('box',C.dark,x-.16,.27+dy,z,.4,.15,.59,yaw);
 draw('box',C.dark,x+.16,.27+dy,z,.4,.15,.59,yaw);
 draw('cyl',C.shirt,x,1.26+dy,z,.47,.94,.35,yaw);
 draw('box',C.wood,x,1.29+dy,z+.29,.68,.77,.3,yaw);
 draw('sphere',C.skin,x,1.99+dy,z,.35,.38,.35);
 draw('sphere',C.dark,x,2.25+dy,z-.03,.40,.13,.38);
 draw('cyl',C.skin,x-.55,1.37+dy,z,.15,.7,.15,yaw,0,.15);
 draw('cyl',C.skin,x+.54,1.37+dy,z,.15,.7,.15,yaw,0,-.29);
 if(!drawAsset('net',x+.56,1.1+dy,z-.19,.85,.85,.85,-cameraYaw,.6,0))
  segment(C.wood,[x+.58,1.2+dy,z],[x+.58,2.5+dy,z],.065);
}
function shark(){let x=Math.sin(sharkAngle)*sharkDist,z=Math.cos(sharkAngle)*sharkDist,ang=Math.atan2(Math.sin(sharkAngle),Math.cos(sharkAngle));draw('sphere',C.fin,x,-.05,z,1.35,.44,.56,ang);draw('cone',C.fin,x-.0,.43,z,.23,.9,.23,ang,0,Math.PI);draw('cone',C.fin,x-.3,-.05,z-.85,.39,.64,.3,ang,Math.PI/2);}
function effects(){
 if(aim&&running&&!paused){let y=.35+Math.sin(realClock*2)*.12;draw('torus',C.yellow,aim.x,y,aim.z,.53,.04,.53,realClock*.5,0,0,1)}
 if(netFx){
  const cast=window.RaftCastMotion.state(netFx.time);
  if(!cast.visibleInHand && cast.phase!=='done'){
   const flight=window.RaftCastMotion.flight(netFx.time,netFx.from,netFx.to);
   // A06: rope and tool follow precisely the same evaluated flight state.
   const hand=[netFx.from.x+.45,1.45,netFx.from.z];
   const x=flight.x,z=flight.z,y=flight.y;
   if(!drawAsset('net',x,y-.48,z,.76,.76,.76,realClock,.76))draw('torus',C.rope,x,y,z,.48,.4,.48,0,Math.PI*.12,0,1);
   segment(C.rope,hand,[x,y,z],.026);
  }
 }
}
function atmosphere(){for(let i=0;i<14;i++){let a=i*2.4,px=Math.sin(a)*125,pz=Math.cos(a)*125,py=19+Math.sin(i)*9;draw('sphere',C.white,px,py,pz,15,2.1,5,0,0,0,1);draw('sphere',C.white,px+9,py+1,pz,9,2.8,4,0,0,0,1)}draw('sphere',C.yellow,-100,85,-135,12,12,12,0,0,0,1)}
function render(){perfDrawCalls=0;perfTriangles=0;resize();const skyMix=Math.sin((elapsed/200%1)*Math.PI*2)*.12,f=clamp(skyMix,-.1,.1);fog=[.67+f*.2,.84+f*.3,.86+f*.1];gl.clearColor(.63+f*.2,.82+f*.2,.85+f*.2,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.enable(gl.CULL_FACE);gl.cullFace(gl.BACK);
 const pos=game.player||{x:0,z:0},cx=pos.x+Math.sin(cameraYaw)*Math.cos(cameraPitch)*cameraDistance,cz=pos.z+Math.cos(cameraYaw)*Math.cos(cameraPitch)*cameraDistance,cy=2.2+Math.sin(cameraPitch)*cameraDistance;eye=[cx,cy,cz];const proj=perspective(Math.PI/3.25,canvas.width/canvas.height,.12,600);vp=mul(proj,look(eye,[pos.x,1.2,pos.z]));
 gl.useProgram(seaP);gl.uniformMatrix4fv(seaU.mvp,false,new Float32Array(vp));gl.uniform1f(seaU.time,realClock);gl.uniform3fv(seaU.eye,eye);gl.uniform3fv(seaU.fog,fog);gl.bindVertexArray(M.sea.vao);gl.drawElements(gl.TRIANGLES,M.sea.count,gl.UNSIGNED_INT,0);perfDrawCalls++;perfTriangles+=M.sea.count/3;
 gl.useProgram(mainP);gl.uniform3fv(mainU.eye,eye);gl.uniform3fv(mainU.fog,fog);gl.uniform3fv(mainU.light,[-.5,.95,.4]);
 if(woodMapsReady)for(let i=0;i<3;i++){gl.activeTexture(gl.TEXTURE0+i);gl.bindTexture(gl.TEXTURE_2D,woodTextures[i]);}
 gl.uniform1i(mainU.woodColor,0);gl.uniform1i(mainU.woodRough,1);gl.uniform1i(mainU.woodNormal,2);
 atmosphere();if(game.tiles)for(let [x,z] of game.tiles)tile(x,z);if(game.buildings)for(let b of game.buildings)objectPart(b.id,(b.x+.5)*TILE,(b.z+.5)*TILE);for(let d of debris)floatingDebris(d);if(game.tiles)player();shark();effects();gl.bindVertexArray(null);
 if(screenshotRequested){screenshotRequested=false;canvas.toBlob(blob=>{if(!blob){tip('Không thể lưu ảnh trong trình duyệt này.');return}const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='RAFTBOUND_A08_'+Date.now()+'.png';a.click();setTimeout(()=>URL.revokeObjectURL(url),5000)},'image/png');}
}
function loop(now){let dt=clamp((now-lastFrame)/1000,0,.06);lastFrame=now;realClock+=dt;if(running&&!paused)simulate(dt);if(noticeTimer>0){noticeTimer-=dt;if(noticeTimer<=0)$('#notice').classList.remove('show')}render();
 perfFrames++;if(now-perfLast>500){perfFPS=Math.round(perfFrames*1000/(now-perfLast));perfLast=now;perfFrames=0;}
 if(perfVisible)$('#perfOverlay').textContent=`FPS ${perfFPS} · ${canvas.width}×${canvas.height}\nRender ${Math.round(renderScale*100)}% (F4) · Draw calls ${perfDrawCalls} · Triangles ${Math.round(perfTriangles).toLocaleString()}\nHero batches: ${ASSETS.survivor?.length??0} · GLB: ${Object.keys(ASSETS).length}/11\nF3: đóng bảng này`;
 requestAnimationFrame(loop)}
$('#startBtn').addEventListener('click',()=>start(false));$('#loadBtn').addEventListener('click',()=>{if(localStorage.getItem('raftbound.save.v1'))start(true);else tip('Chưa có ván đã lưu — hãy bắt đầu trò chơi mới.')});$('#pauseBtn').addEventListener('click',()=>togglePause());$('#resumeBtn').addEventListener('click',()=>togglePause(false));$('#restartBtn').addEventListener('click',()=>{if(confirm('Bắt đầu lại sẽ thay thế dữ liệu đã lưu. Bạn chắc chắn?')){newGame();elapsed=0;paused=false;$('#pauseOverlay').classList.add('hidden');save()}});$('#netBtn').addEventListener('click',cast);$('#craftBtn').addEventListener('click',()=>toggleCraft());$('#closeCraft').addEventListener('click',()=>toggleCraft(false));$('#eatBtn').addEventListener('click',()=>consume('eat'));$('#drinkBtn').addEventListener('click',()=>consume('drink'));
$('#assetStatus').addEventListener('click',()=>{if(!Object.keys(ASSETS).length)return;visualMode=visualMode==='glb'?'legacy':'glb';setAssetStatus(visualMode==='glb'?'Đang hiển thị GLB · Nhấn G để so sánh':'Hình học cũ · Nhấn G để xem GLB');});
const control=['w','a','s','d'];window.addEventListener('keydown',e=>{let k=e.key.toLowerCase();if(control.includes(k))keys[k]=true;if([' ','arrowup','arrowdown','arrowleft','arrowright'].includes(k))e.preventDefault();if(e.repeat)return;if(k===' '){cast()}if(k==='q')toggleCraft();if(k==='g')$('#assetStatus').click();if(k==='v')cycleCamera();if(k==='f3'){e.preventDefault();perfVisible=!perfVisible;$('#perfOverlay').classList.toggle('hidden',!perfVisible)}if(k==='f4'){e.preventDefault();renderScale=renderScale===1?.9:renderScale===.9?.7:1;tip('Độ phân giải render: '+Math.round(renderScale*100)+'%')}if(k==='p'){screenshotRequested=true;tip('Đang lưu ảnh chụp game…')}if(k==='1')consume('eat');if(k==='2')consume('drink');if(k==='escape'){if($('#craftPanel').classList.contains('open'))toggleCraft(false);else togglePause()}});window.addEventListener('keyup',e=>{keys[e.key.toLowerCase()]=false});window.addEventListener('blur',()=>{keys={}});
function cycleCamera(){
 cameraPreset=(cameraPreset+1)%3;
 const modes=[{name:'TOÀN CẢNH',pitch:.42,distance:11},{name:'CẬN NHÂN VẬT',pitch:.32,distance:6.2},{name:'TỪ TRÊN XUỐNG',pitch:.94,distance:12.5}];
 const mode=modes[cameraPreset];cameraPitch=mode.pitch;cameraDistance=mode.distance;tip('Camera: '+mode.name+' · Cuộn chuột để zoom');
}
canvas.addEventListener('wheel',e=>{if(!running||paused)return;e.preventDefault();cameraDistance=clamp(cameraDistance+Math.sign(e.deltaY)*.85,4.5,19)},{passive:false});
canvas.addEventListener('contextmenu',e=>e.preventDefault());canvas.addEventListener('pointerdown',e=>{if(!running||paused)return;if(e.button===2){mouseDown=true;canvas.setPointerCapture(e.pointerId)}else if(e.button===0){cast()}});canvas.addEventListener('pointerup',e=>{if(e.button===2)mouseDown=false});canvas.addEventListener('pointermove',e=>{if(mouseDown){cameraYaw-=e.movementX*.006;cameraPitch=clamp(cameraPitch-e.movementY*.004,.2,.95)}});
for(let b of document.querySelectorAll('[data-move]')){let k=b.dataset.move;b.addEventListener('pointerdown',e=>{e.preventDefault();keys[k]=true;b.setPointerCapture(e.pointerId)});b.addEventListener('pointerup',()=>keys[k]=false);b.addEventListener('pointercancel',()=>keys[k]=false)}
canvas.addEventListener('touchstart',e=>{if(e.touches.length===2){const t=e.touches[0],u=e.touches[1];canvas._touchX=(t.clientX+u.clientX)/2;canvas._touchY=(t.clientY+u.clientY)/2}}, {passive:true});canvas.addEventListener('touchmove',e=>{if(e.touches.length===2){e.preventDefault();const t=e.touches[0],u=e.touches[1],x=(t.clientX+u.clientX)/2,y=(t.clientY+u.clientY)/2;if(canvas._touchX!=null){cameraYaw-=(x-canvas._touchX)*.007;cameraPitch=clamp(cameraPitch-(y-canvas._touchY)*.005,.2,.95)}canvas._touchX=x;canvas._touchY=y}},{passive:false});
window.addEventListener('beforeunload',save);newGame();$('#loadBtn').disabled=!localStorage.getItem('raftbound.save.v1');requestAnimationFrame(loop);
})();
