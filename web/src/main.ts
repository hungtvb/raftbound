import './ui.css';
import './legacy';
import { SurvivalGame } from './game';

const canvas=document.getElementById('world');
if(!(canvas instanceof HTMLCanvasElement))throw new Error('Game canvas is missing');
try {
  const game=new SurvivalGame(canvas);
  game.initialize().catch(error=>{
    console.error('[RAFTBOUND] Initialization failed',error);
    document.getElementById('assetStatus')!.textContent='Lỗi tải asset / vật lý';
  });
} catch(error){
  console.error('[RAFTBOUND] WebGL initialization failed',error);
  document.getElementById('startOverlay')!.innerHTML='<div class="intro-shell"><div class="intro-body"><h1>KHÔNG THỂ CHẠY</h1><p>Trình duyệt cần hỗ trợ WebGL2 và tăng tốc đồ họa.</p></div></div>';
}
