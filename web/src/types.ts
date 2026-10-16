export type ItemId = 'wood'|'plastic'|'leaf'|'metal'|'seed'|'fish'|'meal'|'fresh';
export type BuildingId = 'purifier'|'grill'|'planter'|'storage';
export type RecipeId = BuildingId|'raft'|'spear';
export type Tile = [number,number];
export type Inventory = Record<ItemId,number>;
export interface XY { x:number; z:number; }
export interface Salvage extends XY { type: ItemId; speed:number; phase:number; sway:number; }
export interface Structure { id: BuildingId; x:number; z:number; }
export interface SaveGame {
  hp:number; food:number; water:number; day:number; seconds:number;
  player:XY; inv:Inventory; tiles:Tile[]; buildings:Structure[];
  collected:number; quest:number; crafts:number;
  waterTimer:number; cookTimer:number; growTimer:number; sharkHits:number; hasSpear:boolean;
}
export interface SavePayload { version:1; elapsed:number; game:SaveGame; }
export interface RaftRules {
  onRaft(x:number,z:number,tiles:Tile[],tileSize?:number):boolean;
  expandRaft(tiles:Tile[],yaw:number):Tile|null;
  selectDebris<T extends XY>(debris:T[],player:XY,yaw:number,maxDist?:number):T|null;
  castHit<T extends XY>(object:T|null,from:XY,to:XY,debris:T[],radius?:number):boolean;
  readSave(raw:unknown):SavePayload|null;
}
export interface CastState { phase:string; visibleInHand:boolean; progress:number; throwArm:number; }
export interface CastMotion {
  CAST: { windup:number; release:number; contact:number; returnStart:number; end:number };
  state(t:number):CastState;
  flight(t:number,from:XY,to:XY):XY & {y:number; progress:number; phase:string};
}
declare global {
  interface Window { RaftRules:RaftRules; RaftCastMotion:CastMotion; }
}
