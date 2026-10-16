import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { clone as cloneSkin } from 'three/addons/utils/SkeletonUtils.js';
import RAPIER from '@dimforge/rapier3d-compat';
import { castMotion } from './legacy';
import { TILE_SIZE } from './config';
import type { SaveGame, Salvage, XY } from './types';

const MODELS = {
  foundation:'foundation_2m', net:'salvage_net_tool', survivor:'survivor_sailor_skinned',
  wood:'driftwood_plank', plastic:'plastic_bottle', leaf:'palm_leaf',
  metal:'salvage_barrel', seed:'palm_leaf', fish:'plastic_bottle',
  purifier:'solar_purifier', grill:'compact_grill', planter:'planter_box', storage:'storage_chest'
} as const;
type ModelId = keyof typeof MODELS;
const clamp=(v:number,a:number,b:number)=>Math.max(a,Math.min(b,v));
function fallback(name:ModelId):THREE.Group {
  const root=new THREE.Group();
  const mat=new THREE.MeshStandardMaterial({color:name==='foundation'?0x94704e:name==='survivor'?0xe0b787:name==='leaf'?0x6c9b55:0xd1b57c,roughness:.89});
  const mesh=new THREE.Mesh(new THREE.BoxGeometry(name==='foundation'?1.96:.65,name==='foundation'?.25:.7,name==='foundation'?1.96:.65),mat);
  mesh.castShadow=true;mesh.receiveShadow=true;mesh.position.y=name==='foundation'?-.12:.4;root.add(mesh);return root;
}

export class World {
  readonly renderer:THREE.WebGLRenderer;
  readonly scene=new THREE.Scene();
  readonly camera=new THREE.PerspectiveCamera(57,1,.1,420);
  readonly template=new Map<ModelId,THREE.Object3D>();
  readonly tiles=new Map<string,THREE.Object3D>();
  readonly buildings=new Map<string,THREE.Object3D>();
  readonly debris=new Map<Salvage,THREE.Object3D>();
  readonly ocean:THREE.Mesh;
  readonly playerAnchor=new THREE.Group();
  readonly netAnchor=new THREE.Group();
  readonly shark=new THREE.Group();
  readonly catchRope:THREE.Line;
  readonly info={loaded:0,total:Object.keys(MODELS).length,rapier:false};
  physics?:RAPIER.World;
  body?:RAPIER.RigidBody;
  yaw=0;pitch=.47;distance=12;preset=0;quality=.9;
  private waves:{value:number};
  private bones=new Map<string,THREE.Bone>();
  private activeModel?:THREE.Object3D;
  private heldNet?:THREE.Object3D;
  heading=0;
  private colliderKeys=new Set<string>();
  private previousSize={w:0,h:0};

  constructor(readonly canvas:HTMLCanvasElement) {
    this.renderer=new THREE.WebGLRenderer({canvas,antialias:true,powerPreference:'high-performance',alpha:false});
    this.renderer.setPixelRatio(Math.min(devicePixelRatio,2));
    this.renderer.outputColorSpace=THREE.SRGBColorSpace;
    this.renderer.toneMapping=THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure=1.3;
    this.renderer.shadowMap.enabled=true;
    this.renderer.shadowMap.type=THREE.PCFSoftShadowMap;
    this.scene.background=new THREE.Color(0x95cfdb);
    this.scene.fog=new THREE.FogExp2(0x91cbd8,.005);
    const hemi=new THREE.HemisphereLight(0xd0eeff,0x51655f,2.3);this.scene.add(hemi);
    const sun=new THREE.DirectionalLight(0xffe8bc,3.25);
    sun.position.set(-12,26,-17);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);
    sun.shadow.camera.left=-28;sun.shadow.camera.right=28;sun.shadow.camera.top=28;sun.shadow.camera.bottom=-28;
    sun.shadow.normalBias=.035;this.scene.add(sun);
    const seaTime={value:0};this.waves=seaTime;
    const water=new THREE.ShaderMaterial({
      uniforms:{uTime:seaTime,uDeep:{value:new THREE.Color(0x086179)},uShallow:{value:new THREE.Color(0x2abbb8)}},
      vertexShader:`uniform float uTime;varying vec3 vP;varying float vWave;
        void main(){vec3 p=position;float a=sin(p.x*.48+uTime*.91)*.12;float b=cos(p.y*.41-uTime*.7)*.09;
        p.z+=a+b+sin((p.x+p.y)*.8+uTime*1.5)*.045;vWave=p.z;vP=p;
        gl_Position=projectionMatrix*modelViewMatrix*vec4(p,1.);}`,
      fragmentShader:`uniform float uTime;uniform vec3 uDeep;uniform vec3 uShallow;
        varying vec3 vP;varying float vWave;
        void main(){float bands=sin(vP.x*.61+uTime*1.1)*cos(vP.y*.45-uTime*.87);
        float sparkle=pow(max(0.,sin(vP.x*2.7+vP.y*1.2+uTime*1.9)),32.);
        vec3 col=mix(uDeep,uShallow,clamp(.56+vWave*.9+bands*.08,0.,1.));
        col+=vec3(.22,.27,.23)*sparkle*.22;gl_FragColor=vec4(col,1.);}`,
      side:THREE.DoubleSide
    });
    this.ocean=new THREE.Mesh(new THREE.PlaneGeometry(520,520,88,88),water);
    this.ocean.rotation.x=-Math.PI/2;this.ocean.position.y=-.37;this.scene.add(this.ocean);
    this.playerAnchor.position.y=.22;this.scene.add(this.playerAnchor);
    this.netAnchor.visible=false;this.scene.add(this.netAnchor);
    const ropeGeom=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(),new THREE.Vector3()]);
    this.catchRope=new THREE.Line(ropeGeom,new THREE.LineBasicMaterial({color:0xf8e1aa}));
    this.catchRope.visible=false;this.scene.add(this.catchRope);
    const body=new THREE.Mesh(new THREE.ConeGeometry(.6,2.6,4),new THREE.MeshStandardMaterial({color:0x577886,roughness:.55}));
    body.rotation.x=Math.PI/2;body.position.y=-.25;this.shark.add(body);
    const fin=new THREE.Mesh(new THREE.ConeGeometry(.4,.9,3),new THREE.MeshStandardMaterial({color:0x4c6a76}));
    fin.position.y=.18;this.shark.add(fin);this.scene.add(this.shark);
    this.resize();
    window.addEventListener('resize',()=>this.resize());
  }

  async loadAssets(onProgress:(n:number,total:number)=>void):Promise<void>{
    const loader=new GLTFLoader();
    await Promise.all(Object.entries(MODELS).map(async ([key,path])=>{
      try {
        const gltf=await loader.loadAsync(`${import.meta.env.BASE_URL}glb/${path}.glb`);
        gltf.scene.traverse(obj=>{
          if((obj as THREE.Mesh).isMesh){const m=obj as THREE.Mesh;m.castShadow=true;m.receiveShadow=true;}
        });
        this.template.set(key as ModelId,gltf.scene);
        this.info.loaded++;
      } catch(e){console.warn('[RAFTBOUND] Fallback model:',path,e);}
      onProgress(this.info.loaded,this.info.total);
    }));
    this.mountPlayer();
    // Models might finish loading after the first frame created fallback meshes.
    for(const obj of this.tiles.values())obj.removeFromParent();this.tiles.clear();
    for(const obj of this.buildings.values())obj.removeFromParent();this.buildings.clear();
    for(const obj of this.debris.values())obj.removeFromParent();this.debris.clear();
  }

  async startPhysics():Promise<void>{
    try {
      await RAPIER.init();
      this.physics=new RAPIER.World({x:0,y:-9.81,z:0});
      this.body=this.physics.createRigidBody(RAPIER.RigidBodyDesc.kinematicPositionBased().setTranslation(0,1.02,0));
      this.physics.createCollider(RAPIER.ColliderDesc.capsule(.64,.25),this.body);
      this.info.rapier=true;
      for(const key of this.tiles.keys()){const [x,z]=key.split(',').map(Number);this.addCollider(x,z);}
    } catch(e){console.error('[RAFTBOUND] Rapier unavailable; raft rule fallback remains active',e);}
  }

  private instantiate(id:ModelId):THREE.Object3D {
    const base=this.template.get(id);return base?cloneSkin(base):fallback(id);
  }
  private mountPlayer():void{
    this.activeModel?.removeFromParent();this.activeModel=this.instantiate('survivor');
    this.playerAnchor.add(this.activeModel);
    this.bones.clear();this.activeModel.traverse(obj=>{if((obj as THREE.Bone).isBone)this.bones.set(obj.name,obj as THREE.Bone)});
    this.mountHeldNet();
  }
  private buildFoundation(x:number,z:number):void {
    const obj=this.instantiate('foundation');obj.position.set((x+.5)*TILE_SIZE,.05,(z+.5)*TILE_SIZE);
    this.scene.add(obj);this.tiles.set(`${x},${z}`,obj);
    this.addCollider(x,z);
  }

  private addCollider(x:number,z:number):void {
    const key=`${x},${z}`;if(!this.physics||this.colliderKeys.has(key))return;
    const rb=this.physics.createRigidBody(RAPIER.RigidBodyDesc.fixed().setTranslation((x+.5)*2,-.12,(z+.5)*2));
    this.physics.createCollider(RAPIER.ColliderDesc.cuboid(1,.14,1),rb);this.colliderKeys.add(key);
  }

  sync(g:SaveGame,salvage:Salvage[]):void {
    for(const [x,z] of g.tiles){const key=`${x},${z}`;if(!this.tiles.has(key))this.buildFoundation(x,z);}
    for(const [key,obj] of this.tiles){if(!g.tiles.some(([x,z])=>key===`${x},${z}`)){obj.removeFromParent();this.tiles.delete(key);}}
    for(const structure of g.buildings){const key=`${structure.x},${structure.z}`;
      if(!this.buildings.has(key)){
        const obj=this.instantiate(structure.id);obj.position.set((structure.x+.5)*2,.16,(structure.z+.5)*2);
        this.scene.add(obj);this.buildings.set(key,obj);
      }
    }
    for(const [key,obj] of this.buildings){if(!g.buildings.some(b=>key===`${b.x},${b.z}`)){obj.removeFromParent();this.buildings.delete(key);}}
    for(const d of salvage){if(!this.debris.has(d)){
      const id=(d.type in MODELS?d.type:'wood') as ModelId;
      const obj=this.instantiate(id);obj.scale.setScalar(d.type==='metal'?.45:d.type==='fish'?.42:.72);
      this.scene.add(obj);this.debris.set(d,obj);
    }}
    for(const [d,obj] of this.debris){if(!salvage.includes(d)){obj.removeFromParent();this.debris.delete(d);}}
    this.playerAnchor.position.set(g.player.x,.18,g.player.z);
    if(this.body)this.body.setNextKinematicTranslation({x:g.player.x,y:1.02,z:g.player.z});
  }

  resize():void {
    const w=Math.max(1,this.canvas.clientWidth),h=Math.max(1,this.canvas.clientHeight);
    if(w===this.previousSize.w&&h===this.previousSize.h)return;
    this.previousSize={w,h};this.renderer.setSize(w,h,false);this.renderer.setPixelRatio(Math.min(devicePixelRatio,2)*this.quality);
    this.camera.aspect=w/h;this.camera.updateProjectionMatrix();
  }

  setQuality(q:number):void {this.quality=q;this.previousSize={w:0,h:0};this.resize();}
  update(dt:number,elapsed:number,g:SaveGame,salvage:Salvage[],castFx:{time:number;from:XY;to:XY}|null,moving:boolean):void {
    this.waves.value=elapsed;
    const sin=Math.sin(elapsed*.8);
    this.playerAnchor.position.set(g.player.x,.18+(moving?Math.sin(elapsed*12)*.035:Math.sin(elapsed*1.9)*.015),g.player.z);
    this.playerAnchor.rotation.y=this.heading;
    for(const [d,obj] of this.debris){obj.position.set(d.x,-.15+Math.sin(elapsed*1.8+d.phase)*.07,d.z);obj.rotation.y=elapsed*.35+d.sway;}
    this.shark.position.set(g.player.x+Math.cos(elapsed*.18)*15,-.19+sin*.03,g.player.z+Math.sin(elapsed*.18)*15);
    this.shark.rotation.y=-elapsed*.18;
    this.bones.get('L_Hip')?.rotation.set(moving?Math.sin(elapsed*10)*.35:0,0,0);
    this.bones.get('R_Hip')?.rotation.set(moving?-Math.sin(elapsed*10)*.35:0,0,0);
    const pose=castFx?castMotion.state(castFx.time):null;
    const arm=this.bones.get('R_Shoulder');if(arm)arm.rotation.x=pose?.throwArm??(moving?Math.sin(elapsed*10)*.25:0);
    if(this.heldNet)this.heldNet.visible=!castFx||castFx.time<castMotion.CAST.release;
    if(castFx){
      const flight=castMotion.flight(castFx.time,castFx.from,castFx.to);
      this.netAnchor.visible=pose?.phase!=='done'&&pose?.visibleInHand===false;
      this.netAnchor.position.set(flight.x,flight.y,flight.z);
      this.catchRope.visible=this.netAnchor.visible;
      const arr=this.catchRope.geometry.attributes.position as THREE.BufferAttribute;
      arr.setXYZ(0,g.player.x,.95,g.player.z);arr.setXYZ(1,flight.x,flight.y,flight.z);arr.needsUpdate=true;
    } else {this.netAnchor.visible=false;this.catchRope.visible=false;}
    // The tool remains visible in hand outside the flying phase.
    this.camera.position.set(g.player.x+Math.sin(this.yaw)*this.distance*Math.cos(this.pitch),
      Math.sin(this.pitch)*this.distance+1.8,g.player.z+Math.cos(this.yaw)*this.distance*Math.cos(this.pitch));
    this.camera.lookAt(g.player.x,1.0,g.player.z);
    this.physics?.step();
    this.renderer.render(this.scene,this.camera);
  }

  private mountHeldNet():void {
    if(this.heldNet)this.heldNet.removeFromParent();
    this.heldNet=this.instantiate('net');this.heldNet.scale.setScalar(.63);
    this.heldNet.rotation.set(-.35,0,.45);this.heldNet.position.set(.02,-.05,.03);
    (this.bones.get('R_Wrist')??this.playerAnchor).add(this.heldNet);
  }
  mountNet():void{
    while(this.netAnchor.children.length)this.netAnchor.remove(this.netAnchor.children[0]);
    this.netAnchor.add(this.instantiate('net'));
    this.mountHeldNet();
  }
  setPreset():void{
    this.preset=(this.preset+1)%3;
    const presets=[{pitch:.47,distance:12},{pitch:.32,distance:6.5},{pitch:1.12,distance:16}];
    this.pitch=presets[this.preset].pitch;this.distance=presets[this.preset].distance;
  }
  orbit(dx:number,dy:number):void{this.yaw-=dx*.006;this.pitch=clamp(this.pitch-dy*.004,.15,1.32);}
  zoom(delta:number):void{this.distance=clamp(this.distance+Math.sign(delta)*.8,4.5,23);}
  screenshot():void{
    // Screenshot is an explicit user action. Preserve drawing buffer on demand by rendering again.
    this.renderer.render(this.scene,this.camera);
    const a=document.createElement('a');a.download='raftbound-a09.png';a.href=this.canvas.toDataURL('image/png');a.click();
  }
}
