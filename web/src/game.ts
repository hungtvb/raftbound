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
  activeDrawer:'craft'|'bag'|null=null; craftFilter='TẤT CẢ'; pauseTab:'menu'|'settings'|'controls'='menu'; lastInventoryMarkup='';

  constructor(canvas:HTMLCanvasElement){this.world=new World(canvas);this.bind();this.reset();requestAnimationFrame(t=>this.loop(t));}
  async initialize():Promise<void>{
    const status=$<HTMLButtonElement>('#assetStatus');
    await Promise.all([
      this.world.startPhysics(),
      this.world.loadAssets((loaded,total)=>{status.textContent=`THREE.JS · ${loaded}/${total} GLB`;})
    ]);
    this.world.mountNet();
    $('#qualityBtn').textContent=`${Math.round(this.world.quality*100)}% ↻`;
    status.textContent=`THREE.JS ${this.world.info.rapier?'+ RAPIER':'+ PHYSICS DEGRADED'} · ${this.world.info.loaded}/${this.world.info.total} GLB`;
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
    this.running=true;this.paused=false;this.setDrawer(null);
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
    if(this.activeDrawer){this.setDrawer(null);if(force!==true)return;}
    this.paused=force??!this.paused;
    $('#pauseOverlay').classList.toggle('hidden',!this.paused);
    if(this.paused){this.save();this.showPauseTab('menu');$('#pauseDay').textContent=String(this.state.day).padStart(2,'0');$<HTMLButtonElement>('#resumeBtn').focus();}
    else $<HTMLButtonElement>('#pauseBtn').focus();
  }
  private setDrawer(type:'craft'|'bag'|null):void{
    this.activeDrawer=type;
    for(const [id,name] of [['craftPanel','craft'],['bagPanel','bag']] as const){
      const el=$('#'+id),active=type===name;
      el.classList.toggle('open',active);el.setAttribute('aria-hidden',String(!active));
    }
    $('#drawerBackdrop').classList.toggle('hidden',type===null);
    $('#crosshair').classList.toggle('hidden',type!==null);
    $('#aimHint').classList.toggle('hidden',type!==null);
    if(type==='craft'){this.renderFilters();this.renderRecipes();$<HTMLButtonElement>('#closeCraft').focus();}
    else if(type==='bag'){this.renderBag();$<HTMLButtonElement>('#closeBag').focus();}
    else if(this.running&&!this.paused)$<HTMLButtonElement>('#netBtn').focus();
    this.keys.clear();
  }
  toggleCraft(force?:boolean):void{
    if(!this.running||this.paused)return;
    this.setDrawer((force??this.activeDrawer!=='craft')?'craft':null);
  }
  toggleBag(force?:boolean):void{
    if(!this.running||this.paused)return;
    this.setDrawer((force??this.activeDrawer!=='bag')?'bag':null);
  }
  private showPauseTab(tab:'menu'|'settings'|'controls'):void{
    this.pauseTab=tab;
    for(const key of ['menu','settings','controls'] as const){
      $(`#pause${key[0].toUpperCase()+key.slice(1)}`).classList.toggle('hidden',key!==tab);
      const b=$<HTMLButtonElement>(`[data-pause-tab="${key}"]`);b.classList.toggle('active',key===tab);b.setAttribute('aria-selected',String(key===tab));
    }
  }
  private renderFilters():void{
    const filters=['TẤT CẢ',...new Set(recipes.map(r=>r.category))];
    $('#craftFilters').innerHTML=filters.map(category=>`<button type="button" class="${this.craftFilter===category?'active':''}" data-filter="${category}" aria-pressed="${this.craftFilter===category}">${category}</button>`).join('');
    $('#craftFilters').querySelectorAll<HTMLButtonElement>('[data-filter]').forEach(b=>b.addEventListener('click',()=>{
      this.craftFilter=b.dataset.filter!;this.renderFilters();this.renderRecipes();
    }));
  }
  private renderBag():void{
    const items=Object.keys(defs) as ItemId[];
    $('#bagTotal').textContent=`${items.reduce((sum,k)=>sum+this.state.inv[k],0)} vật phẩm`;
    $('#bagGrid').innerHTML=items.map(k=>{
      const usable=k==='meal'||k==='fresh';const count=this.state.inv[k];
      return `<${usable?'button type="button"':'div'} class="bag-item ${count===0?'empty':''} ${usable?'usable':''}" ${usable?`data-consume="${k==='meal'?'eat':'drink'}"`:''} aria-label="${defs[k].name}: ${count}${usable?', nhấn để sử dụng':''}"><span class="count">${count}</span><span class="emoji" aria-hidden="true">${defs[k].icon}</span><strong>${defs[k].name}</strong></${usable?'button':'div'}>`;
    }).join('');
    $('#bagGrid').querySelectorAll<HTMLButtonElement>('[data-consume]').forEach(b=>b.addEventListener('click',()=>this.consume(b.dataset.consume as 'eat'|'drink')));
  }
  message(text:string):void{
    const el=$('#notice');el.textContent=text;el.classList.add('show');el.classList.toggle('danger',/không|thiếu|cá mập|kiệt sức|chưa/i.test(text));this.noticeUntil=performance.now()+2800;
  }
  spawn(initial=false):void{
    if(this.salvage.length>=60)return;
    this.salvage.push({type:salvageTypes[Math.floor(Math.random()*salvageTypes.length)],
      x:rnd(-11,11),z:initial?rnd(-27,17):rnd(-42,-30),speed:rnd(.35,.82),phase:rnd(0,6.28),sway:rnd(0,6.28)});
  }
  cast():void{
    if(!this.running||this.paused||this.activeDrawer||this.castFx)return;
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
    g.crafts++;this.checkQuests();if(this.activeDrawer==='craft')this.renderRecipes();this.updateUI();this.save();
    this.message(`Đã chế tạo: ${recipe.title}`);
  }
  consume(type:'eat'|'drink'):void{
    const id=type==='eat'?'meal':'fresh';
    if(this.state.inv[id]===0){this.message(type==='eat'?'Chưa có đồ ăn.':'Chưa có nước sạch.');return;}
    this.state.inv[id]--;
    if(type==='eat')this.state.food=clamp(this.state.food+29,0,100);
    else this.state.water=clamp(this.state.water+37,0,100);
    this.updateUI();if(this.activeDrawer==='bag')this.renderBag();if(this.activeDrawer==='craft')this.renderRecipes();this.save();this.message(type==='eat'?'Đã ăn · +29 độ no':'Đã uống · +37 nước');
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
    $('#dayInfo').textContent=`NGÀY ${String(g.day).padStart(2,'0')}`;
    $<HTMLElement>('#stats').querySelectorAll('.vital').forEach((e,i)=>e.classList.toggle('low',[g.hp,g.food,g.water][i]<25));
    $('#waveInfo').textContent=g.hasSpear?'CÓ PHÒNG THỦ':'BIỂN ÊM';
    const quest=quests[g.quest];$('#questTitle').textContent=quest?.name??'CHINH PHỤC ĐẠI DƯƠNG';
    $('#questDesc').textContent=quest?.desc??'Tiếp tục phát triển chiếc bè của bạn!';
    $<HTMLElement>('#questProgress').style.width=`${quest?Math.min(100,100*quest.progress(g)/quest.need):100}%`;
    $('#questCount').textContent=quest?`${Math.min(quest.need,quest.progress(g))} / ${quest.need}`:'✓';
    const keys:ItemId[]=['meal','fresh','wood','plastic','leaf','metal','seed','fish'];
    const markup=keys.map((k,i)=>`<${i<2?'button type="button"':'div'} class="inv-item ${i<2?'quick-action selected':''}" ${i<2?`data-hotbar="${k}"`:''} title="${defs[k].name}: ${g.inv[k]}" aria-label="${defs[k].name}, còn ${g.inv[k]}"><span class="num">${g.inv[k]}</span>${i<2?`<span class="slot-key">${i+1}</span>`:''}<span class="emoji" aria-hidden="true">${defs[k].icon}</span><span class="inv-label">${defs[k].name}</span></${i<2?'button':'div'}>`).join('');
    if(markup!==this.lastInventoryMarkup){$('#inventory').innerHTML=markup;this.lastInventoryMarkup=markup;
      $('#inventory').querySelectorAll<HTMLButtonElement>('[data-hotbar]').forEach(button=>button.addEventListener('click',()=>this.consume(button.dataset.hotbar==='meal'?'eat':'drink')));
    }
    const target=rules.selectDebris(this.salvage,g.player,this.world.yaw);
    $('#crosshair').classList.toggle('target',Boolean(target));$('#aimHint').classList.toggle('acquired',Boolean(target));
    $('#aimText').textContent=target?`${defs[target.type].icon} ${defs[target.type].name} · SPACE để thu gom`:'Nhìn về vật phẩm trôi nổi · SPACE để quăng vợt';
    if(this.activeDrawer==='bag')this.renderBag();
  }
  private renderRecipes():void{
    const g=this.state;
    const categories=[...new Set(recipes.map(r=>r.category))].filter(c=>this.craftFilter==='TẤT CẢ'||c===this.craftFilter);
    $('#craftRecipes').innerHTML=categories.map(category=>
      `<div class="section-title">${category}</div>`+
      recipes.filter(r=>r.category===category).map(r=>{
        const has=Object.entries(r.cost).every(([id,n])=>g.inv[id as ItemId]>=(n??0));
        const blocked=r.id==='spear'&&g.hasSpear;
        const cost=Object.entries(r.cost).map(([id,n])=>`<span class="cost-chip ${g.inv[id as ItemId]<(n??0)?'missing':''}">${defs[id as ItemId].icon} ${g.inv[id as ItemId]}/${n}</span>`).join('');
        return `<article class="recipe"><span class="recipe-icon" aria-hidden="true">${r.icon}</span><div class="recipe-copy"><h3>${r.title}</h3><p>${r.desc}</p><div class="cost">${cost}</div></div><button type="button" data-craft="${r.id}" ${has&&!blocked?'':'disabled'}>${blocked?'ĐÃ CÓ':has?'CHẾ TẠO':'THIẾU ĐỒ'}</button></article>`;
      }).join('')).join('');
    $('#craftRecipes').querySelectorAll<HTMLButtonElement>('[data-craft]').forEach(b=>b.addEventListener('click',()=>this.craft(b.dataset.craft as RecipeId)));
  }
  private loop(now:number):void{
    const dt=Math.min(.05,Math.max(0,(now-this.last)/1000));this.last=now;
    if(this.running&&!this.paused&&!this.activeDrawer)this.simulate(dt);
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
    $('#restartBtn').addEventListener('click',()=>{this.reset();this.pause(false);this.save();this.message('Đã bắt đầu lại từ ngày đầu tiên.');});
    $('#netBtn').addEventListener('click',()=>this.cast());
    $('#craftBtn').addEventListener('click',()=>this.toggleCraft());
    $('#bagBtn').addEventListener('click',()=>this.toggleBag());
    $('#closeCraft').addEventListener('click',()=>this.setDrawer(null));
    $('#closeBag').addEventListener('click',()=>this.setDrawer(null));
    $('#drawerBackdrop').addEventListener('click',()=>this.setDrawer(null));
    for(const t of ['menu','settings','controls'] as const){
      $(`[data-pause-tab="${t}"]`).addEventListener('click',()=>this.showPauseTab(t));
    }
    $('#qualityBtn').addEventListener('click',()=>this.cycleQuality());
    $('#cameraBtn').addEventListener('click',()=>{this.world.setPreset();this.message('Đã đổi góc camera.');});
    $('#performanceBtn').addEventListener('click',()=>this.togglePerformance());
    $('#assetStatus').addEventListener('click',()=>this.togglePerformance());
    addEventListener('keydown',e=>{
      if(['Space','ArrowUp','ArrowDown','Tab'].includes(e.code)&&this.running)e.preventDefault();
      if(e.code==='Escape'){
        if(this.activeDrawer)this.setDrawer(null);
        else if(this.running)this.pause();
        return;
      }
      if(!this.running||this.paused)return;
      if(e.code==='KeyQ'){if(!e.repeat)this.toggleCraft();return;}
      if(e.code==='Tab'){if(!e.repeat)this.toggleBag();return;}
      if(this.activeDrawer)return;
      this.keys.add(e.code);if(e.repeat)return;
      if(e.code==='Space')this.cast();
      if(e.code==='Digit1')this.consume('eat');if(e.code==='Digit2')this.consume('drink');
      if(e.code==='KeyV')this.world.setPreset();
      if(e.code==='KeyP')this.world.screenshot();
      if(e.code==='F3')this.togglePerformance();
      if(e.code==='F4')this.cycleQuality();
    });
    addEventListener('keyup',e=>this.keys.delete(e.code));
    addEventListener('blur',()=>this.keys.clear());
    addEventListener('beforeunload',()=>this.save());
    const canvas=this.world.canvas;let drag=false;
    canvas.addEventListener('contextmenu',e=>e.preventDefault());
    canvas.addEventListener('pointerdown',e=>{if(!this.running||this.paused||this.activeDrawer)return;if(e.button===2){drag=true;canvas.setPointerCapture(e.pointerId);}else if(e.button===0)this.cast();});
    canvas.addEventListener('pointerup',()=>{drag=false;});
    canvas.addEventListener('pointermove',e=>{if(drag&&!this.paused)this.world.orbit(e.movementX,e.movementY);});
    canvas.addEventListener('wheel',e=>{if(!this.activeDrawer){e.preventDefault();this.world.zoom(e.deltaY);}},{passive:false});
    document.querySelectorAll<HTMLButtonElement>('[data-move]').forEach(b=>{
      const code=`Key${b.dataset.move!.toUpperCase()}`;
      b.addEventListener('pointerdown',e=>{if(this.activeDrawer||this.paused)return;e.preventDefault();this.keys.add(code);b.setPointerCapture(e.pointerId);});
      b.addEventListener('pointerup',()=>this.keys.delete(code));
      b.addEventListener('pointercancel',()=>this.keys.delete(code));
    });
  }
  private cycleQuality():void{
    const q=this.world.quality;this.world.setQuality(q===1?.7:q===.7?.9:1);
    $('#qualityBtn').textContent=`${Math.round(this.world.quality*100)}% ↻`;
    this.message(`Chất lượng render: ${Math.round(this.world.quality*100)}%`);
  }
  private togglePerformance():void{
    this.perfVisible=!this.perfVisible;$('#perfOverlay').classList.toggle('hidden',!this.perfVisible);
    $('#performanceBtn').textContent=this.perfVisible?'ĐANG BẬT':'ĐANG TẮT';
  }
}
