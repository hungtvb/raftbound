import type { Inventory, ItemId, RecipeId, SaveGame } from './types';
export const TILE_SIZE=2;
export const SAVE_KEY='raftbound.save.v1';
export const defs:Record<ItemId,{icon:string;name:string;asset?:string}>={
  wood:{icon:'🪵',name:'Gỗ',asset:'driftwood_plank'},
  plastic:{icon:'🧴',name:'Nhựa',asset:'plastic_bottle'},
  leaf:{icon:'🌿',name:'Lá',asset:'palm_leaf'},
  metal:{icon:'🔩',name:'Kim loại',asset:'salvage_barrel'},
  seed:{icon:'🌱',name:'Hạt giống',asset:'palm_leaf'},
  fish:{icon:'🐟',name:'Cá sống'},meal:{icon:'🍲',name:'Thức ăn'},fresh:{icon:'💧',name:'Nước sạch'}
};
export const recipes:{id:RecipeId;category:string;icon:string;title:string;desc:string;cost:Partial<Inventory>}[]=[
 {id:'raft',category:'XÂY DỰNG',icon:'🪵',title:'Mở rộng bè',desc:'Thêm ô sàn theo hướng camera.',cost:{wood:4,plastic:2}},
 {id:'purifier',category:'THIẾT BỊ SINH TỒN',icon:'💧',title:'Máy lọc nước',desc:'Tạo 1 nước sạch mỗi 20 giây.',cost:{wood:4,plastic:3,metal:1}},
 {id:'grill',category:'THIẾT BỊ SINH TỒN',icon:'🔥',title:'Bếp nướng',desc:'Nướng cá thành thức ăn.',cost:{wood:5,metal:2,plastic:1}},
 {id:'planter',category:'TRỒNG TRỌT',icon:'🌱',title:'Khay trồng rau',desc:'Thu hoạch 1 thức ăn mỗi 35 giây.',cost:{wood:4,plastic:2,leaf:2,seed:1}},
 {id:'storage',category:'XÂY DỰNG',icon:'📦',title:'Rương đồ',desc:'Thêm chỗ chứa đồ trên bè.',cost:{wood:6,plastic:3}},
 {id:'spear',category:'CÔNG CỤ',icon:'🔱',title:'Giáo chống cá mập',desc:'Giảm sát thương từ cá mập.',cost:{wood:3,metal:3}}
];
export const quests:{name:string;desc:string;need:number;progress:(g:SaveGame)=>number}[]=[
 {name:'Thu gom nguyên liệu',desc:'Thu thập 5 vật phẩm bằng vợt.',need:5,progress:g=>Math.min(5,g.collected)},
 {name:'Mở rộng chiếc bè',desc:'Xây ít nhất 1 ô sàn.',need:1,progress:g=>Math.max(0,g.tiles.length-4)},
 {name:'Nguồn nước ổn định',desc:'Chế tạo máy lọc nước.',need:1,progress:g=>Number(g.buildings.some(b=>b.id==='purifier'))},
 {name:'Bữa ăn đầu tiên',desc:'Chế tạo bếp nướng.',need:1,progress:g=>Number(g.buildings.some(b=>b.id==='grill'))},
 {name:'Vườn giữa biển',desc:'Chế tạo khay trồng rau.',need:1,progress:g=>Number(g.buildings.some(b=>b.id==='planter'))},
 {name:'Trụ vững qua đêm',desc:'Sống tới ngày thứ hai.',need:1,progress:g=>Number(g.day>=2)}
];
export function freshGame():SaveGame{return {
 hp:100,food:87,water:83,day:1,seconds:0,player:{x:0,z:0},
 inv:{wood:2,plastic:1,leaf:0,metal:0,seed:0,fish:0,meal:1,fresh:1},
 tiles:[[-1,-1],[-1,0],[0,-1],[0,0]],buildings:[],collected:0,quest:0,crafts:0,
 waterTimer:0,cookTimer:0,growTimer:0,sharkHits:0,hasSpear:false
};}
