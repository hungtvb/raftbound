import { World } from './world';
import { castMotion, rules } from './legacy';
import { defs, freshGame, quests, recipes, SAVE_KEY, TILE_SIZE } from './config';
import type { ItemId, RecipeId, Salvage, SaveGame, XY } from './types';

const $=<T extends HTMLElement>(selector:string)=>{
  const element=document.querySelector<T>(selector);if(!element)throw new Error(`Missing UI element: ${selector}`);
  return element;
};
const clamp=(v:number,a:number,b:number)=>Math.max(a,Math.min(b,v));
const rnd=(min:number,max:number)=>Math.random()*(max-min)+min;
const salvageTypes:ItemId[]=['wood','wood','wood','plastic','plastic','leaf','leaf','metal','seed','fish'];

export class SurvivalGame {
  readonly world:World;
  readonly keys=new Set<string>();
  state:SaveGame=freshGame();
  salvage:Salvage[]=[];
  castFx:{time:number;from:XY;to:XY;target:Salvage|null;caught:boolean}|null=null;
  running=false;paused=false;elapsed=0;noticeUntil=0;spawnTimer=0;sharkTimer=0;saveTimer=0;uiTimer=0;
  last=performance.now();moveActive=false;perfVisible=false;frames=0;perfAt=performance.now();fps=0;

  constructor(canvas:HTMLCanvasElement){this.world=new World(canvas);this.bind();this.reset();requestAnimationFrame(t=>this.loop(t));}
  async initialize():Promise<void>{
    const status=$<HTMLButtonElement>('#assetStatus');
    await Promise.all([
      this.world.startPhysics(),
      this.world.loadAssets((loaded,total)=>{status.textContent=`THREE.JS · ${loaded}/${total} GLB`;})
    ]);
    this.world.mountNet();
    status.textContent=`THREE.JS + RAPIER · ${this.world.info.loaded}/${this.world.info.total} GLB`;
    this.world.sync(this.state,this.salvage);
    $('#loadBtn').toggleAttribute('disabled',!localStorage.getItem(SAVE_KEY));
  }
  reset():void {
    this.state=freshGame();this.elapsed=0;this.castFx=null;this.salvage=[];this.spawnTimer=0;this.sharkTimer=0;
    for(let i=0;i<28;i++)this.spawn(true);
    this.updateUI();
  }
  start(fromSave:boolean):void{
    if(!fromSave||!this.restore())this.reset();
    this.running=true;this.paused=false;
    $('#startOverlay').classList.add('hidden');$('#pauseOverlay').classList.add('hidden');
    this.message('WASD để di chuyển · SPACE để quăng vợt · Q để chế tạo');
  }
  restore():boolean{
    try{
      const raw=localStorage.getItem(SAVE_KEY);if(!raw)return false;
      const payload=rules.readSave(JSON.parse(raw));if(!payload)return false;
      this.state=payload.game;this.elapsed=payload.elapsed;this.salvage=[];this.castFx=null;
      for(let i=0;i<28;i++)this.spawn(true);
      this.updateUI();return true;
    }catch(e){console.warn('[RAFTBOUND] Save rejected',e);return false;}
  }
  save():void{
    if(!this.running)return;
    try{localStorage.setItem(SAVE_KEY,JSON.stringify({version:1,game:this.state,elapsed:this.elapsed}));}
    catch(e){console.warn('[RAFTBOUND] Unable to save',e);}
  }
  pause(force?:boolean):void{
    if(!this.running)return;
    this.paused=force??!this.paused;
    $('#pauseOverlay').classList.toggle('hidden',!this.paused);
    if(this.paused)this.save();
  }
  toggleCraft(force?:boolean):void{
    if(!this.running||this.paused)return;
    const panel=$('#craftPanel'),active=force??!panel.classList.contains('open');
    panel.classList.toggle('open',active);if(active)this.renderRecipes();
  }
  message(text:string):void{
    const el=$('#notice');el.textContent=text;el.classList.add('show');this.noticeUntil=performance.now()+2600;
  }
  spawn(initial=false):void{
    if(this.salvage.length>=60)return;
    this.salvage.push({type:salvageTypes[Math.floor(Math.random()*salvageTypes.length)],
      x:rnd(-11,11),z:initial?rnd(-27,17):rnd(-42,-30),speed:rnd(.35,.82),phase:rnd(0,6.28),sway:rnd(0,6.28)});
  }
  cast():void{
    if(!this.running||this.paused||this.castFx)return;
    const target=rules.selectDebris(this.salvage,this.state.player,this.world.yaw);
    const from={...this.state.player};
    const to=target?{x:target.x,z:target.z}:{x:from.x-Math.sin(this.world.yaw)*8,z:from.z-Math.cos(this.world.yaw)*8};
    this.castFx={time:0,from,to,target,caught:false};
  }
  craft(id:RecipeId):void{
    const recipe=recipes.find(r=>r.id===id);if(!recipe)return;
    const g=this.state;
    if(!Object.entries(recipe.cost).every(([k,n])=>g.inv[k as ItemId]>=(n??0))){this.message('Chưa đủ nguyên liệu.');return;}
    if(id==='spear'&&g.hasSpear){this.message('Đã trang bị giáo.');return;}
    const occupied=new Set(g.buildings.map(b=>`${b.x},${b.z}`));
    const free=g.tiles.filter(([x,z])=>!occupied.has(`${x},${z}`)).sort((a,b)=>Math.hypot(...a)-Math.hypot(...b))[0];
    const newTile=id==='raft'?rules.expandRaft(g.tiles,this.world.yaw):null;
    if(id==='raft'&&!newTile){this.message('Không thể mở rộng bè thêm.');return;}
    if(id!=='raft'&&id!=='spear'&&!free){this.message('Bè hết chỗ, hãy mở rộng trước.');return;}
    for(const [k,n] of Object.entries(recipe.cost))g.inv[k as ItemId]-=n??0;
    if(id==='raft'&&newTile)g.tiles.push(newTile);
    else if(id==='spear')g.hasSpear=true;
    else if(free&&id!=='raft')g.buildings.push({id,x:free[0],z:free[1]});
    g.crafts++;this.checkQuests();this.renderRecipes();this.updateUI();this.save();
    this.message(`Đã chế tạo: ${recipe.title}`);
  }
  consume(type:'eat'|'drink'):void{
    const id=type==='eat'?'meal':'fresh';
    if(this.state.inv[id]===0){this.message(type==='eat'?'Chưa có đồ ăn.':'Chưa có nước sạch.');return;}
    this.state.inv[id]--;
    if(type==='eat')this.state.food=clamp(this.state.food+29,0,100);
    else this.state.water=clamp(this.state.water+37,0,100);
    this.updateUI();this.save();this.message(type==='eat'?'Đã ăn · +29 độ no':'Đã uống · +37 nước');
  }
  private checkQuests():void{
    const g=this.state;let next=g.quest;
    while(next<quests.length&&quests[next].progress(g)>=quests[next].need)next++;
    if(next!==g.quest){g.quest=next;this.message(next===quests.length?'Đã hoàn thành mục tiêu sinh tồn!':'Nhiệm vụ mới đã mở!');}
  }
  private simulate(dt:number):void{
    const g=this.state;this.elapsed+=dt;g.seconds+=dt;g.day=1+Math.floor(this.elapsed/200);
    g.food=clamp(g.food-dt*.087,0,100);g.water=clamp(g.water-dt*.115,0,100);
    g.hp=clamp(g.hp+((g.food===0||g.water===0)?-2.1:.022)*dt,0,100);
    if(g.hp===0){g.hp=35;g.food=25;g.water=25;this.message('Bạn kiệt sức và được sóng đưa về bè.');}
    let mx=Number(this.keys.has('KeyD'))-Number(this.keys.has('KeyA'));
    let mz=Number(this.keys.has('KeyS'))-Number(this.keys.has('KeyW'));
    const len=Math.hypot(mx,mz);this.moveActive=len>0;
    if(len){mx/=len;mz/=len;
      const sin=Math.sin(this.world.yaw),cos=Math.cos(this.world.yaw);
      const dx=mx*cos+mz*sin,dz=-mx*sin+mz*cos;
      this.world.heading=Math.atan2(-dx,-dz);
      const x=g.player.x+dx*3.7*dt,z=g.player.z+dz*3.7*dt;
      if(rules.onRaft(x,z,g.tiles,TILE_SIZE)){g.player.x=x;g.player.z=z;}
    }
    for(const d of this.salvage){d.z+=d.speed*dt;d.x+=Math.sin(this.elapsed*.23+d.sway)*dt*.12;
      if(d.z>35){d.z=-38;d.x=rnd(-12,12);}
    }
    this.spawnTimer+=dt;if(this.spawnTimer>1.8){this.spawnTimer=0;this.spawn();}
    if(this.castFx){const fx=this.castFx;fx.time+=dt;
      if(fx.time>=castMotion.CAST.contact&&!fx.caught){fx.caught=true;
        if(rules.castHit(fx.target,fx.from,fx.to,this.salvage)){
          const found=this.salvage.indexOf(fx.target!);
          if(found>=0){this.salvage.splice(found,1);g.inv[fx.target!.type]++;g.collected++;
            this.message(`+1 ${defs[fx.target!.type].icon} ${defs[fx.target!.type].name}`);this.checkQuests();}
        }else this.message('Vợt không bắt trúng vật phẩm nào.');
      }
      if(fx.time>=castMotion.CAST.end)this.castFx=null;
    }
    if(g.buildings.some(b=>b.id==='purifier')){g.waterTimer+=dt;if(g.waterTimer>20){g.waterTimer=0;g.inv.fresh++;this.message('Máy lọc nước: +1 nước sạch');}}
    if(g.buildings.some(b=>b.id==='grill')&&g.inv.fish>0){g.cookTimer+=dt;if(g.cookTimer>11){g.cookTimer=0;g.inv.fish--;g.inv.meal++;this.message('Bếp nướng: +1 thức ăn');}}
    if(g.buildings.some(b=>b.id==='planter')){g.growTimer+=dt;if(g.growTimer>35){g.growTimer=0;g.inv.meal++;this.message('Đã thu hoạch: +1 thức ăn');}}
    this.sharkTimer+=dt;if(this.sharkTimer>58){this.sharkTimer=0;g.sharkHits++;g.hp=clamp(g.hp-(g.hasSpear?3:13),0,100);this.message(g.hasSpear?'Giáo đã đẩy lùi cá mập!':'Cá mập tấn công!');}
    this.uiTimer+=dt;this.saveTimer+=dt;
    if(this.uiTimer>.2){this.uiTimer=0;this.updateUI();}
    if(this.saveTimer>10){this.saveTimer=0;this.save();}
    this.checkQuests();
  }
  private updateUI():void{
    const g=this.state;
    for(const [id,value] of [['hp',g.hp],['food',g.food],['water',g.water]] as const){
      $(`#${id}Val`).textContent=String(Math.ceil(value));$<HTMLElement>(`#${id}Bar`).style.width=`${value}%`;
    }
    $('#dayInfo').textContent=`☀ NGÀY ${String(g.day).padStart(2,'0')}`;
    $('#waveInfo').textContent=g.hasSpear?'CÓ PHÒNG THỦ':'BIỂN ÊM';
    const quest=quests[g.quest];$('#questTitle').textContent=quest?.name??'CHINH PHỤC ĐẠI DƯƠNG';
    $('#questDesc').textContent=quest?.desc??'Tiếp tục phát triển chiếc bè của bạn!';
    $<HTMLElement>('#questProgress').style.width=`${quest?100*quest.progress(g)/quest.need:100}%`;
    const keys=Object.keys(defs) as ItemId[];
    $('#inventory').innerHTML=keys.map(k=>`<div class="inv-item"><span class="num">${g.inv[k]}</span><span class="emoji">${defs[k].icon}</span><span class="inv-label">${defs[k].name}</span></div>`).join('');
    const target=rules.selectDebris(this.salvage,g.player,this.world.yaw);
    $('#aimText').textContent=target?`${defs[target.type].icon} ${defs[target.type].name} · SPACE để thu gom`:'Quay camera về phía vật phẩm trôi để dùng vợt';
  }
  private renderRecipes():void{
    const g=this.state;
    $('#craftRecipes').innerHTML=['XÂY DỰNG','THIẾT BỊ SINH TỒN','TRỒNG TRỌT','CÔNG CỤ'].map(category=>
      `<div class="section-title">${category}</div>`+
      recipes.filter(r=>r.category===category).map(r=>{
        const can=Object.entries(r.cost).every(([id,n])=>g.inv[id as ItemId]>=(n??0));
        const cost=Object.entries(r.cost).map(([id,n])=>`${defs[id as ItemId].icon} ${n}`).join(' · ');
        return `<div class="recipe"><div class="recipe-copy"><strong>${r.icon} ${r.title}</strong><p>${r.desc}</p><div class="cost">${cost}</div></div><button data-craft="${r.id}" ${can?'':'disabled'}>${can?'CHẾ TẠO':'THIẾU ĐỒ'}</button></div>`;
      }).join('')).join('');
    $('#craftRecipes').querySelectorAll<HTMLButtonElement>('[data-craft]').forEach(b=>b.addEventListener('click',()=>this.craft(b.dataset.craft as RecipeId)));
  }
  private loop(now:number):void{
    const dt=Math.min(.05,Math.max(0,(now-this.last)/1000));this.last=now;
    if(this.running&&!this.paused)this.simulate(dt);
    this.world.sync(this.state,this.salvage);
    this.world.update(dt,this.elapsed,this.state,this.salvage,this.castFx,this.moveActive);
    if(this.perfVisible){this.frames++;if(now-this.perfAt>=1000){this.fps=Math.round(this.frames*1000/(now-this.perfAt));this.frames=0;this.perfAt=now;}
      $('#perfOverlay').textContent=`Three.js + Rapier\nFPS: ${this.fps}\nDraw calls: ${this.world.renderer.info.render.calls}\nTriangles: ${this.world.renderer.info.render.triangles}\nAssets: ${this.world.info.loaded}/${this.world.info.total}`;
    }
    if(now>this.noticeUntil)$('#notice').classList.remove('show');
    requestAnimationFrame(t=>this.loop(t));
  }
  private bind():void{
    $('#startBtn').addEventListener('click',()=>this.start(false));
    $('#loadBtn').addEventListener('click',()=>this.start(true));
    $('#pauseBtn').addEventListener('click',()=>this.pause());
    $('#resumeBtn').addEventListener('click',()=>this.pause(false));
    $('#restartBtn').addEventListener('click',()=>{this.reset();this.pause(false);this.message('Đã bắt đầu lại từ ngày đầu tiên.');});
    $('#netBtn').addEventListener('click',()=>this.cast());
    $('#craftBtn').addEventListener('click',()=>this.toggleCraft());
    $('#closeCraft').addEventListener('click',()=>this.toggleCraft(false));
    $('#eatBtn').addEventListener('click',()=>this.consume('eat'));
    $('#drinkBtn').addEventListener('click',()=>this.consume('drink'));
    addEventListener('keydown',e=>{
      if(['Space','ArrowUp','ArrowDown'].includes(e.code))e.preventDefault();
      this.keys.add(e.code);if(e.repeat)return;
      if(e.code==='Space')this.cast();if(e.code==='KeyQ')this.toggleCraft();
      if(e.code==='Digit1')this.consume('eat');if(e.code==='Digit2')this.consume('drink');
      if(e.code==='Escape')this.pause();if(e.code==='KeyV')this.world.setPreset();
      if(e.code==='KeyP')this.world.screenshot();
      if(e.code==='F3'){this.perfVisible=!this.perfVisible;$('#perfOverlay').classList.toggle('hidden',!this.perfVisible);}
      if(e.code==='F4'){const q=this.world.quality;this.world.setQuality(q===1?.7:q===.7?.9:1);this.message(`Độ phân giải: ${Math.round(this.world.quality*100)}%`);}
    });
    addEventListener('keyup',e=>this.keys.delete(e.code));
    addEventListener('blur',()=>this.keys.clear());
    addEventListener('beforeunload',()=>this.save());
    const canvas=this.world.canvas;let drag=false;
    canvas.addEventListener('contextmenu',e=>e.preventDefault());
    canvas.addEventListener('pointerdown',e=>{if(e.button===2){drag=true;canvas.setPointerCapture(e.pointerId);}else if(e.button===0)this.cast();});
    canvas.addEventListener('pointerup',()=>{drag=false;});
    canvas.addEventListener('pointermove',e=>{if(drag)this.world.orbit(e.movementX,e.movementY);});
    canvas.addEventListener('wheel',e=>{e.preventDefault();this.world.zoom(e.deltaY);},{passive:false});
    document.querySelectorAll<HTMLButtonElement>('[data-move]').forEach(b=>{
      const code=`Key${b.dataset.move!.toUpperCase()}`;
      b.addEventListener('pointerdown',e=>{e.preventDefault();this.keys.add(code);b.setPointerCapture(e.pointerId);});
      b.addEventListener('pointerup',()=>this.keys.delete(code));
      b.addEventListener('pointercancel',()=>this.keys.delete(code));
    });
  }
}
